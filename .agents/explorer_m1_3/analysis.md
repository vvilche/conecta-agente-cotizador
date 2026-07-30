# Test Design Specification: `odoo_ecosystem` (`tests/test_odoo_ecosystem.py`)

## 1. Executive Summary & Objectives
This specification outlines the comprehensive test architecture, verification criteria, assertion strategies, and mock setup fixtures for Milestone 1 (`odoo_ecosystem`).

The test suite ensures 100% robustness across:
1. Multi-protocol Odoo API client (`XML-RPC`, `JSON-RPC`, `REST`).
2. Schema enforcement and validation for all 9 key Odoo models (`res.partner`, `crm.lead`, `sale.order`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `account.move`, `account.payment`).
3. In-memory `MockOdooServer` harness behavior and error injection capabilities.
4. Auto-retry strategies, exponential backoff, rate limiting, and HTTP/RPC error handling.
5. Human-in-the-Loop draft staging (`create_draft`, `commit_draft`).
6. Structured audit logging and credential redaction.

---

## 2. Test Architecture & Directory Layout

The tests for `odoo_ecosystem` will be organized cleanly within `tests/`:

```
tests/
├── conftest.py               # Shared pytest fixtures (MockOdooServer, OdooClient variants, seed data)
├── test_odoo_ecosystem.py    # Main M1 unit & integration test suite
```

---

## 3. Fixture Architecture (`tests/conftest.py`)

### 3.1 Mock Server Fixtures
- **`mock_odoo_server`**: Function/module-scoped instance of `MockOdooServer` pre-populated with standard seed data for all 9 models.
- **`mock_odoo_server_failing`**: A configurable mock server fixture for injecting specific failure modes (e.g., XML-RPC faults, HTTP 429 rate limit, 500 server error, network timeout).

### 3.2 Client Fixtures
- **`odoo_client_xmlrpc`**: `OdooClient` configured to use XML-RPC protocol connected to `mock_odoo_server`.
- **`odoo_client_jsonrpc`**: `OdooClient` configured to use JSON-RPC protocol connected to `mock_odoo_server`.
- **`odoo_client_rest`**: `OdooClient` configured to use REST protocol connected to `mock_odoo_server`.
- **`odoo_client_param`**: Parametrized fixture yielding `OdooClient` instances for all three protocols (`xmlrpc`, `jsonrpc`, `rest`).

### 3.3 Seed Data Fixtures
- `sample_partner_payload`: Valid data dict for `res.partner`.
- `sample_crm_lead_payload`: Valid data dict for `crm.lead`.
- `sample_sale_order_payload`: Valid data dict for `sale.order` with `order_line`.
- `sample_project_payload`: Valid data dict for `project.project`.
- `sample_task_payload`: Valid data dict for `project.task`.
- `sample_analytic_account_payload`: Valid data dict for `account.analytic.account`.
- `sample_budget_payload`: Valid data dict for `crossovered.budget`.
- `sample_account_move_payload`: Valid data dict for `account.move` with `invoice_line_ids`.
- `sample_payment_payload`: Valid data dict for `account.payment`.

---

## 4. Specification of `tests/test_odoo_ecosystem.py`

### 4.1 Suite Organization (Test Classes)

`tests/test_odoo_ecosystem.py` is divided into 7 specialized test classes:

