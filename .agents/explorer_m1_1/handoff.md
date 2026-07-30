# Handoff Report: Odoo Core Connector & Models (`odoo_ecosystem`)

**Milestone**: Milestone 1 (Odoo Core Connector & Models - odoo_ecosystem)  
**Agent**: Explorer 1 (`.agents/explorer_m1_1`)  
**Date**: 2026-07-28  

---

## 1. Observation

- **Project Specification**: `PROJECT.md` defines `odoo_ecosystem/` as the Core Module for XML-RPC / JSON-RPC / REST connectivity and abstraction layer for 9 base domain models (`res.partner`, `crm.lead`, `sale.order`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `account.move`, `account.payment`).
- **Required Interface Contracts**:
  1. `OdooClient.search_read(model: str, domain: list, fields: list) -> list[dict]`
  2. `OdooClient.create_draft(model: str, values: dict) -> dict` (Staged creation, returns draft payload ID)
  3. `OdooClient.commit_draft(draft_id: str, approved_by: str) -> dict` (Executed strictly upon VoBo approval)
- **Directory Structure Requirement**:
  - `pyproject.toml`
  - `src/odoo_ecosystem/client.py`
  - `src/odoo_ecosystem/models.py`
  - `src/odoo_ecosystem/mock_server.py`
  - `src/odoo_ecosystem/audit.py`
  - `tests/test_odoo_ecosystem.py`

---

## 2. Logic Chain

1. **Requirement Mapping**:
   - `pyproject.toml` needs `pydantic>=2.5.0`, `pydantic-settings>=2.1.0`, `requests`, `urllib3`, `tenacity`, and `pytest` stack to fulfill validation, settings configuration, multi-protocol HTTP/RPC calls, exponential backoff retries, and unit testing.
2. **Client Architecture (`client.py`)**:
   - Must encapsulate XML-RPC (`/xmlrpc/2/common` & `/xmlrpc/2/object`) and JSON-RPC (`/jsonrpc`) protocols behind a unified `OdooClient` class.
   - Must enforce 0% auto-execution by routing mutation requests through `create_draft(model, values)` (staging pending drafts with unique IDs) and committing via `commit_draft(draft_id, approved_by)` only upon explicit VoBo authorization.
   - Resilience is guaranteed by a thread-safe `TokenBucketRateLimiter` and `tenacity` retry wrappers.
3. **Pydantic Model Layer (`models.py`)**:
   - Standardizes Odoo's dynamic typing (such as Many2one tuples `[id, name]` vs integers and One2many lists) into clean Pydantic v2 schemas across 3 key operational domains:
     - **CRM & Sales**: `ResPartner`, `CrmLead`, `SaleOrder`, `SaleOrderLine`
     - **Projects & Operations**: `ProjectProject`, `ProjectTask`, `AccountAnalyticAccount`
     - **Finance & Budgets**: `CrossoveredBudget`, `CrossoveredBudgetLines`, `AccountMove`, `AccountMoveLine`, `AccountPayment`

---

## 3. Caveats

- **Odoo Version Differences**: Field names in Odoo 15, 16, and 17 are largely consistent for core modules (`crm.lead`, `sale.order`, `project.task`, `account.move`), but custom modules (e.g. `crossovered.budget`) require `account_budget` addon installed in Odoo enterprise/community setups.
- **REST Protocol**: Odoo standard core uses XML-RPC/JSON-RPC natively. REST endpoints depend on third-party modules or API gateways; client design includes fallback wrappers for REST endpoints.
- **Mock Server Harness**: Mock server harness will be implemented by peer/implementer in `src/odoo_ecosystem/mock_server.py` using `pytest-mock` or lightweight `http.server` for unit test isolation.

---

## 4. Conclusion

The technical design specification for Milestone 1 (`odoo_ecosystem`) is complete, fully specified in `.agents/explorer_m1_1/analysis.md`, and ready for immediate implementation by the implementer agent.

---

## 5. Verification Method

To verify the implementation once completed by the implementer:
1. **File Existence & Layout**:
   - Confirm `pyproject.toml`, `src/odoo_ecosystem/client.py`, and `src/odoo_ecosystem/models.py` exist in target paths matching `PROJECT.md`.
2. **Package & Syntax Check**:
   - Run `python -m py_compile src/odoo_ecosystem/client.py src/odoo_ecosystem/models.py`.
3. **Pydantic Model Verification**:
   - Instantiate each Pydantic model with test payloads in Python REPL or `pytest`.
4. **Interface Contract Verification**:
   - Verify `OdooClient` exposes `.search_read()`, `.create_draft()`, and `.commit_draft()` with identical signatures.
