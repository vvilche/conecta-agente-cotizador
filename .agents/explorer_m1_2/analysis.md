# Deep Technical Analysis & Architecture Specification: Odoo Mock Server & Audit Engine

## Executive Summary
This document provides the complete architecture design and technical specification for two critical components of Milestone 1 in the `odoo_ecosystem` module:
1. `src/odoo_ecosystem/mock_server.py`: An in-memory and HTTP-accessible Odoo mock server supporting multi-version RPC/REST protocols (Odoo 14, 15, 16, 17), domain filtering evaluation, full CRUD operation simulation across all 9 target models, and controllable error injection (rate limiting, auth errors, timeouts).
2. `src/odoo_ecosystem/audit.py`: Security credential management (Environment + Vault interface with secret redaction), structured JSONL API audit logging, and a 0% auto-execution draft staging helper.

---

## Part 1: Architecture & Design for `mock_server.py`

### 1.1 Multi-Version Protocol Compatibility
Odoo ERP has evolved its API protocols across versions 14 through 17. `mock_server.py` must support and simulate all of them:

| Odoo Version | Core Protocol | Primary Endpoints | Auth Mechanism | Key Behavioral Nuance |
|--------------|---------------|-------------------|----------------|----------------------|
| **Odoo 14**  | XML-RPC / JSON-RPC | `/xmlrpc/2/common`, `/xmlrpc/2/object`, `/jsonrpc` | `common.authenticate(db, user, pwd, env)` -> `uid` | Loose domain tuple types allowed (lists/tuples). |
| **Odoo 15**  | XML-RPC / JSON-RPC | `/xmlrpc/2/common`, `/xmlrpc/2/object`, `/web/session/authenticate` | Session Cookie + `uid` | `user_context` dictionary returned in authentication. |
| **Odoo 16**  | XML-RPC / JSON-RPC | `/xmlrpc/2/*`, `/web/dataset/call_kw` | Session / UID | Strict domain validation (tuples must be 3-element `(field, operator, value)`). |
| **Odoo 17**  | REST API / JSON-RPC | `/api/v1/auth/token`, `/api/v1/models/<model>`, `/jsonrpc` | Bearer Token / API Key (`Authorization: Bearer <key>`) | Native REST API endpoints, updated keyword arguments (`order`, `limit`, `offset`). |

### 1.2 Class Architecture Diagram (`mock_server.py`)

```
+-----------------------------------------------------------------------------+
|                               MockOdooServer                                |
|  - version: OdooVersion (V14, V15, V16, V17)                                |
|  - db: MockOdooDB                                                           |
|  - domain_evaluator: DomainEvaluator                                        |
|  - fault_config: FaultInjectionConfig                                       |
+-----------------------------------------------------------------------------+
         |                        |                         |
         v                        v                         v
+------------------+    +------------------+    +-----------------------+
|  XMLRPCController|    | JSONRPCController|    |     RESTController    |
| - common.auth()  |    | - /web/session   |    | - /api/v1/auth/token  |
| - execute_kw()   |    | - /jsonrpc       |    | - /api/v1/models/*    |
+------------------+    +------------------+    +-----------------------+
         \                        |                        /
          +-----------------------+-----------------------+
                                  |
                                  v
                        +-------------------+
                        |   MockOdooDB      |
                        | - tables: dict    |
                        | - seed_defaults() |
                        | - CRUD methods    |
                        +-------------------+
```

### 1.3 In-Memory Seed Database (`MockOdooDB`)
The mock database initializes default fixture data for all 9 required target Odoo models:

1. **`res.partner`**:
   - Fields: `id`, `name`, `email`, `phone`, `vat`, `is_company`, `active`, `street`, `city`
   - Default Seed: 3 records (Customer: "Empresa Electrica COMASA S.A.", Vendor: "Transelec S.A.", Contact: "Juan Perez")

2. **`crm.lead`**:
   - Fields: `id`, `name`, `partner_id`, `expected_revenue`, `probability`, `stage_id`, `user_id`, `description`, `type`
   - Default Seed: 2 leads ("Licitación Mantenimiento Subestación 2026", "Prospección Servicio SSCC")

3. **`sale.order`**:
   - Fields: `id`, `name`, `partner_id`, `date_order`, `state`, `amount_untaxed`, `amount_tax`, `amount_total`, `order_line`
   - Default Seed: 2 sale orders ("SO001" - `draft`, "SO002" - `sale`)

4. **`project.project`**:
   - Fields: `id`, `name`, `partner_id`, `user_id`, `analytic_account_id`, `allow_billable`, `tasks`
   - Default Seed: 2 projects ("Proyecto Digitalización COMASA", "Inspección PMUS ENEL")