| Class Name | Focus Area | Key Assertions |
|------------|------------|----------------|
| `TestOdooClientAuthentication` | Auth across protocols, invalid credentials, UID caching | Returns valid integer UID; raises `OdooAuthenticationError` on bad creds |
| `TestOdooClientProtocols` | XML-RPC, JSON-RPC, REST dispatch (`search_read`, `create`, `write`, `unlink`) | Correct RPC payload structure, response unwrapping, domain filtering |
| `TestOdooClientDraftWorkflow` | 0% auto-execution draft staging & commit mechanism | `create_draft` returns draft_id without mutating prod table; `commit_draft` validates `approved_by` before write |
| `TestOdooModelValidations` | Schema validation & serialization for all 9 Odoo models | Data type validation, default values, state enums, dict <-> model round-trip |
| `TestMockOdooServer` | In-memory CRUD, domain evaluation logic, state storage | In-memory DB state integrity, filter operator handling (`=`, `!=`, `>`, `<`, `in`) |
| `TestErrorHandlingAndRetries` | Retries, exponential backoff, rate limiting, non-retryable errors | Retry count equals `max_retries`; total sleep time follows backoff formula; non-retryable errors fail fast |
| `TestAuditLogging` | Structured log generation, credential redaction, log retrieval | Logs include `method`, `model`, `latency_ms`; credentials (`password`, `api_key`) masked with `***REDACTED***` |

---

## 5. Detailed Test Method Specifications & Assertion Strategies

### 5.1 `TestOdooClientAuthentication`
1. **`test_successful_authentication`**:
   - Setup: Call `client.authenticate()` with valid credentials.
   - Assert: Returns `uid > 0`, sets `client.uid`.
2. **`test_failed_authentication_invalid_password`**:
   - Setup: Call `client.authenticate()` with wrong password.
   - Assert: Raises `OdooAuthenticationError`, `client.uid is None`.
3. **`test_failed_authentication_invalid_db`**:
   - Setup: Call `client.authenticate()` with non-existent DB.
   - Assert: Raises `OdooDatabaseNotFoundError`.

### 5.2 `TestOdooClientProtocols`
1. **`test_search_read_filtering`** (parametrized by protocol):
   - Setup: Execute `client.search_read('res.partner', domain=[('is_company', '=', True)], fields=['name', 'email'])`.
   - Assert: Returned list contains only partners where `is_company == True`, returned keys match specified fields.
2. **`test_create_record`** (parametrized by protocol):
   - Setup: `client.create('crm.lead', {'name': 'New Opportunity', 'expected_revenue': 50000.0})`.
   - Assert: Returns valid record ID (integer), record exists in mock server DB.
3. **`test_write_record`** (parametrized by protocol):
   - Setup: `client.write('sale.order', [order_id], {'state': 'sent'})`.
   - Assert: Returns `True`, search_read confirms updated state.
4. **`test_unlink_record`** (parametrized by protocol):
   - Setup: `client.unlink('project.task', [task_id])`.
   - Assert: Returns `True`, subsequent `search_read` does not find record.

### 5.3 `TestOdooClientDraftWorkflow`
1. **`test_create_draft_does_not_mutate_production_model`**:
   - Setup: `draft = client.create_draft('account.move', invoice_payload)`.
   - Assert: `draft['draft_id']` is generated string, `draft['status'] == 'pending_vobo'`, `account.move` count in mock server remains unchanged.
2. **`test_commit_draft_with_valid_vobo`**:
   - Setup: `res = client.commit_draft(draft['draft_id'], approved_by='supervisor_admin')`.
   - Assert: `res['status'] == 'committed'`, `res['record_id']` is valid integer, record now exists in `account.move`.
3. **`test_commit_draft_without_approval_fails`**:
   - Setup: `client.commit_draft(draft_id, approved_by='')` or invalid `draft_id`.
   - Assert: Raises `OdooDraftCommitError`.

### 5.4 `TestOdooModelValidations`
Parametrized across all 9 models: `['res.partner', 'crm.lead', 'sale.order', 'project.project', 'project.task', 'account.analytic.account', 'crossovered.budget', 'account.move', 'account.payment']`.
1. **`test_model_instantiation_valid_data`**:
   - Setup: Instantiate model dataclass/Pydantic class with valid payload.
   - Assert: Fields correctly typed, `.to_odoo_dict()` outputs dictionary ready for XML-RPC / JSON-RPC.
2. **`test_model_validation_invalid_enum_state`**:
   - Setup: Pass invalid `state='invalid_state'` to `SaleOrderModel` or `AccountMoveModel`.
   - Assert: Raises `ValidationError`.
