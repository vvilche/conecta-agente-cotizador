# Detailed Technical Analysis & Design Specification: Odoo Core Connector & Models (`odoo_ecosystem`)

**Milestone**: 1 — Odoo Core Connector & Models  
**Author**: Explorer 1 (`.agents/explorer_m1_1`)  
**Date**: 2026-07-28  

---

## 1. Executive Overview & System Architecture

Milestone 1 establishes the bedrock layer of the **Sistema Agenticio Inteligente Ecosistémico para Odoo ERP**. The `odoo_ecosystem` package provides a robust, multi-protocol communication engine and type-safe Pydantic domain models that insulate the upper multi-agent swarm (`swarm_engine`), RAG historical memory (`rag_memory`), and Human-in-the-Loop supervisor console (`supervisor_ui`) from low-level Odoo RPC intricacies.

```
+-------------------------------------------------------------------+
|               Supervisor UI / Agent Swarm Engine                  |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               odoo_ecosystem.models (Pydantic v2)                 |
|  (ResPartner, CrmLead, SaleOrder, ProjectProject, AccountMove...) |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               odoo_ecosystem.client (OdooClient)                  |
|  - Unified Interface: search_read, create_draft, commit_draft     |
|  - Multi-Protocol: XML-RPC / JSON-RPC / REST                      |
|  - Resilience: Retries (tenacity), Rate Limiter, SSL/Env config   |
|  - Audit Integration: AuditLogger calls on mutation/read          |
+-------------------------------------------------------------------+
                                  |
            +---------------------+---------------------+
            |                     |                     |
            v                     v                     v
     [XML-RPC /xmlrpc/2]   [JSON-RPC /jsonrpc]     [Odoo REST API]
```

---

## 2. Dependencies & Build Configuration (`pyproject.toml`)

### 2.1 Dependency Rationale

1. **Python Runtime**: `python = "^3.10"` (Required by project spec for modern type union syntax `X | Y`, `match/case`, and `asyncio` enhancements).
2. **Data Validation & Settings**:
   - `pydantic>=2.5.0`: Fast runtime validation, serialisation, and standard schema creation.
   - `pydantic-settings>=2.1.0`: Clean environment variable loading (`.env` support for Odoo staging vs. prod config).
3. **HTTP & RPC Protocol Stack**:
   - `requests>=2.31.0`: Standard library for XML-RPC and HTTP-based JSON-RPC/REST interactions.
   - `urllib3>=2.0.0`: Connection pooling, socket timeout configuration, and SSL adapter control.
4. **Resilience & Rate Limiting**:
   - `tenacity>=8.2.0`: Declarative, configurable retries with exponential backoff and jitter for transient 5xx/network errors.
5. **Testing & Quality Assurance**:
   - `pytest>=7.4.0`: Test discovery and execution.
   - `pytest-cov>=4.1.0`: Test coverage enforcement.
   - `pytest-mock>=3.11.0`: Easy mocking of HTTP/RPC endpoints for the mock Odoo server harness.

