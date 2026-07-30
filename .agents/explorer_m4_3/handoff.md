# Handoff Report: Milestone 4 Test Strategy & Specification (`tests/test_supervisor_ui.py`)

**Agent**: Explorer 3 (Milestone 4)  
**Working Directory**: `.agents/explorer_m4_3/`  
**Target Specification File**: `.agents/explorer_m4_3/analysis.md`  
**Target Output File**: `tests/test_supervisor_ui.py`  

---

## 1. Observation

Direct observations and evidence collected during analysis:
- **Repository Structure & Existing Tests**:
  - `src/odoo_ecosystem/client.py`: Implements `OdooClient.create_draft(...)` and `OdooClient.commit_draft(draft_id, approved_by)` requiring explicit `approved_by` signature. Lines 370–419.
  - `src/odoo_ecosystem/audit.py`: Implements `DraftStager`, `DraftRecord`, `AuditLogger`, `mask_sensitive_data`. Lines 65–207.
  - `src/swarm_engine/base_agent.py`: Defines `DraftAction` Pydantic v2 schema with default `status="pending_vobo"`. Lines 19–77.
  - `src/swarm_engine/swarm.py`: Implements `AgentSwarm.process_task` and `dispatch_event`. Lines 137–183.
  - Existing pytest test suites: `tests/conftest.py` (provides `MockOdooServer`), `tests/test_odoo_ecosystem.py`, `tests/test_rag_memory.py`, `tests/test_swarm_engine.py`.
- **Architectural Design for Milestone 4 (Supervisor UI)**:
  - `src/supervisor_ui/audit_logger.py`: `SupervisorAuditEntry` dataclass and `SupervisorAuditLogger` class for immutable JSONL recording of supervisor VoBo actions (`approved`, `rejected`).
  - `src/supervisor_ui/console.py`: `SupervisorConsole` engine for pending draft queue state management, `get_pending_drafts`, `approve_draft`, `reject_draft`, `get_stats`.
  - `src/supervisor_ui/app.py`: REST API app serving `/api/drafts`, `/api/drafts/<id>`, `/api/drafts/<id>/approve`, `/api/drafts/<id>/reject`, `/api/audit-logs`, `/api/stats`.

---

## 2. Logic Chain

1. **Safety Contract & Invariant**:
   - The primary requirement of Milestone 4 is enforcing the 0% auto-execution rule. Specialized agents produce `DraftAction` objects that default to `status="pending_vobo"`.
   - Staging these actions in `SupervisorConsole` queue must NOT cause any mutation in `MockOdooServer` or Odoo ERP.
2. **Approval Workflow (`approve_draft`)**:
   - Calling `approve_draft(draft_id, supervisor_id, justification)` verifies that the draft is currently `"pending_vobo"`.
   - If valid, it invokes `OdooClient.create` / `commit_draft`, which writes the record to Odoo ERP and returns `odoo_record_id`.
   - The draft status updates to `"committed"` (or `"approved"`), and a record is added to `SupervisorAuditLogger` containing the supervisor ID, verdict `"approved"`, target model, and record ID.
3. **Rejection Workflow (`reject_draft`)**:
   - Calling `reject_draft(draft_id, supervisor_id, reason)` updates status to `"rejected"`.
   - `OdooClient` write methods are NEVER called, guaranteeing 0% database mutation.
   - An entry is logged in `SupervisorAuditLogger` with verdict `"rejected"`, `odoo_record_id=None`, and rejection reason.
4. **REST API Endpoints Integration**:
   - Endpoints in `src/supervisor_ui/app.py` delegate request handling to `SupervisorConsole`.
   - `GET /api/drafts` filters queue by `agent` and `status`.
   - `POST /api/drafts/<id>/approve` and `POST /api/drafts/<id>/reject` accept JSON payloads containing `supervisor_id` and justification/reason, returning structured HTTP responses (200, 400, 404).
5. **Test Specification Architecture**:
   - `tests/test_supervisor_ui.py` is structured into 6 focused test classes:
     - `TestSupervisorConsoleQueue`
     - `TestApproveDraftWorkflow`
     - `TestRejectDraftWorkflow`
     - `TestSupervisorRESTAPI`
     - `TestZeroAutoExecutionInvariantM4`
     - Pytest fixtures (`mock_odoo_server`, `odoo_client`, `temp_audit_logger`, `supervisor_console`, `sample_drafts`, `api_test_client`).

---

## 3. Caveats

- **Decoupled Execution Mode**: `SupervisorConsole` supports running either with an active `OdooClient` or in decoupled standalone mode (`odoo_client=None`). Test cases explicitly cover both modes (returning `"committed"` with `odoo_record_id` when connected vs `"approved"` with `odoo_record_id=None` when decoupled).
- **Web Server Framework**: The integration test specification uses Flask's `app.test_client()` assuming `src/supervisor_ui/app.py` is built using Flask (as specified in sibling specs). If FastAPI or standard library `http.server` is selected by the implementer, the test client wrapper in `api_test_client` fixture should be adapted accordingly.
- **Read-Only Scope**: Explorer 3 operates strictly in read-only analysis mode. The actual file `tests/test_supervisor_ui.py` and `src/supervisor_ui/` will be instantiated by worker/implementer agents based on `analysis.md`.

---

## 4. Conclusion

A comprehensive, production-ready test specification for `tests/test_supervisor_ui.py` has been designed and documented in `.agents/explorer_m4_3/analysis.md`. It provides complete coverage across queue management, approval and rejection workflows, Supervisor Audit Logger persistence, REST API integration, adversarial edge cases, and empirical enforcement of the 0% auto-execution invariant.

---

## 5. Verification Method

To independently verify the test specification and subsequent implementation:

1. **Inspect Analysis Specification**:
   - Inspect `.agents/explorer_m4_3/analysis.md` for completeness and code accuracy.
2. **Execute Pytest Test Suite** (once `src/supervisor_ui/` and `tests/test_supervisor_ui.py` are written):
   ```bash
   pytest tests/test_supervisor_ui.py -v
   ```
3. **Check Test Coverage**:
   ```bash
   pytest --cov=src/supervisor_ui tests/test_supervisor_ui.py
   ```
4. **Invalidation Conditions**:
   - Any test failure where an unapproved draft mutates Odoo DB prior to VoBo approval signature.
   - Any failure to log supervisor approval or rejection in `SupervisorAuditLogger`.
   - Any unhandled exception during REST API endpoint filtering or payload submission.
