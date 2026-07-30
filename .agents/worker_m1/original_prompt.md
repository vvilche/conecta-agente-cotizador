## 2026-07-28T08:00:47Z
You are Worker 1 for Milestone 1 (Odoo Core Connector & Models - `odoo_ecosystem`).
Your working directory is `.agents/worker_m1`. Create `.agents/worker_m1` directory if needed.

Read the specifications and handoffs written by the Explorers:
- `PROJECT.md`
- `.agents/explorer_m1_1/analysis.md`
- `.agents/explorer_m1_1/handoff.md`
- `.agents/explorer_m1_2/analysis.md`
- `.agents/explorer_m1_2/handoff.md`
- `.agents/explorer_m1_3/analysis.md`
- `.agents/explorer_m1_3/handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Create `pyproject.toml` with `pydantic>=2.5.0`, `requests`, `urllib3`, `tenacity`, `pytest`, `pytest-cov`, `pydantic-settings`.
2. Implement `src/odoo_ecosystem/__init__.py`.
3. Implement `src/odoo_ecosystem/models.py` containing Pydantic v2 schemas for all 9 models:
   - `ResPartner`, `CrmLead`, `SaleOrder`, `SaleOrderLine`
   - `ProjectProject`, `ProjectTask`, `AccountAnalyticAccount`
   - `CrossoveredBudget`, `CrossoveredBudgetLines`, `AccountMove`, `AccountMoveLine`, `AccountPayment`
4. Implement `src/odoo_ecosystem/client.py` with multi-protocol support (XML-RPC, JSON-RPC, REST), rate limiting, retries, and draft staging (`search_read`, `create_draft`, `commit_draft`).
5. Implement `src/odoo_ecosystem/mock_server.py` with in-memory database (`MockOdooDB`), domain evaluator, protocol endpoints, and fault injection engine.
6. Implement `src/odoo_ecosystem/audit.py` with `CredentialManager` (masking passwords/keys), `AuditLogger` (JSONL recorder), and `DraftStager`.
7. Implement `tests/conftest.py` and `tests/test_odoo_ecosystem.py` testing all classes, endpoints, validations, errors, retries, and draft workflows.
8. Execute tests using pytest (`pytest tests/test_odoo_ecosystem.py -v`) and verify 100% passing tests and high coverage.

Document all build/test outputs, commands run, test results, and file paths in `.agents/worker_m1/changes.md` and `.agents/worker_m1/handoff.md`.
Send a message back to the main agent when done.