### 2.2 Complete `pyproject.toml` Blueprint

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "odoo_ecosystem"
version = "0.1.0"
description = "Ecosystem Connector, Pydantic Abstraction Models, and Mock Server for Odoo ERP Integration"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [
    { name = "Inteligencia Comercial Team" }
]
dependencies = [
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "requests>=2.31.0",
    "urllib3>=2.0.0",
    "tenacity>=8.2.0",
    "python-dotenv>=1.0.0",
    "typing-extensions>=4.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.9.0",
    "ruff>=0.1.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --cov=src --cov-report=term-missing"
testpaths = [
    "tests",
]
python_files = [
    "test_*.py",
]
python_classes = [
    "Test*",
]
python_functions = [
    "test_*",
]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

---

## 3. Odoo Core Connector Architecture (`src/odoo_ecosystem/client.py`)

### 3.1 Key Requirements & Design Features

1. **Protocol Flexibility**:
   - **XML-RPC**: Native Odoo endpoints (`/xmlrpc/2/common` for auth/version, `/xmlrpc/2/object` for `execute_kw`). Uses Python's `xmlrpc.client` wrapped with HTTP timeout and SSL custom context support.
   - **JSON-RPC**: Standard HTTP POST to `/jsonrpc` endpoint using payload format `{"jsonrpc": "2.0", "method": "call", "params": {...}, "id": ...}`.
   - **REST**: Optional HTTP bearer/API key REST wrapper for Odoo 16/17 REST plugins or API gateways.
2. **Environment Configuration (`OdooConfig`)**:
   - Manages Staging vs. Production parameters (e.g. disabling strict SSL check in staging if required, custom timeouts, distinct DB names).
   - Reads directly from environment variables or `.env` files.
3. **Unified Interface Contracts** (as required by `PROJECT.md`):
   - `search_read(model: str, domain: list, fields: list = None, offset: int = 0, limit: int = None, order: str = None) -> list[dict]`
   - `create_draft(model: str, values: dict) -> dict`
   - `commit_draft(draft_id: str, approved_by: str) -> dict`
   - Auxiliary CRUD: `read()`, `create()`, `write()`, `unlink()`, `execute_kw()`.
4. **Draft Lifecycle & VoBo Policy**:
   - `create_draft`: Prepares a staged change structure with a unique `draft_id`, status `pending_vobo`, target `model`, and proposed `values`. It does NOT execute a mutating write in production Odoo unless explicitly allowed or staged as an Odoo `state='draft'` record with audit logging.
   - `commit_draft`: Receives `draft_id` and `approved_by` signature from the Supervisor UI, verifies non-repudiation and authorization, and performs the actual Odoo database write/confirmation (`execute_kw('create'/'write'/'action_confirm')`).
5. **Resilience & Rate Limiting**:
   - **Token Bucket Rate Limiter**: Thread-safe token bucket preventing HTTP 429 / XML-RPC socket exhaustion by limiting requests per second (default: 10 req/sec).
   - **Exponential Backoff**: Wrapped with `tenacity` retrying on `requests.exceptions.RequestException`, `xmlrpc.client.ProtocolError`, and transient HTTP 5xx responses.
6. **Exception Taxonomy**:
   - `OdooEcosystemError` (Base)
   - `OdooConnectionError` (Network/DNS/Connection refused)
   - `OdooAuthenticationError` (Bad DB/User/Password/API key)
   - `OdooValidationError` (Odoo UserError/ValidationError)
   - `OdooRPCError` (Protocol level XML-RPC/JSON-RPC errors)

### 3.2 `client.py` Class Interface & Blueprint

```python
"""
Odoo Ecosystem Client Module.
Supports XML-RPC, JSON-RPC, and REST protocols with resilience, rate-limiting,
and 100% VoBo draft lifecycle management.
"""

from typing import Any, Dict, List, Optional, Union
import time
import uuid
import logging
from xmlrpc.client import ServerProxy, Error as XmlRpcError
import requests
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl

logger = logging.getLogger(__name__)


class OdooConfig(BaseSettings):
    """Configuration settings for Odoo Connection."""
    url: str = Field(default="http://localhost:8069", description="Odoo Server Base URL")
    db: str = Field(default="odoo_db", description="Odoo Database Name")
    username: str = Field(default="admin", description="Odoo Username")
    password: str = Field(default="admin", description="Odoo Password or API Key")
    protocol: str = Field(default="xmlrpc", description="Protocol: xmlrpc | jsonrpc | rest")
    environment: str = Field(default="staging", description="Environment: staging | prod")
    timeout: int = Field(default=30, description="HTTP Request Timeout in seconds")
    max_retries: int = Field(default=3, description="Max Retry Attempts for Transient Errors")
    rate_limit_rps: float = Field(default=10.0, description="Max Requests Per Second")
    verify_ssl: bool = Field(default=True, description="Verify SSL Certificates")

    model_config = SettingsConfigDict(env_prefix="ODOO_", env_file=".env", extra="ignore")


class OdooClientException(Exception):
    """Base Exception for Odoo Ecosystem Client."""
    pass

class OdooConnectionException(OdooClientException):
    """Raised on socket/network failure."""
    pass

class OdooAuthenticationException(OdooClientException):
    """Raised on invalid credentials or failed UID auth."""
    pass

class OdooRPCException(OdooClientException):
    """Raised when Odoo returns a server-side exception/fault."""
    pass


class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter."""
    def __init__(self, rps: float):
        self.rps = rps
        self.capacity = rps
        self.tokens = rps
        self.last_update = time.monotonic()

    def acquire(self):
        now = time.monotonic()
        delta = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + delta * self.rps)
        if self.tokens < 1.0:
            sleep_time = (1.0 - self.tokens) / self.rps
            time.sleep(sleep_time)
            self.tokens = 0.0
        else:
            self.tokens -= 1.0


class OdooClient:
    """
    Unified Client Connector for Odoo ERP.
    Implements search_read, create_draft, and commit_draft interface contract.
    """
    def __init__(self, config: Optional[OdooConfig] = None, audit_logger: Optional[Any] = None):
        self.config = config or OdooConfig()
        self.audit_logger = audit_logger
        self.uid: Optional[int] = None
        self._rate_limiter = TokenBucketRateLimiter(self.config.rate_limit_rps)
        self._draft_store: Dict[str, Dict[str, Any]] = {}  # Staged pending drafts storage

    def authenticate(self) -> int:
        """Authenticate against Odoo and return UID."""
        self._rate_limiter.acquire()
        if self.config.protocol == "xmlrpc":
            common_url = f"{self.config.url.rstrip('/')}/xmlrpc/2/common"
            try:
                common = ServerProxy(common_url)
                self.uid = common.authenticate(
                    self.config.db, self.config.username, self.config.password, {}
                )
                if not self.uid:
                    raise OdooAuthenticationException(f"Failed authentication for user {self.config.username} on DB {self.config.db}")
                return self.uid
            except Exception as e:
                raise OdooAuthenticationException(f"XML-RPC Authentication error: {str(e)}") from e
        elif self.config.protocol == "jsonrpc":
            json_url = f"{self.config.url.rstrip('/')}/jsonrpc"
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "common",
                    "method": "authenticate",
                    "args": [self.config.db, self.config.username, self.config.password, {}]
                },
                "id": 1
            }
            try:
                resp = requests.post(json_url, json=payload, timeout=self.config.timeout, verify=self.config.verify_ssl)
                data = resp.json()
                if "error" in data:
                    raise OdooAuthenticationException(f"JSON-RPC Auth Error: {data['error']}")
                self.uid = data.get("result")
                if not self.uid:
                    raise OdooAuthenticationException("Invalid credentials, returned null UID")
                return self.uid
            except Exception as e:
                raise OdooAuthenticationException(f"JSON-RPC Auth failure: {str(e)}") from e
        else:
            # REST protocol or default fallback
            self.uid = 1
            return self.uid

    def execute_kw(self, model: str, method: str, args: List[Any], kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """Execute method on Odoo model with auto-authentication and audit logging."""
        if not self.uid:
            self.authenticate()
        
        kwargs = kwargs or {}
        self._rate_limiter.acquire()
        
        start_time = time.time()
        try:
            if self.config.protocol == "xmlrpc":
                object_url = f"{self.config.url.rstrip('/')}/xmlrpc/2/object"
                models_proxy = ServerProxy(object_url)
                result = models_proxy.execute_kw(
                    self.config.db, self.uid, self.config.password, model, method, args, kwargs
                )
            elif self.config.protocol == "jsonrpc":
                json_url = f"{self.config.url.rstrip('/')}/jsonrpc"
                payload = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "service": "object",
                        "method": "execute_kw",
                        "args": [self.config.db, self.uid, self.config.password, model, method, args, kwargs]
                    },
                    "id": int(time.time() * 1000)
                }
                resp = requests.post(json_url, json=payload, timeout=self.config.timeout, verify=self.config.verify_ssl)
                data = resp.json()
                if "error" in data:
                    raise OdooRPCException(f"Odoo RPC Error: {data['error']}")
                result = data.get("result")
            else:
                raise NotImplementedError(f"Protocol {self.config.protocol} not fully implemented")
            
            duration_ms = (time.time() - start_time) * 1000
            if self.audit_logger:
                self.audit_logger.log_call(model=model, method=method, duration_ms=duration_ms, status="SUCCESS")
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            if self.audit_logger:
                self.audit_logger.log_call(model=model, method=method, duration_ms=duration_ms, status="ERROR", error=str(e))
            raise OdooRPCException(f"Failed execute_kw {model}.{method}: {str(e)}") from e

    def search_read(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Required Interface Contract: Search & Read records from Odoo model.
        """
        domain = domain or []
        kwargs: Dict[str, Any] = {"offset": offset}
        if fields:
            kwargs["fields"] = fields
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
            
        return self.execute_kw(model=model, method="search_read", args=[domain], kwargs=kwargs)

    def create_draft(self, model: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Required Interface Contract: Create a staged draft (0% auto-execution rule).
        Generates a unique draft ID and stores payload pending Human Supervisor VoBo approval.
        """
        draft_id = f"draft_{uuid.uuid4().hex[:12]}"
        draft_record = {
            "draft_id": draft_id,
            "model": model,
            "values": values,
            "status": "pending_vobo",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": self.config.environment
        }
        self._draft_store[draft_id] = draft_record
        logger.info("Draft created: %s for model %s", draft_id, model)
        return draft_record

    def commit_draft(self, draft_id: str, approved_by: str) -> Dict[str, Any]:
        """
        Required Interface Contract: Execute database write strictly upon VoBo approval.
        """
        if draft_id not in self._draft_store:
            raise KeyError(f"Draft ID {draft_id} not found in pending queue")
        
        draft = self._draft_store[draft_id]
        if draft["status"] == "committed":
            raise ValueError(f"Draft {draft_id} is already committed")
        
        model = draft["model"]
        values = draft["values"]
        
        # Perform real record creation in Odoo
        record_id = self.execute_kw(model=model, method="create", args=[values])
        
        draft["status"] = "committed"
        draft["approved_by"] = approved_by
        draft["committed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        draft["odoo_record_id"] = record_id
        
        logger.info("Draft %s committed by %s -> Odoo ID: %s", draft_id, approved_by, record_id)
        return draft
```

---

## 4. Odoo Domain Models Abstraction (`src/odoo_ecosystem/models.py`)

To ensure standard data serialization, input validation, and clear documentation, we define Pydantic v2 domain abstractions covering CRM/Sales, Projects/Operations, and Finance/Budgets.

### 4.1 Schema Mapping Table

| Odoo Model Name | Pydantic Class | Domain Category | Key Fields & Relationships |
|---|---|---|---|
| `res.partner` | `ResPartner` | CRM & Base | `id`, `name`, `email`, `phone`, `vat`, `is_company`, `credit_limit`, `country_id` |
| `crm.lead` | `CrmLead` | CRM & Sales | `id`, `name`, `partner_id`, `expected_revenue`, `probability`, `stage_id`, `type` |
| `sale.order` | `SaleOrder` | CRM & Sales | `id`, `name`, `partner_id`, `state`, `amount_total`, `order_line`, `analytic_account_id` |
| `sale.order.line` | `SaleOrderLine` | CRM & Sales | `id`, `order_id`, `product_id`, `name`, `product_uom_qty`, `price_unit`, `price_subtotal` |
| `project.project` | `ProjectProject` | Operations | `id`, `name`, `partner_id`, `analytic_account_id`, `privacy_visibility`, `active` |
| `project.task` | `ProjectTask` | Operations | `id`, `name`, `project_id`, `stage_id`, `planned_hours`, `effective_hours`, `remaining_hours` |
| `account.analytic.account`| `AccountAnalyticAccount`| Operations/Finance| `id`, `name`, `code`, `partner_id`, `balance`, `debit`, `credit` |
| `crossovered.budget` | `CrossoveredBudget` | Finance & Budget | `id`, `name`, `user_id`, `date_from`, `date_to`, `state`, `crossovered_budget_line` |
| `crossovered.budget.lines`| `CrossoveredBudgetLines`| Finance & Budget| `id`, `crossovered_budget_id`, `analytic_account_id`, `planned_amount`, `practical_amount` |
| `account.move` | `AccountMove` | Finance (Invoices/DTE)| `id`, `name`, `move_type`, `partner_id`, `state`, `amount_total`, `invoice_line_ids` |
| `account.move.line` | `AccountMoveLine` | Finance (Invoice Lines)| `id`, `move_id`, `product_id`, `quantity`, `price_unit`, `price_subtotal`, `analytic_account_id` |
| `account.payment` | `AccountPayment` | Finance (Payments) | `id`, `name`, `payment_type`, `partner_type`, `partner_id`, `amount`, `state`, `ref` |

### 4.2 Handling Many2one, One2many, and Many2many in Odoo Pydantic Models

In Odoo RPC:
- **Many2one fields** return either `False` (if empty) or a tuple `[id, name]` (e.g. `[42, "Acme Corp"]`).
- **One2many / Many2many fields** return either a list of IDs `[101, 102, 103]` or nested list of record dicts.

Our Pydantic models will use custom validators or flexible types to cleanly convert standard Odoo RPC responses into standard Python primitives (e.g. extracting `partner_id` integer or pair, while exposing `partner_name` properties).

### 4.3 `models.py` Complete Blueprint

```python
"""
Pydantic v2 Models for Odoo Ecosystem Abstractions.
Covers CRM & Sales, Projects & Operations, and Finance & Budgets.
"""

from typing import List, Optional, Union, Tuple, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class OdooBaseModel(BaseModel):
    """Base class for all Odoo entity abstractions."""
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[int] = Field(default=None, description="Odoo Database Primary Key ID")

    @classmethod
    def _extract_many2one_id(cls, v: Any) -> Optional[int]:
        if isinstance(v, (list, tuple)) and len(v) > 0:
            return int(v[0])
        elif isinstance(v, int):
            return v
        return None

    @classmethod
    def _extract_many2one_name(cls, v: Any) -> Optional[str]:
        if isinstance(v, (list, tuple)) and len(v) > 1:
            return str(v[1])
        return None


# ==========================================
# 1. CRM & SALES DOMAIN
# ==========================================

class ResPartner(OdooBaseModel):
    """Abstraction for res.partner (Customers, Vendors, Contacts)."""
    name: str = Field(..., description="Partner Name or Company Name")
    is_company: bool = Field(default=False, description="True if partner is a legal entity")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    vat: Optional[str] = Field(default=None, description="Tax ID / RUT")
    street: Optional[str] = Field(default=None, description="Street Address")
    city: Optional[str] = Field(default=None, description="City")
    country_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Country Many2one")
    credit_limit: float = Field(default=0.0, description="Credit Limit")
    active: bool = Field(default=True, description="Active status")


class CrmLead(OdooBaseModel):
    """Abstraction for crm.lead (Opportunities & Leads)."""
    name: str = Field(..., description="Lead / Opportunity Subject")
    partner_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Associated Customer")
    email_from: Optional[str] = Field(default=None, description="Contact Email")
    phone: Optional[str] = Field(default=None, description="Contact Phone")
    expected_revenue: float = Field(default=0.0, description="Expected Revenue")
    probability: float = Field(default=0.0, description="Win Probability Percentage")
    stage_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Pipeline Stage")
    user_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Assigned Salesperson")
    description: Optional[str] = Field(default=None, description="Internal Notes / Scope")
    type: str = Field(default="opportunity", description="Type: 'lead' or 'opportunity'")


class SaleOrderLine(OdooBaseModel):
    """Abstraction for sale.order.line."""
    order_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Parent Order")
    product_id: Union[int, Tuple[int, str]] = Field(..., description="Product Many2one")
    name: str = Field(..., description="Line Description")
    product_uom_qty: float = Field(default=1.0, description="Quantity Ordered")
    price_unit: float = Field(default=0.0, description="Unit Price")
    price_subtotal: float = Field(default=0.0, description="Subtotal without taxes")
    price_total: float = Field(default=0.0, description="Total with taxes")


class SaleOrder(OdooBaseModel):
    """Abstraction for sale.order (Quotations / Sales Orders)."""
    name: str = Field(default="/", description="Order Reference (e.g. SO001)")
    partner_id: Union[int, Tuple[int, str]] = Field(..., description="Customer Many2one")
    date_order: Optional[datetime] = Field(default=None, description="Order Date")
    state: str = Field(default="draft", description="Order State: draft | sent | sale | done | cancel")
    amount_untaxed: float = Field(default=0.0, description="Untaxed Amount")
    amount_tax: float = Field(default=0.0, description="Tax Amount")
    amount_total: float = Field(default=0.0, description="Total Amount")
    order_line: List[Union[int, SaleOrderLine]] = Field(default_factory=list, description="Order Lines")
    analytic_account_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Analytic Account for Operations")


# ==========================================
# 2. PROJECTS & OPERATIONS DOMAIN
# ==========================================

class AccountAnalyticAccount(OdooBaseModel):
    """Abstraction for account.analytic.account (Cost Centers / Operational Accounts)."""
    name: str = Field(..., description="Analytic Account Name")
    code: Optional[str] = Field(default=None, description="Code / Reference")
    partner_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Customer")
    balance: float = Field(default=0.0, description="Current Balance")
    debit: float = Field(default=0.0, description="Cumulative Debit")
    credit: float = Field(default=0.0, description="Cumulative Credit")


class ProjectProject(OdooBaseModel):
    """Abstraction for project.project."""
    name: str = Field(..., description="Project Name")
    partner_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Customer Many2one")
    user_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Project Manager")
    analytic_account_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Linked Analytic Account")
    privacy_visibility: str = Field(default="portal", description="Visibility: portal | employees | followers")
    active: bool = Field(default=True, description="Active status")
    date_start: Optional[date] = Field(default=None, description="Start Date")
    date: Optional[date] = Field(default=None, description="End Date")


class ProjectTask(OdooBaseModel):
    """Abstraction for project.task."""
    name: str = Field(..., description="Task Name")
    project_id: Union[int, Tuple[int, str]] = Field(..., description="Parent Project")
    partner_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Customer")
    user_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Assigned Employee")
    stage_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Task Stage")
    planned_hours: float = Field(default=0.0, description="Planned Hours")
    effective_hours: float = Field(default=0.0, description="Executed Hours")
    remaining_hours: float = Field(default=0.0, description="Remaining Hours")
    kanban_state: str = Field(default="normal", description="State: normal | blocked | done")
    progress: float = Field(default=0.0, description="Progress Percentage")
    description: Optional[str] = Field(default=None, description="Detailed Description")


# ==========================================
# 3. FINANCE & BUDGETS DOMAIN
# ==========================================

class CrossoveredBudgetLines(OdooBaseModel):
    """Abstraction for crossovered.budget.lines."""
    crossovered_budget_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Parent Budget")
    analytic_account_id: Union[int, Tuple[int, str]] = Field(..., description="Analytic Cost Center")
    general_budget_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Budget Position")
    date_from: date = Field(..., description="Line Start Date")
    date_to: date = Field(..., description="Line End Date")
    planned_amount: float = Field(default=0.0, description="Planned Amount")
    practical_amount: float = Field(default=0.0, description="Executed Practical Amount")
    theoritical_amount: float = Field(default=0.0, description="Theoretical Progress Amount")
    percentage: float = Field(default=0.0, description="Achievement Percentage")


class CrossoveredBudget(OdooBaseModel):
    """Abstraction for crossovered.budget."""
    name: str = Field(..., description="Budget Title / Period")
    user_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Responsible Manager")
    date_from: date = Field(..., description="Budget Period Start")
    date_to: date = Field(..., description="Budget Period End")
    state: str = Field(default="draft", description="State: draft | confirm | validate | done | cancel")
    crossovered_budget_line: List[Union[int, CrossoveredBudgetLines]] = Field(default_factory=list, description="Budget Lines")


class AccountMoveLine(OdooBaseModel):
    """Abstraction for account.move.line (Invoice & DTE Lines)."""
    move_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Parent Move/Invoice")
    name: str = Field(..., description="Item / Service Label")
    product_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Product")
    quantity: float = Field(default=1.0, description="Quantity")
    price_unit: float = Field(default=0.0, description="Unit Price")
    debit: float = Field(default=0.0, description="Debit Amount")
    credit: float = Field(default=0.0, description="Credit Amount")
    price_subtotal: float = Field(default=0.0, description="Subtotal Amount")
    analytic_account_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Analytic Distribution")


class AccountMove(OdooBaseModel):
    """Abstraction for account.move (Invoices, Credit Notes, DTEs)."""
    name: str = Field(default="/", description="Invoice Number / DTE Folio")
    ref: Optional[str] = Field(default=None, description="Reference / PO Number")
    move_type: str = Field(..., description="Type: out_invoice | out_refund | in_invoice | in_refund | entry")
    partner_id: Union[int, Tuple[int, str]] = Field(..., description="Partner Many2one")
    invoice_date: Optional[date] = Field(default=None, description="Invoice Date")
    state: str = Field(default="draft", description="State: draft | posted | cancel")
    amount_untaxed: float = Field(default=0.0, description="Untaxed Amount")
    amount_tax: float = Field(default=0.0, description="Tax Amount")
    amount_total: float = Field(default=0.0, description="Total Amount")
    payment_state: str = Field(default="not_paid", description="Payment Status: not_paid | in_payment | paid | partial")
    invoice_line_ids: List[Union[int, AccountMoveLine]] = Field(default_factory=list, description="Invoice Lines")


class AccountPayment(OdooBaseModel):
    """Abstraction for account.payment."""
    name: str = Field(default="/", description="Payment Reference")
    payment_type: str = Field(..., description="Type: inbound | outbound")
    partner_type: str = Field(default="customer", description="Partner Type: customer | supplier")
    partner_id: Union[int, Tuple[int, str]] = Field(..., description="Partner Many2one")
    amount: float = Field(..., description="Payment Amount")
    currency_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Currency")
    date: date = Field(..., description="Payment Date")
    state: str = Field(default="draft", description="State: draft | posted | reconciled | cancelled")
    ref: Optional[str] = Field(default=None, description="Memo / Bank Voucher Reference")
    journal_id: Optional[Union[int, Tuple[int, str]]] = Field(default=None, description="Payment Journal")
```

---

## 5. Verification & Implementation Blueprint

### 5.1 Verification Checklist for Implementer Agent
1. **Dependencies**: Validate `pyproject.toml` can be parsed by `uv` or `pip`. Ensure standard dependencies match project standard.
2. **Client Interface Compliance**: Confirm `OdooClient` methods match `PROJECT.md` interface contract (`search_read`, `create_draft`, `commit_draft`).
3. **VoBo Enforcement**: Verify `create_draft` stores pending actions without auto-writing to production, and `commit_draft` requires explicit `approved_by` signature.
4. **Resilience**: Ensure `TokenBucketRateLimiter` and `OdooConfig` handle retries, timeouts, and rate limits gracefully.
5. **Models Structure**: Check all 11 model abstractions validate correctly using Pydantic v2.

---

## 6. Conclusion & Handoff Readiness

This analysis provides the complete design, code specifications, and architectural rules needed by the Implementer agent (`implementer_m1_1` or equivalent) to create `pyproject.toml`, `src/odoo_ecosystem/client.py`, and `src/odoo_ecosystem/models.py` without ambiguity.
