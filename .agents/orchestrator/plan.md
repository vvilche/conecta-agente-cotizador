# Master Orchestration Plan — Audit & Document Format Standardization

## Mission
Audit and standardize all generated project documents (Word .docx proposals, Excel .xlsx 9-sheet workbooks, PDF technical reports) to ensure 100% fidelity to historical Conecta S.A. project standards (`ot_7000` / `ot_8000_smart_extracted`), support voltage rating filtering and Spanish number word parsing, provide dynamic configurable target gross margin (10.0% to 85.0%), and achieve 300+ passing pytest tests with zero broken contracts and clean forensic audit.

## Milestones & Work Breakdown Structure

| Milestone | Task Description | Primary Deliverable | Target Agents | Status |
|-----------|------------------|---------------------|---------------|--------|
| M1 | Deep Audit & Gap Analysis of Document Generators & Test Suite | Gap analysis reports for Word builder, Excel builder, UI margin config, and test suite | 3 Explorers | IN_PROGRESS |
| M2 | Word Quotation Builder & Quantity Parser Standardization | `src/operations/official_word_quote_builder.py` & quantity parser updated with 6 headings, metadata block, table formatting, voltage filtering, Spanish words | Worker + 2 Reviewers | PLANNED |
| M3 | Excel 9-Sheet BOM Builder & Dynamic Gross Margin Standardization | `src/operations/bom_excel_builder.py` updated with all 9 sheets, formulas, cash flow, risk matrix, margin sensitivity + UI/Engine dynamic margin (10.0%-85.0%) | Worker + 2 Reviewers | PLANNED |
| M4 | Comprehensive Test Hardening (300+ Pytest Suite) | Comprehensive test suite in `tests/` with 300+ passing tests, 0 failures, 100% contract compliance | Worker + Challenger + Reviewer | PLANNED |
| M5 | Forensic Integrity Audit & Sentinel Handoff | Forensic audit report (CLEAN verdict) + Executive summary of document standardization | Auditor | PLANNED |

## Quality Gate & Verification Standards
- Word .docx: valid 6 official sections, metadata block, summary table, CLP/USD prices.
- Excel .xlsx: valid 9 official worksheets, non-zero formulas, cash flow, margin sensitivity, risk matrix.
- Quantity parser: filters `220kV`/`110kV` voltage ratings and parses Spanish words (`una PMU` -> 1).
- Dynamic Margin: 10.0% to 85.0% dynamically configurable via UI/Engine.
- Pytest: 300+ tests passing 100% with 0 failures.
- Audit: Forensic Auditor CLEAN verdict (zero facade/mock cheating).