5. **`project.task`**:
   - Fields: `id`, `name`, `project_id`, `user_id`, `stage_id`, `allocated_hours`, `effective_hours`, `kanban_state`
   - Default Seed: 3 tasks ("Auditoría SITR AT-SITR-1", "Revisión Esquema EDAC/ERAG", "Elaboración Informe Técnico")

6. **`account.analytic.account`**:
   - Fields: `id`, `name`, `code`, `partner_id`, `balance`
   - Default Seed: 2 cost centers ("CC-COMASA-001", "CC-TRANSELEC-002")

7. **`crossovered.budget`**:
   - Fields: `id`, `name`, `user_id`, `date_from`, `date_to`, `state`, `crossovered_budget_line`
   - Default Seed: 1 budget ("Presupuesto Operativo Anual 2026" - state `validate`)

8. **`account.move`**:
   - Fields: `id`, `name`, `move_type`, `partner_id`, `invoice_date`, `state`, `amount_untaxed`, `amount_tax`, `amount_total`, `invoice_line_ids`
   - Default Seed: 2 invoices ("INV/2026/0001" - `out_invoice`, "BILL/2026/0001" - `in_invoice`)

9. **`account.payment`**:
   - Fields: `id`, `name`, `payment_type`, `partner_type`, `partner_id`, `amount`, `date`, `state`, `ref`
   - Default Seed: 2 payments ("PAY/2026/0001" - `posted`, "PAY/2026/0002" - `draft`)

### 1.4 Domain Filtering Engine (`DomainEvaluator`)
Odoo uses Polish prefix notation for logical operations in domain lists.

#### Domain Grammar & Syntax Rules:
- Tuples: `(field_name, operator, value)`
- Default implicit operator: `&` (AND) between consecutive tuples.
- Explicit logical operators: `'&'` (AND), `'|'` (OR), `'!'` (NOT).
- Supported comparison operators:
  - `=` / `!=`: Exact equality / inequality
  - `>`, `>=`, `<`, `<=`: Numeric / Date comparisons
  - `in` / `not in`: Membership check in list/set
  - `like` / `ilike`: Substring match (case-sensitive / case-insensitive)
  - `=like` / `=ilike`: Wildcard match where `%` matches any sequence and `_` matches a single character.

#### Evaluation Algorithm (Polish Notation Evaluator):
```python
def evaluate_domain(record: dict, domain: list) -> bool:
    if not domain:
        return True
    
    stack = []
    # Reverse polish evaluation using stack
    tokens = list(domain)
    
    def _eval_token(tokens_iter):
        token = next(tokens_iter)
        if token == '&':
            left = _eval_token(tokens_iter)
            right = _eval_token(tokens_iter)
            return left and right
        elif token == '|':
            left = _eval_token(tokens_iter)
            right = _eval_token(tokens_iter)
            return left or right
        elif token == '!':
            expr = _eval_token(tokens_iter)
            return not expr
        elif isinstance(token, (list, tuple)) and len(token) == 3:
            field, op, val = token
            return _compare_field(record.get(field), op, val)
        else:
            raise ValueError(f"Invalid domain token: {token}")

    tokens_iter = iter(tokens)
    res = _eval_token(tokens_iter)
    # If there are remaining implicit AND tokens
    while True:
        try:
            next_token = _eval_token(tokens_iter)
            res = res and next_token
        except StopIteration:
            break
    return res
```

### 1.5 Fault & Error Injection Framework (`FaultInjectionConfig`)
To thoroughly test error handling in the client layer, `MockOdooServer` supports injectable fault modes:

```python
@dataclass
class FaultInjectionConfig:
    simulate_rate_limit: bool = False  # Triggers 429 Too Many Requests
    rate_limit_after_n_calls: Optional[int] = None
    simulate_auth_failure: bool = False  # Triggers AccessDenied (401)
    simulate_network_timeout: bool = False  # Simulates delay > client timeout
    timeout_delay_seconds: float = 30.0
    simulate_server_error: bool = False  # Triggers 500 Internal Server Error / RPC Fault
    simulate_validation_error: bool = False # Triggers Odoo ValidationError / UserError
    custom_fault_models: Dict[str, str] = field(default_factory=dict) # e.g. {"sale.order": "LockError"}
```

---

## Part 2: Architecture & Design for `audit.py`

### 2.1 Credential Management & Vault Integration (`CredentialManager`)
Security credential handling must ensure zero plaintext secrets are leaked into logs or codebase.

