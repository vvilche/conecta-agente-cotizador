## 2026-07-28T08:34:08-04:00
You are Reviewer 2 for Milestone 3 (Swarm Agentic Engine), operating in directory `.agents/reviewer_m3_2/`.

Your mission is to perform a comprehensive specialized agents and security review of:
- `src/swarm_engine/agents/estados_pago.py` (progress invoicing, Chilean 19% IVA)
- `src/swarm_engine/agents/gestion_documental.py` (statutory labor compliance: F30-1, Mutualidad, PreviRed, SEC)
- `src/swarm_engine/agents/conciliador_contable.py` (Chilean DTE tax document reconciliation against POs)
- `tests/test_swarm_engine.py` (specifically `TestZeroAutoExecutionInvariant`)

Inspect code for:
1. Strict enforcement of the 0% Auto-Execution VoBo rule across all agents (verifying no direct DB mutations occur without VoBo approval).
2. Domain logic accuracy for Chilean progress billing (IVA calculation), labor compliance checks, and DTE tax reconciliation.
3. Exception safety, missing field handling, and data sanitization.
4. Run `pytest tests/test_swarm_engine.py -v` and `pytest -v`.

Write your review report to `.agents/reviewer_m3_2/review.md` with explicit findings and final verdict (**PASS** or **REQUEST_CHANGES**).
