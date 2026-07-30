## 2026-07-28T12:38:22Z
You are Explorer 3 for Milestone 4 (Supervisor Human-in-the-Loop Web Console), operating in directory `.agents/explorer_m4_3/`.

Your mission:
Design the comprehensive test strategy and test specification for Milestone 4 (`tests/test_supervisor_ui.py`):
1. Unit tests for `SupervisorConsole` queue management and filtering.
2. Unit tests for `approve_draft` workflow: verifying that approving a draft invokes `OdooClient.commit_draft`, mutates Odoo DB, updates draft status to `"approved"`, and creates audit log entry.
3. Unit tests for `reject_draft` workflow: verifying that rejecting a draft prevents Odoo DB mutation, updates status to `"rejected"`, and creates audit log entry.
4. Integration tests for REST API endpoints (`/api/drafts`, `/api/drafts/<id>/approve`, `/api/drafts/<id>/reject`, `/api/audit-logs`).
5. Enforce 0% auto-execution invariant: verify that unapproved drafts in the queue CANNOT affect Odoo DB until explicit VoBo payload signature is passed.

Read `PROJECT.md`, `ORIGINAL_REQUEST.md`, `src/odoo_ecosystem/`, `src/swarm_engine/`, and `tests/`.
Write your test specification to `.agents/explorer_m4_3/analysis.md` and handoff report to `.agents/explorer_m4_3/handoff.md`.
