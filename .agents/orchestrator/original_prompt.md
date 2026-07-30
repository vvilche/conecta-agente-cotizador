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

## 2026-07-30T17:00:04Z

Goal: Audit and standardize file structures, Word/Excel document generators, and folder mappings across Commercial & Operations modules.

Audit and standardize all generated project documents (Word .docx proposals, Excel .xlsx 9-sheet workbooks, PDF technical reports) to ensure 100% fidelity to historical Conecta S.A. project standards (`ot_7000` / `ot_8000_smart_extracted`).

Requirements:
R1. Word Quote Builder Standardization (`official_word_quote_builder.py`)
Ensure Word documents generated for quotations follow the exact corporate template of Conecta S.A.:
- Professional cover & metadata block: Reference number (`260730 Rev 0`), Date (`Santiago, 30 de Julio de 2026`), Client name, Subject.
- Official Headings:
  1. `DETALLE DE LOS SUMINISTROS Y SERVICIOS`
  2. `DETALLE DE PRECIO OFERTA BASE`
  3. `EXCLUSIONES DE LA OFERTA`
  4. `VALIDEZ DE LA OFERTA`
  5. `CONDICIONES DE PAGO`
  6. `TÉRMINOS Y CONDICIONES (T&C)`
- Properly formatted summary table with item codes, descriptions, quantities, unit prices in CLP/USD, and net totals.

R2. Excel 9-Sheet BOM Builder Standardization (`bom_excel_builder.py`)
Ensure Excel workbooks generated for projects populate all 9 official Conecta worksheets:
1. `Ficha`: Transpaso OT Metadata.
2. `Resumen`: Net sales, 19% IVA, Total gross, Target Gross Margin %.
3. `Control HH y Costos`: Man-hours matrix by activity (Planificación, Ingeniería, Pruebas HIL FAT, SAT Terreno).
4. `Equi. Mat. Arr. Sub.`: Hardware, Materials, Equipment Rentals, Subcontracts.
5. `Cash Flow`: Milestone billing (EDP 1 Pre-kitting 50%, EDP 2 SAT HIL 50%).
6. `Cliente`: Client corporate metadata.
7. `Expenses y Logistica`: Travel, 4x4 trucks, Sicop/Pronexo accreditation.
8. `Terminos de Pago`: Payment terms, performance bonds, warranty.
9. `Check y Sensibilidad`: Financial margin sensitivity (30% - 68.5%) and risk matrix.

R3. Automated Test Suite & Audit Integrity
Verify that all 302+ automated unit & integration tests in `pytest` pass with 100% coverage and zero broken contracts.

Acceptance Criteria:
- Word quotation builder generates valid `.docx` files conforming to Conecta's 6 official sections.
- Multi-tab Excel builder generates valid `.xlsx` files with all 9 sheets populated and non-zero formulas.
- Quantity parser correctly filters voltage ratings (`220kV`, `110kV`) and parses Spanish number words (`una PMU` -> 1).
- Target Gross Margin % is dynamically configurable from UI (10.0% to 85.0%).
- Pytest suite executes cleanly with 300+ passing tests and 0 failures.