```
+------------------------------------------------------------------+
|                        CredentialManager                         |
|  - vault_provider: VaultProvider                                 |
|  - env_provider: EnvCredentialProvider                           |
+------------------------------------------------------------------+
                                 |
                                 v
                 +-------------------------------+
                 |  get_odoo_credentials()       |
                 |  - url: str                   |
                 |  - db: str                    |
                 |  - username: str              |
                 |  - password: SecretStr        |
                 |  - api_key: Optional[SecretStr]|
                 +-------------------------------+
```

#### Secret Redaction Engine:
```python
SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "authorization", "cookie", "pwd"}

def mask_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                masked[k] = "***MASKED***"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data
```

### 2.2 Structured API Audit Recorder (`AuditLogger`)
Every outgoing RPC / REST call executed against Odoo (mock or real) is recorded in JSON Lines format (`audit.jsonl`) and kept in an in-memory `AuditLogRegistry`.

#### Schema of an Audit Log Entry:
```json
{
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "timestamp": "2026-07-28T12:05:00.123456Z",
  "protocol": "xmlrpc",
  "odoo_version": "16.0",
  "endpoint": "https://odoo.internal/xmlrpc/2/object",
  "model": "sale.order",
  "method": "search_read",
  "domain": [["state", "=", "draft"]],
  "fields": ["name", "partner_id", "amount_total"],
  "payload_size_bytes": 248,
  "response_time_ms": 42.5,
  "status": "SUCCESS",
  "http_status_code": 200,
  "user_agent_id": "swarm_agent_cotizacion",
  "error_details": null
}
```

### 2.3 Draft Staging Helper (`DraftStager` - 0% Auto-Execution)
To comply with the project requirement of **0% auto-execution enforcement**, any write/create/delete operation attempted by an agent must pass through `DraftStager`.

#### Workflow:
1. Agent calls `create_draft(model, values, agent_id)`.
2. `DraftStager` validates input schema against Odoo model rules.
3. `DraftStager` generates a unique `draft_id` (e.g., `DRAFT-20260728-001`), creates a `DraftRecord` in state `PENDING_APPROVAL`, and saves it to disk (`staged_drafts.json`).
4. **No Odoo API write call is executed yet.**
5. When human supervisor reviews in Supervisor UI and approves, `commit_draft(draft_id, vobo_token, approved_by)` is invoked.
6. Only upon receipt of valid VoBo confirmation does `DraftStager` trigger `client.create()` or `client.write()` to commit changes to Odoo ERP.

---

## Part 3: Implementation Strategy & Component Specifications

### 3.1 `mock_server.py` File Specification
- File location: `src/odoo_ecosystem/mock_server.py`
- Main exports:
  - `MockOdooDB`: Data store & seed generator.
  - `DomainEvaluator`: Domain filter parser & evaluator.
  - `FaultInjectionConfig`: Fault control dataclass.
  - `MockOdooServer`: Central mock controller supporting XML-RPC, JSON-RPC, REST handlers.
  - `MockOdooHTTPHandler`: stdlib `http.server.BaseHTTPRequestHandler` implementation for running a live local server.
  - `MockClientAdapter`: Direct Python call adapter bypassing sockets for ultra-fast pytest execution.

### 3.2 `audit.py` File Specification
- File location: `src/odoo_ecosystem/audit.py`
- Main exports:
  - `VaultProvider` (ABC), `EnvCredentialProvider`, `MockVaultProvider`.
  - `CredentialManager`: Resolves Odoo connection params safely.
  - `mask_sensitive_data`: Data redactor.
  - `AuditLogEntry`: Dataclass matching JSON log schema.
  - `AuditLogger`: JSONL file logger + memory logger with rotation support.
  - `DraftRecord`: Dataclass representing staged draft operations.
  - `DraftStager`: Draft creation, storage, VoBo approval, and execution coordinator.

---

## Part 4: Proposed Code Artifacts & Interfaces

