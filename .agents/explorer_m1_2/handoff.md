# Handoff Report: Odoo Mock Server Harness & Audit Engine Specification (Milestone 1)

## 1. Observation
- Target module paths specified in `PROJECT.md` line 47-48:
  - `src/odoo_ecosystem/mock_server.py`
  - `src/odoo_ecosystem/audit.py`
- Target interface contracts defined in `PROJECT.md` lines 22-26:
  - `OdooClient.search_read(model: str, domain: list, fields: list) -> list[dict]`
  - `OdooClient.create_draft(model: str, values: dict) -> dict`
  - `OdooClient.commit_draft(draft_id: str, approved_by: str) -> dict`
- Requirements for R1 in `ORIGINAL_REQUEST.md` lines 10-15:
  - Model abstractions for: `res.partner`, `crm.lead`, `sale.order`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `account.move`, `account.payment`.
  - XML-RPC / JSON-RPC / REST compatibility across Odoo 14, 15, 16, 17.
  - Staging/dev support, credential security, retries, and API audit log recorder.
- 0% Auto-execution rule defined in `PROJECT.md` line 9 & `ORIGINAL_REQUEST.md` line 30.

## 2. Logic Chain
1. **Observation 1** establishes the requirement for `mock_server.py` and `audit.py` in `src/odoo_ecosystem/`.
2. **Observation 2 & 3** define the mandatory support for 9 Odoo core operational models (`res.partner`, `crm.lead`, `sale.order`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `account.move`, `account.payment`) across versions 14, 15, 16, and 17.
3. Therefore, `mock_server.py` must include an in-memory database (`MockOdooDB`) pre-seeded with valid record fixtures for all 9 models, an Odoo Polish notation domain evaluator (`DomainEvaluator`), and protocol endpoints for XML-RPC, JSON-RPC, and REST (Odoo 17).
4. Furthermore, testing resilience against real-world Odoo API failures requires `mock_server.py` to provide a controllable fault injection engine (`FaultInjectionConfig`) capable of simulating rate limits (429), auth failures (401/AccessDenied), server errors (500), and network timeouts.
5. **Observation 4** mandates strict 0% auto-execution for write operations. Therefore, `audit.py` must implement `DraftStager` to record proposed mutations as `PENDING_APPROVAL` drafts without directly writing to Odoo until explicit VoBo confirmation.
6. In addition, `audit.py` requires a security credential manager (`CredentialManager`) with Vault/ENV resolution and automatic password/API key masking (`mask_sensitive_data`), as well as a JSONL API audit recorder (`AuditLogger`).

## 3. Caveats
- No external network access is available in the current execution mode (CODE_ONLY). Tests and mock server operations run strictly locally via in-memory adapter or `127.0.0.1` stdlib HTTP server.
- Odoo 17 REST API specs are based on standard Odoo v17 community/enterprise web controllers and standard JSON/REST interfaces.
- Custom Odoo third-party modules beyond the 9 standard models specified in `PROJECT.md` are out of scope for Milestone 1.

## 4. Conclusion
The design specifications detailed in `.agents/explorer_m1_2/analysis.md` provide a complete blueprint for `src/odoo_ecosystem/mock_server.py` and `src/odoo_ecosystem/audit.py`. The design guarantees:
- Compatibility across Odoo versions 14, 15, 16, and 17 over XML-RPC, JSON-RPC, and REST.
- Domain filter parsing for complex logical domains (`&`, `|`, `!`, `=`, `!=`, `>`, `<`, `in`, `ilike`).
- Pre-seeded in-memory mock database for all 9 target models.
- Controllable error simulation (429 Rate Limit, Auth Failure, Timeout, Server Error).
- Credential protection with redaction/masking and Vault interface.
- 0% auto-execution compliance via `DraftStager` and structured JSONL API audit log recording.

## 5. Verification Method
1. **File Inspection**:
   - Inspect `.agents/explorer_m1_2/analysis.md` to review full class interfaces, domain parsing algorithm, fault injection configuration, audit log schema, and draft staging workflow.
2. **Pytest Verification (after implementation by Implementer)**:
   - Run `pytest tests/test_odoo_ecosystem.py -k "mock_server or audit"`
   - Confirm test coverage across XML-RPC, JSON-RPC, REST, domain filtering, error injection, secret redaction, audit logging, and draft staging.
3. **Invalidation Conditions**:
   - If domain filtering fails to evaluate logical OR (`|`) or substring match (`ilike`).
   - If sensitive credentials (e.g. `password` or `api_key`) appear unmasked in JSONL audit logs.
   - If write operations (`create`, `write`, `unlink`) bypass draft staging and execute automatically without VoBo token approval.
