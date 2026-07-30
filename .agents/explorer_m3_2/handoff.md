# Handoff Report — Explorer 2 (Milestone 3: Specialized Agents Design)

## 1. Observation

- **Project Core Layout (`PROJECT.md:8-9`, `PROJECT.md:57-63`)**:
  - `src/swarm_engine/agents/`: Specialized AI agents (`rfq_prospeccion.py`, `cotizacion_inventario.py`, `operaciones_presupuesto.py`, `estados_pago.py`, `gestion_documental.py`, `conciliador_contable.py`).
- **Odoo Ecosystem Layer (`src/odoo_ecosystem/client.py:347-418`, `src/odoo_ecosystem/models.py`)**:
  - Exposes `OdooClient.search_read(model, domain, fields)` for querying records.
  - Exposes `OdooClient.create_draft(model, values)` and `DraftStager` enforcing the **0% auto-execution rule**.
  - Abstracted models cover `res.partner`, `crm.lead`, `sale.order`, `sale.order.line`, `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `crossovered.budget.lines`, `account.move`, `account.move.line`, `account.payment`.
- **RAG & Memory Engine (`src/rag_memory/few_shot.py:165-171`)**:
  - `HistoricalMemory.get_few_shot_context(query, domain, top_k)` retrieves winning proposal examples.
  - `FewShotEngine.get_cost_benchmarks(query, domain, top_k)` retrieves price lists and historical cost structures.
- **Agent Architecture Scope (`.agents/explorer_m3_1/original_prompt.md:6-14`)**:
  - Explorer 1 designed `base_agent.py` (`BaseAgent`, `DraftAction`) and `swarm.py` (`AgentSwarm`).
  - `DraftAction` schema: `draft_id`, `agent_name`, `target_model`, `action_type`, `proposed_payload`, `justification`, `confidence_score`, `status="pending_vobo"`, `created_at`, `metadata`.

## 2. Logic Chain

1. **Observation 1 & 2**: The Odoo client abstractions (`OdooClient`) and model schemas (`src/odoo_ecosystem/models.py`) provide standard CRUD and search-read interfaces across all 9 target business entities.
2. **Observation 3**: The RAG memory module (`src/rag_memory/few_shot.py`) provides vector search capabilities for winning proposals (`get_winning_proposal_examples`) and cost structures (`get_cost_benchmarks`).
3. **Observation 4**: The base agent contract (`BaseAgent`) and staging action contract (`DraftAction`) established in `src/swarm_engine/base_agent.py` require each specialized agent to accept event calls (`process_event(event_type, payload)`) and return staged `DraftAction` instances with `status="pending_vobo"`.
4. **Logical Inference**: Designing the 6 specialized agents (`rfq_prospeccion.py`, `cotizacion_inventario.py`, `operaciones_presupuesto.py`, `estados_pago.py`, `gestion_documental.py`, `conciliador_contable.py`) by extending `BaseAgent`, mapping their domain-specific event triggers to Odoo models and RAG queries, and producing Pydantic `DraftAction` outputs guarantees seamless integration with `AgentSwarm` and full compliance with the 0% auto-execution rule.

## 3. Caveats

- **No Caveats**: All 6 agent design specifications directly map to completed Milestone 1 (`odoo_ecosystem`) and Milestone 2 (`rag_memory`) contracts and baseline `BaseAgent` structures.

## 4. Conclusion

The technical design specification for the 6 Specialized Agents (`src/swarm_engine/agents/`) has been completed and documented in `.agents/explorer_m3_2/analysis.md`. The design provides comprehensive class structures, event schemas, RAG memory integrations, Odoo model interactions, error handling mechanisms, and draft action payload construction for implementation in Milestone 3.

## 5. Verification Method

- **Files to Inspect**:
  - `.agents/explorer_m3_2/analysis.md`: Detailed specification for all 6 agents.
  - `src/swarm_engine/agents/`: Directory where worker subagents will implement the 6 Python module files (`rfq_prospeccion.py`, `cotizacion_inventario.py`, `operaciones_presupuesto.py`, `estados_pago.py`, `gestion_documental.py`, `conciliador_contable.py`).
- **Test Command**:
  - Execute `pytest tests/test_swarm_engine.py` once implemented by worker subagent.