### 4.1 Proposed `mock_server.py` Skeleton Implementation Blueprint
```python
# Interface Sketch for src/odoo_ecosystem/mock_server.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
import uuid
import time
import re

class OdooVersion:
    V14 = "14.0"
    V15 = "15.0"
    V16 = "16.0"
    V17 = "17.0"

@dataclass
class FaultInjectionConfig:
    simulate_rate_limit: bool = False
    simulate_auth_failure: bool = False
    simulate_network_timeout: bool = False
    timeout_delay_seconds: float = 30.0
    simulate_server_error: bool = False

class DomainEvaluator:
    @staticmethod
    def evaluate(record: Dict[str, Any], domain: List[Any]) -> bool:
        # Polish notation evaluator for domain filter lists
        ...

class MockOdooDB:
    def __init__(self):
        self.tables: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self._seed_default_data()

    def _seed_default_data(self):
        # Seeds res.partner, crm.lead, sale.order, project.project, project.task,
        # account.analytic.account, crossovered.budget, account.move, account.payment
        ...

    def search_read(self, model: str, domain: List[Any], fields: Optional[List[str]] = None, offset: int = 0, limit: Optional[int] = None, order: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def create(self, model: str, vals: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[int, List[int]]:
        ...

    def write(self, model: str, ids: List[int], vals: Dict[str, Any]) -> bool:
        ...

    def unlink(self, model: str, ids: List[int]) -> bool:
        ...

class MockOdooServer:
    def __init__(self, version: str = OdooVersion.V16, fault_config: Optional[FaultInjectionConfig] = None):
        self.version = version
        self.db = MockOdooDB()
        self.fault_config = fault_config or FaultInjectionConfig()
        self.valid_users = {"admin": "admin", "agent_user": "secret_pass"}
        self.valid_tokens = {"bearer_token_123": "admin"}

    def xmlrpc_authenticate(self, db_name: str, login: str, password: str, user_agent_env: Any) -> int:
        ...

    def xmlrpc_execute_kw(self, db_name: str, uid: int, password: str, model: str, method: str, args: List[Any], kwargs: Optional[Dict[str, Any]] = None) -> Any:
        ...

    def jsonrpc_dispatch(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def rest_dispatch(self, method: str, path: str, headers: Dict[str, str], body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        ...
```

### 4.2 Proposed `audit.py` Skeleton Implementation Blueprint
```python
# Interface Sketch for src/odoo_ecosystem/audit.py
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import os
import uuid

@dataclass
class AuditLogEntry:
    request_id: str
    timestamp: str
    protocol: str
    odoo_version: str
    endpoint: str
    model: str
    method: str
    domain: Optional[List[Any]]
    fields: Optional[List[str]]
    payload_size_bytes: int
    response_time_ms: float
    status: str  # SUCCESS, RATE_LIMITED, AUTH_ERROR, SERVER_ERROR
    http_status_code: int
    user_agent_id: str
    error_details: Optional[str] = None

class AuditLogger:
    def __init__(self, log_file_path: str = ".agents/audit_logs/odoo_api.jsonl"):
        self.log_file_path = log_file_path
        self.memory_entries: List[AuditLogEntry] = []
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

    def log_call(self, entry: AuditLogEntry):
        self.memory_entries.append(entry)
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

@dataclass
class DraftRecord:
    draft_id: str
    created_at: str
    agent_id: str
    target_model: str
    operation_type: str  # create, write, unlink, action_post, etc.
    payload: Dict[str, Any]
    state: str  # PENDING_APPROVAL, APPROVED, REJECTED, COMMITTED
    vobo_details: Optional[Dict[str, Any]] = None

class DraftStager:
    def __init__(self, storage_path: str = ".agents/drafts/staged_drafts.json"):
        self.storage_path = storage_path
        self.drafts: Dict[str, DraftRecord] = {}
        self._load_drafts()

    def create_draft(self, agent_id: str, model: str, operation_type: str, payload: Dict[str, Any]) -> DraftRecord:
        ...

    def approve_draft(self, draft_id: str, approved_by: str, vobo_notes: str) -> DraftRecord:
        ...

    def reject_draft(self, draft_id: str, rejected_by: str, reason: str) -> DraftRecord:
        ...
```

---

## Part 5: Verification & Testing Plan

### 5.1 Unit Tests for `mock_server.py` (`tests/test_odoo_ecosystem.py`)
- Test 1: XML-RPC auth success & failure.
- Test 2: JSON-RPC dataset `call_kw` execution for `search_read`, `create`, `write`, `unlink`.
- Test 3: REST API endpoint dispatching for Odoo 17 (`/api/v1/models/sale.order`).
- Test 4: Complex domain filter parsing (`[('state', '=', 'draft'), ('amount_total', '>', 1000)]`, `'|'` condition).
- Test 5: Fault injection verification (Rate limit 429 error raised, Auth failure 401, Timeout simulation).

### 5.2 Unit Tests for `audit.py` (`tests/test_odoo_ecosystem.py`)
- Test 1: Credential manager loading from ENV and Vault interface fallback.
- Test 2: Sensitive credential masking (`mask_sensitive_data` masks `password` and `api_key`).
- Test 3: Audit logger JSONL line writing & memory entries query.
- Test 4: Draft stager 0% auto-execution enforcement (draft created as `PENDING_APPROVAL`, cannot be committed without VoBo token approval).
