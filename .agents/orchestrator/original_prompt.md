## 2026-07-30T03:07:05Z

You are the PROJECT ORCHESTRATOR. Your working directory is `.agents/orchestrator`.

Your mission is to orchestrate and execute the complete implementation of the operational automation software package for Conecta Ingeniería S.A. as detailed in ORIGINAL_REQUEST.md.

Project Scope & Requirements:
1. R1: Operational Automations Package in `src/operations/`:
   - DocAutomator: Generates Fichas de Traspaso, Protocolos AT-SITR-1, and IPES reports (PDF/DOCX) in ~3 seconds.
   - FatSatSimulator: Laboratory testbed with HIL simulation for DNP3/C37.118 telemetries validation.
   - KittingEngine: Standardized assembly motor for PMU and RTU SCADA kits pre-wired in workshop.
   - AccreditationAutomator: Auto-compiler of digital accreditation dossiers (F30-1, contracts, medical ex, EPP, ODI/DAS) for express site access (Sicop/Pronexo/RyS).
   - PaymentStatementAutomator: Instant generator of Payment Statements with signed FAT/SAT certificate attached for Odoo billing triggering.
2. R2: Profitability Matrix & Financial Impact Engine:
   - Calculates released man-hours, reduced field days, and internal gross margin retained (54.8%).
3. R3: Integrated Supervision Console in `src/supervisor_ui/app.py`:
   - Interactively audit and execute all automations with test controls.
4. Acceptance Criteria:
   - 100% operational modules in `src/operations/`.
   - Test suite in `tests/` with 200+ pytest tests passing 100% with 0 errors.
   - UI in `src/supervisor_ui/app.py` functioning for all automations.
   - Executive report in Markdown generated for the operations team.

Instructions:
1. Initialize `.agents/orchestrator/plan.md` and `.agents/orchestrator/progress.md`.
2. Spawn worker/specialist subagents to analyze existing code and implement the core python modules, financial matrix, UI, and test suite.
3. Keep `.agents/orchestrator/progress.md` updated at every milestone completion.
4. When all tasks and acceptance criteria pass, report completion to Sentinel.
