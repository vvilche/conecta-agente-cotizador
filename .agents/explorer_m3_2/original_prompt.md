## 2026-07-28T08:27:38Z
You are Explorer 2 for Milestone 3 (Swarm Agentic Engine), operating in directory `.agents/explorer_m3_2/`.

Your mission:
Analyze and design the 6 Specialized Agents (`src/swarm_engine/agents/`):
1. `rfq_prospeccion.py`: RFQ & Commercial Prospecting Agent (`res.partner`, `crm.lead`, `sale.order`). Integrates with `HistoricalMemory` for winning proposal few-shot prompt context.
2. `cotizacion_inventario.py`: Quotation & Inventory Matching Agent (`product.product`, `sale.order`). Matches requirements to inventory items, calculates prices & discounts using historical cost benchmarks.
3. `operaciones_presupuesto.py`: Operations & Budget Control Agent (`project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`). Detects budget overruns and operational delays.
4. `estados_pago.py`: Progress Invoicing Agent (`account.move`, `project.task`). Generates draft customer progress billing invoices based on task completions.
5. `gestion_documental.py`: Document Compliance & Accreditation Agent (F30-1, mutualidad, contractor compliance). Flags non-compliance gaps before payment approvals.
6. `conciliador_contable.py`: Accounting Reconciliation & DTE Agent (SII DTEs, `account.move` vendor bills, `purchase.order`). Matches DTE XML/JSON data against purchase orders and vendor invoices.

Read `PROJECT.md`, `ORIGINAL_REQUEST.md`, `src/odoo_ecosystem/`, and `src/rag_memory/`.
Write your agent design specification to `.agents/explorer_m3_2/analysis.md` and handoff report to `.agents/explorer_m3_2/handoff.md`.