3. **`test_model_from_odoo_dict_roundtrip`**:
   - Setup: `model = PartnerModel.from_odoo_dict(raw_odoo_dict)`.
   - Assert: `model.to_odoo_dict()` matches raw dictionary.

### 5.5 `TestMockOdooServer`
1. **`test_mock_server_domain_operators`**:
   - Setup: Query mock server with complex domains `[('amount_total', '>=', 1000), ('state', 'in', ['draft', 'sent'])]`.
   - Assert: Correct matching logic applied.
2. **`test_mock_server_error_injection`**:
   - Setup: `mock_server.inject_error('search_read', error_type='Timeout')`.
   - Assert: Next `search_read` call raises `TimeoutError` / `ConnectionError`.

### 5.6 `TestErrorHandlingAndRetries`
1. **`test_transient_network_failure_retries_and_succeeds`**:
   - Setup: Mock server fails twice with transient network error, succeeds on 3rd attempt.
   - Assert: Client retries twice, succeeds, total call count == 3.
2. **`test_exceeds_max_retries_raises_exception`**:
   - Setup: Server continuously throws 503 Service Unavailable. Configured `max_retries=3`.
   - Assert: Client attempts 3 times, then raises `OdooMaxRetriesExceededError`.
3. **`test_non_retryable_401_fails_immediately`**:
   - Setup: Server returns 401 Unauthorized.
   - Assert: Client fails immediately on 1st attempt, call count == 1.
4. **`test_rate_limit_429_respects_retry_after`**:
   - Setup: Server returns HTTP 429 with `Retry-After: 1`.
   - Assert: Client waits indicated duration and retries.

### 5.7 `TestAuditLogging`
1. **`test_audit_log_captures_all_api_calls`**:
   - Setup: Execute `search_read`, `create_draft`, `commit_draft`.
   - Assert: Audit logger contains 3 entries with corresponding model, method, duration, and status.
2. **`test_audit_log_redacts_sensitive_credentials`**:
   - Setup: Initialize client with `password="secret_pass_123"` and call `authenticate()`.
   - Assert: Log entry does NOT contain `"secret_pass_123"`; contains `"***REDACTED***"`.

---

## 6. Code Skeletons & Implementation Guide for `tests/test_odoo_ecosystem.py`

