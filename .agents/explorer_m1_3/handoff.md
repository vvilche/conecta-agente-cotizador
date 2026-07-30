# Handoff Report: Explorer M1-3 — Test Suite Design Specification for `odoo_ecosystem`

## 1. Observation
- Workspace state: `PROJECT.md`, `ORIGINAL_REQUEST.md`, and `.agents/orchestrator/plan.md` defined Milestone 1 (`odoo_ecosystem`) requirements.
- Core target module components to be tested:
  - `src/odoo_ecosystem/client.py`: Multi-protocol client (`XML-RPC`, `JSON-RPC`, `REST`), `create_draft`, `commit_draft`, retry strategy, rate limiting.
  - `src/odoo_ecosystem/models.py`: 9 Odoo model abstractions (`res.partner`, `crm.lead`, `sale.order`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `account.move`, `account.payment`).
  - `src/odoo_ecosystem/mock_server.py`: In-memory `MockOdooServer` harness with domain filtering and error injection.
  - `src/odoo_ecosystem/audit.py`: `OdooAuditLogger` with credential redaction.
- Test destination: `tests/test_odoo_ecosystem.py` and `tests/conftest.py`.

## 2. Logic Chain
1. **Target Identification**: Milestone 1 defines an ecosystem connector wrapper interacting with Odoo. Testing must cover all 3 protocols (XML-RPC, JSON-RPC, REST) and all 9 Odoo models.
2. **Draft Staging Enforcement**: The system enforces a strict 0% auto-execution policy. `OdooClient` must support staged creation (`create_draft`) and explicit Human-in-the-Loop approval before commit (`commit_draft`). The test suite structure must specifically assert this boundary condition (`TestOdooClientDraftWorkflow`).
3. **Resilience & Fault Tolerance**: Network operations against Odoo are susceptible to latency, rate limiting (HTTP 429), transient 5xx errors, and credential failures. `TestErrorHandlingAndRetries` ensures exponential backoff and fast-fail behavior on 401/403.
4. **Data Contract Security & Auditing**: Credentials must be redacted in logs. `TestAuditLogging` verifies that passwords and API keys are masked as `***REDACTED***`.
5. **Mock Server Strategy**: Dependencies on external live Odoo instances during unit/integration tests must be avoided. `MockOdooServer` in `conftest.py` provides deterministic, fast, in-memory execution.

## 3. Caveats
- `src/odoo_ecosystem/` source code is planned for implementation by parallel implementer subagents (Implementer 1, 2, 3). The test suite structure defined here assumes standard exception naming (`OdooAuthenticationError`, `OdooDraftCommitError`, `OdooMaxRetriesExceededError`, `ValidationError`) which should be imported by `tests/test_odoo_ecosystem.py`.
- No live network calls are made during tests; all protocol handlers interact with `MockOdooServer`.

## 4. Conclusion
The detailed test design specification for `tests/test_odoo_ecosystem.py` is fully documented in `.agents/explorer_m1_3/analysis.md`. The design comprises 7 specialized test classes covering authentication, protocol dispatch, 0% auto-execution draft workflows, 9 model schema validations, mock server domain evaluation, error retries, and credential-safe audit logging.

## 5. Verification Method
1. **Inspect Specification Files**:
   - `analysis.md`: Detailed test architecture, fixture declarations, test class layout, and code skeletons.
   - `handoff.md`: Handoff report and logic chain.
2. **Execute Pytest once M1 code is created**:
   ```bash
   pytest tests/test_odoo_ecosystem.py -v
   pytest --cov=src/odoo_ecosystem tests/test_odoo_ecosystem.py --cov-report=term-missing
   ```
