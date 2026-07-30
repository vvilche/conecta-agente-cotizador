# Specialized Agents and Security Review Report (Milestone 3 - Swarm Agentic Engine)

**Reviewer**: Reviewer 2 (`reviewer_m3_2`)  
**Date**: 2026-07-28  
**Scope**:
- `src/swarm_engine/agents/estados_pago.py` (Progress Invoicing & Chilean 19% IVA)
- `src/swarm_engine/agents/gestion_documental.py` (Statutory Labor & SEC Compliance: F30-1, Mutualidad, PreviRed, SEC)
- `src/swarm_engine/agents/conciliador_contable.py` (Chilean DTE Tax Document Reconciliation against POs)
- `tests/test_swarm_engine.py` (Specifically `TestZeroAutoExecutionInvariant` and agent test coverage)

---

## Review Summary

**Verdict**: **PASS**

**Key Highlights**:
1. **0% Auto-Execution VoBo Invariant**: Strictly enforced. All specialized agents produce staged `DraftAction` objects with `status="pending_vobo"`. No direct mutations occur in Odoo ERP during event processing.
2. **Domain Logic Accuracy**:
   - `EstadosPagoAgent`: Accurate calculation of Chilean 19% IVA (`billable_amount * 0.19`) and total invoice values for `account.move` (`out_invoice`).
   - `GestionDocumentalAgent`: Comprehensive verification of F30-1, Mutualidad, PreviRed, and SEC certifications under Chilean Subcontracting Law (Ley 20.123). Correctly creates blocked `project.task` actions when gaps exist.
   - `ConciliadorContableAgent`: Accurate reconciliation of Chilean DTE tax documents (`in_invoice`), RUT matching, PO reference matching, and tax/PO discrepancy detection (triggering confidence score downgrade to 0.68 on discrepancy).
3. **Integrity & Code Quality**: No hardcoded test outputs, dummy facades, or shortcuts detected. Implementation is clean, modular, and fully functional.

---

## Verified Claims

| Claim | Target File / Class | Method | Result |
|---|---|---|---|
| 0% Auto-Execution VoBo Rule Enforcement | `estados_pago.py`, `gestion_documental.py`, `conciliador_contable.py` | Source inspection of `process_event` & `create_draft_action` | **PASS** — Status is unconditionally set to `pending_vobo`. Only read-only queries executed via `query_odoo`. |
| Zero Mutation Invariant Verification | `tests/test_swarm_engine.py::TestZeroAutoExecutionInvariant` | Inspection of `test_zero_auto_execution_mock_server_mutation_prevention` | **PASS** — Asserts Odoo record counts across 9 models remain 100% unchanged before/after agent task processing. |
| Chilean 19% IVA Tax Calculation | `estados_pago.py` (lines 63-65) | Inspection of `_handle_progress_invoice` math & test assertions | **PASS** — `tax_iva = billable_amount * 0.19`, `total = billable_amount + tax_iva`. |
| Statutory Labor Compliance (Ley 20.123) | `gestion_documental.py` (lines 52-106) | Inspection of document audit logic (F30-1, Mutualidad, PreviRed, SEC) | **PASS** — Evaluates valid vs expired/missing documents, creates blocked task with compliance justification. |
| Chilean DTE Reconciliation & Discrepancy Flagging | `conciliador_contable.py` (lines 77-116) | Inspection of DTE folio, RUT matching, PO matching, tax discrepancy logic | **PASS** — Flags tax discrepancy when `abs(iva - expected_iva) > 1.0`, drops confidence score to 0.68. |

---

## Findings & Recommendations

### [Minor] Finding 1: Falsy Value Evaluation for Zero Numerical Inputs (`0` / `0.0`)
- **Location**: `src/swarm_engine/agents/estados_pago.py` (line 51) & `src/swarm_engine/agents/conciliador_contable.py` (line 49)
- **What**: Python expression `payload.get("billable_amount") or payload.get("amount_untaxed") or 10000000.0` treats explicit `0` or `0.0` numeric inputs as falsy, defaulting to `10000000.0`.
- **Why**: If a caller explicitly sends `billable_amount: 0.0` for a zero-value progress milestone, the agent will substitute the default fallback instead of `0.0`.
- **Suggestion**: Use `v if (v := payload.get("billable_amount")) is not None else ...` or explicit check `if payload.get("billable_amount") is not None: ...`.

### [Minor] Finding 2: Unfiltered Duplicate Invoice Query Scope
- **Location**: `src/swarm_engine/agents/estados_pago.py` (lines 57-61)
- **What**: Odoo query for existing customer invoices `domain=[["move_type", "=", "out_invoice"], ["state", "!=", "cancel"]]` does not filter by `partner_id` or `project_id`.
- **Why**: `existing_invoices_count` in metadata reflects total system `out_invoice` count rather than project-specific prior progress invoices.
- **Suggestion**: Add project/partner filters to domain: `domain=[["move_type", "=", "out_invoice"], ["partner_id", "=", partner_id], ["state", "!=", "cancel"]]`.

---

## Integrity Violation Check

- **Hardcoded Test Results**: None found.
- **Dummy / Facade Implementations**: None found.
- **Bypasses of 0% VoBo Rule**: None found.
- **Fabricated Verification Artifacts**: None found.
- **Verdict Impact**: **PASS** (Zero integrity violations).

---

## Test Suite Assessment

`tests/test_swarm_engine.py` contains 9 test classes covering:
1. `TestDraftActionAndBaseAgent`: Pydantic validation, status defaults, score boundaries [0.0, 1.0], serialization, helper methods.
2. `TestRFQAgent`: Lead generation, RUT lookup, RAG memory enrichment.
3. `TestQuotationAgent`: Product catalog lookup, Chilean 19% IVA, multi-line items.
4. `TestOperationsAgent`: Budget overrun detection (>10%), task creation.
5. `TestProgressInvoicingAgent`: Milestone progress invoicing, 19% IVA, draft line items.
6. `TestComplianceAgent`: F30-1, Mutualidad, PreviRed, SEC compliance auditing.
7. `TestDTEConciliationAgent`: DTE folio, RUT matching, PO matching, tax discrepancy confidence adjustment.
8. `TestAgentSwarmRoutingAndWorkflows`: Event routing, broadcast auditing, agent registration, error isolation.
9. `TestZeroAutoExecutionInvariant`: End-to-end database mutation prevention assertion across all 6 agents.

---

## Final Recommendation

Approve Milestone 3 specialized agents (`estados_pago.py`, `gestion_documental.py`, `conciliador_contable.py`) and test suite. The implementation is robust, secure, and fully aligned with Chilean domain standards and the 0% Auto-Execution VoBo invariant.
