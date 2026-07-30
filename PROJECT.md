# Project: Sistema Agenticio Inteligente Ecosistémico para Odoo ERP

## Architecture
- **Language & Runtime**: Python 3.10+
- **Core Modules**:
  - `odoo_ecosystem/`: Odoo ERP Connector (XML-RPC / JSON-RPC / REST) & Abstraction Layer (`res.partner`, `crm.lead`, `sale.order`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `account.move`, `account.payment`).
  - `rag_memory/`: Historical Knowledge Base & Few-Shot Dynamic Prompt Engine (tenders, won/lost proposals, historical prices, cost structures).
  - `swarm_engine/`: 6 Specialized AI Agents (RFQ, Quotation/Inventory, Operations/Budget, Progress Invoicing, Document Compliance, DTE/Accounting Reconciliation).
  - `supervisor_ui/`: Human-in-the-Loop Web Console with 0% auto-execution enforcement, VoBo draft approval workflows, and structured audit logs.
- **Testing Infrastructure**: `tests/` directory with pytest, mock Odoo server, and Tier 1-5 test coverage.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Odoo Core Connector & Models | XML-RPC/JSON-RPC/REST wrapper, model abstractions, mock server, retries, audit | None | DONE |
| 2 | RAG Memory & Ingestion Engine | Ingestion pipelines, embeddings indexer, few-shot dynamic context provider | M1 | DONE |
| 3 | Swarm Agentic Engine | 6 Specialized agents (RFQ, Quotations, Operations, Invoicing, Compliance, DTE) | M1, M2 | DONE |
| 4 | Supervisor Human-in-the-Loop Web Console | Web console, Pending Drafts queue, VoBo/Reject logic, structured audit logs | M1, M3 | DONE |
| 5 | System Integration & Test Hardening | End-to-end integration, test suite execution (Tiers 1-5), coverage hardening | M1, M2, M3, M4 | IN-PROGRESS |

## Interface Contracts
### `odoo_ecosystem` ↔ `swarm_engine`
- `OdooClient.search_read(model: str, domain: list, fields: list) -> list[dict]`
- `OdooClient.create_draft(model: str, values: dict) -> dict` (Staged creation, returns draft payload ID)
- `OdooClient.commit_draft(draft_id: str, approved_by: str) -> dict` (Executed strictly upon VoBo approval)

### `rag_memory` ↔ `swarm_engine`
- `HistoricalMemory.ingest_document(doc_type: str, content: dict) -> str`
- `HistoricalMemory.get_few_shot_context(query: str, domain: str, top_k: int = 5) -> list[dict]`

### `swarm_engine` ↔ `supervisor_ui`
- `AgentSwarm.process_task(agent_name: str, payload: dict) -> DraftAction`
- `SupervisorConsole.get_pending_drafts() -> list[DraftAction]`
- `SupervisorConsole.approve_draft(draft_id: str, user_vobo: dict) -> ActionResult`

## Code Layout
```
.
├── PROJECT.md
├── ORIGINAL_REQUEST.md
├── pyproject.toml
├── src/
│   ├── odoo_ecosystem/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── models.py
│   │   ├── mock_server.py
│   │   └── audit.py
│   ├── rag_memory/
│   │   ├── __init__.py
│   │   ├── ingester.py
│   │   ├── indexer.py
│   │   └── few_shot.py
│   ├── swarm_engine/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── agents/
│   │   │   ├── rfq_prospeccion.py
│   │   │   ├── cotizacion_inventario.py
│   │   │   ├── operaciones_presupuesto.py
│   │   │   ├── estados_pago.py
│   │   │   ├── gestion_documental.py
│   │   │   └── conciliador_contable.py
│   │   └── swarm.py
│   └── supervisor_ui/
│       ├── __init__.py
│       ├── app.py
│       ├── drafts.py
│       └── audit_logger.py
└── tests/
    ├── conftest.py
    ├── test_odoo_ecosystem.py
    ├── test_rag_memory.py
    ├── test_swarm_engine.py
    ├── test_supervisor_ui.py
    └── test_e2e_integration.py
```