Below is the design skeleton for `tests/test_odoo_ecosystem.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

# Imports from src.odoo_ecosystem (to be implemented)
# from odoo_ecosystem.client import OdooClient, OdooAuthenticationError, OdooMaxRetriesExceededError
# from odoo_ecosystem.models import PartnerModel, CrmLeadModel, SaleOrderModel, ProjectModel, TaskModel, AnalyticAccountModel, BudgetModel, AccountMoveModel, PaymentModel
# from odoo_ecosystem.mock_server import MockOdooServer
# from odoo_ecosystem.audit import OdooAuditLogger


class TestOdooClientAuthentication:
    """Tests for authentication behavior across protocols."""

    def test_successful_authentication(self, mock_odoo_server):
        # Spec: Authenticate with valid credentials, expect positive integer UID.
        pass

    def test_failed_authentication_invalid_password(self, mock_odoo_server):
        # Spec: Authenticate with bad password, expect OdooAuthenticationError.
        pass

    def test_failed_authentication_invalid_db(self, mock_odoo_server):
        # Spec: Authenticate with non-existent database, expect OdooDatabaseNotFoundError.
        pass


class TestOdooClientProtocols:
    """Tests for XML-RPC, JSON-RPC, and REST protocol execution."""

    @pytest.mark.parametrize("protocol", ["xmlrpc", "jsonrpc", "rest"])
    def test_search_read_filtering(self, protocol, mock_odoo_server):
        # Spec: Verify domain search filtering and field projection across protocols.
        pass

    @pytest.mark.parametrize("protocol", ["xmlrpc", "jsonrpc", "rest"])
    def test_create_record(self, protocol, mock_odoo_server):
        # Spec: Verify record creation across protocols.
        pass

    @pytest.mark.parametrize("protocol", ["xmlrpc", "jsonrpc", "rest"])
    def test_write_record(self, protocol, mock_odoo_server):
        # Spec: Verify record updates across protocols.
        pass

    @pytest.mark.parametrize("protocol", ["xmlrpc", "jsonrpc", "rest"])
    def test_unlink_record(self, protocol, mock_odoo_server):
        # Spec: Verify record deletion across protocols.
        pass


class TestOdooClientDraftWorkflow:
    """Tests for 0% auto-execution draft staging and VoBo commit workflow."""

    def test_create_draft_does_not_mutate_production_model(self, mock_odoo_server):
        # Spec: Draft creation stores payload in staging without writing to Odoo model.
        pass

    def test_commit_draft_with_valid_vobo(self, mock_odoo_server):
        # Spec: Committing draft with valid approval writes to Odoo model and returns ID.
        pass

    def test_commit_draft_without_approval_fails(self, mock_odoo_server):
        # Spec: Attempting to commit draft without user approval raises error.
        pass


class TestOdooModelValidations:
    """Tests for schema validation of all 9 Odoo models."""

    @pytest.mark.parametrize("model_name", [
        "res.partner", "crm.lead", "sale.order",
        "project.project", "project.task", "account.analytic.account",
        "crossovered.budget", "account.move", "account.payment"
    ])
    def test_model_instantiation_valid_data(self, model_name, seed_payloads):
        # Spec: Verify valid payload instantiates correctly and outputs odoo dict.
        pass

    def test_invalid_account_move_type(self):
        # Spec: Verify invalid move_type raises ValidationError.
        pass

    def test_invalid_sale_order_state(self):
        # Spec: Verify invalid sale order state raises ValidationError.
        pass


class TestMockOdooServer:
    """Tests for mock server in-memory database and error injection."""

    def test_mock_server_domain_operators(self, mock_odoo_server):
        # Spec: Test =, !=, >, <, >=, <=, in, not in operators.
        pass

    def test_mock_server_error_injection(self, mock_odoo_server):
        # Spec: Inject artificial errors into mock server and verify client catches them.
        pass


class TestErrorHandlingAndRetries:
    """Tests for retry mechanisms, rate limiting, and exponential backoff."""

    def test_transient_network_failure_retries_and_succeeds(self, mock_odoo_server):
        # Spec: Transient failure succeeds after N retries.
        pass

    def test_exceeds_max_retries_raises_exception(self, mock_odoo_server):
        # Spec: Persistent failure raises max retries exception after max attempts.
        pass

    def test_non_retryable_401_fails_immediately(self, mock_odoo_server):
        # Spec: Auth/Permission errors fail immediately without retry.
        pass


class TestAuditLogging:
    """Tests for structured audit logs and credential protection."""

    def test_audit_log_captures_all_api_calls(self, audit_logger):
        # Spec: All client interactions log timestamp, method, model, latency, status.
        pass

    def test_audit_log_redacts_sensitive_credentials(self, audit_logger):
        # Spec: Ensure passwords and API keys are redacted in audit output.
        pass
```

---

## 7. Verification Method

To independently verify the test suite design once implemented:

1. **Run Unit Tests via Pytest**:
   ```bash
   pytest tests/test_odoo_ecosystem.py -v --tb=short
   ```
2. **Verify Coverage**:
   ```bash
   pytest --cov=src/odoo_ecosystem tests/test_odoo_ecosystem.py --cov-report=term-missing
   ```
   *Criterion*: 100% test pass rate, target line coverage > 90% across `odoo_ecosystem` modules.

3. **Verify Protocol Matrix**:
   Ensure all 3 protocols (XML-RPC, JSON-RPC, REST) and all 9 models pass test assertions without warnings or unhandled exceptions.
