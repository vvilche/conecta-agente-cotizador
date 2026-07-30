## 2026-07-29T23:12:26Z
You are a Reviewer subagent for Milestone 2 (Core Operations Package & Financial Engine Review - Independent Verification).
Your working directory is `.agents/teamwork_preview_reviewer_m2_2/`. Create this directory if needed and write your review handoff report to `.agents/teamwork_preview_reviewer_m2_2/handoff.md`.

Task Instructions:
1. Conduct an independent, rigorous code review of `src/operations/` (`financial_engine.py`, `doc_automator.py`, `fat_sat_simulator.py`, `kitting_engine.py`, `accreditation_automator.py`, `payment_statement_automator.py`, `__init__.py`) and `tests/test_operations_engine.py`.
2. Check for edge cases, missing assertions, type hints, error handling, boundary values, and integration capability with Odoo models and supervisor UI.
3. Execute test commands (`pytest tests/test_operations_engine.py`) via run_command to independently verify all tests pass with 0 errors.
4. Report your independent review verdict (PASS/FAIL with detailed analysis) in `.agents/teamwork_preview_reviewer_m2_2/handoff.md` and send a summary message to orchestrator.
