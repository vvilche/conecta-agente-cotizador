# Handoff Report: Swarm Agentic Engine Architecture & Design (Milestone 3 Core)

**Agent**: Explorer 1  
**Milestone**: Milestone 3 — Swarm Agentic Engine  
**Target Files**: `src/swarm_engine/base_agent.py` and `src/swarm_engine/swarm.py`  
**Location**: `.agents/explorer_m3_1/handoff.md`  

---

## 1. Observation

1. **Existing Infrastructure**:
   - `src/odoo_ecosystem/client.py`: Provides `OdooClient` with contracts `search_read(model, domain, fields)`, `create_draft(model, values)`, `commit_draft(draft_id, approved_by)`.
   - `src/rag_memory/few_shot.py`: Provides `HistoricalMemory` with `get_few_shot_context(query, domain, top_k)` and `FewShotEngine.build_few_shot_prompt(...)`.
   - `PROJECT.md` line 32: Specifies contract `AgentSwarm.process_task(agent_name: str, payload: dict) -> DraftAction`.
   - `PROJECT.md` lines 55-64: Specifies file layout for `src/swarm_engine/` including `base_agent.py`, `swarm.py`, and `agents/` directory containing the 6 specialized agents.

2. **0% Auto-Execution Requirement**:
   - `ORIGINAL_REQUEST.md` R4 & `PROJECT.md` section 9 enforce that no agent auto-executes database mutations directly. Every agent action must produce a `DraftAction` with `status="pending_vobo"`.

---

## 2. Logic Chain

1. **DraftAction Specification**:
   - `DraftAction` requires Pydantic v2 validation (`model_config = ConfigDict(...)`).
   - Fields: `draft_id` (str, UUID format), `agent_name` (str), `target_model` (str), `action_type` (Literal["create", "write", "unlink", "custom_operation"]), `proposed_payload` (dict), `justification` (str), `confidence_score` (float, constrained to [0.0, 1.0]), `status` (Literal["pending_vobo", "approved", "rejected", "committed"], defaulting to `"pending_vobo"`), `created_at` (ISO 8601 UTC).

2. **BaseAgent Abstract Base Class**:
   - `BaseAgent` standardizes agent properties (`agent_name`, `domain`, `status`) and dependency references (`odoo_client`, `memory`).
   - Declares `@abstractmethod process_event(event_type: str, payload: dict) -> DraftAction`.
   - Supplies helper methods: `get_historical_context`, `build_few_shot_prompt`, `query_odoo`, `create_draft_action`, `check_health`.

3. **AgentSwarm Orchestrator**:
   - Manages registry for the 6 specialized agents (`rfq_prospeccion`, `cotizacion_inventario`, `operaciones_presupuesto`, `estados_pago`, `gestion_documental`, `conciliador_contable`).
   - Implements `process_task(agent_name, payload)` for direct execution.
   - Implements `dispatch_event(event_type, payload)` with an event routing map (`EVENT_ROUTING_MAP`) and error isolation.
   - Implements `health_check()` returning aggregate status (`HEALTHY`, `DEGRADED`, `UNHEALTHY`) and per-agent diagnostic reports.

---

## 3. Caveats

- **Scope Boundary**: Explorer 1 produces read-only architectural analysis and concrete implementation code specifications. The actual creation of `src/swarm_engine/base_agent.py` and `src/swarm_engine/swarm.py` on disk is to be performed by the Implementer agent based on `.agents/explorer_m3_1/analysis.md`.
- **Specialized Agent Implementation**: The 6 specialized agents residing in `src/swarm_engine/agents/` will subclass `BaseAgent` and be registered into `AgentSwarm`.

---

## 4. Conclusion

The design specification for `src/swarm_engine/base_agent.py` and `src/swarm_engine/swarm.py` is complete, fully specified with production-grade Pydantic v2 models and Python code, and ready for immediate implementation.

Detailed specifications and copy-pasteable code implementations are documented in `.agents/explorer_m3_1/analysis.md`.

---

## 5. Verification Method

To verify the implementation once created by the implementer:
1. **Directory Layout**: Check that `src/swarm_engine/__init__.py`, `src/swarm_engine/base_agent.py`, `src/swarm_engine/swarm.py`, and `src/swarm_engine/agents/__init__.py` exist.
2. **Pytest Verification**:
   Execute:
   ```bash
   pytest tests/test_swarm_engine.py -v
   ```
3. **Key Test Checks**:
   - `DraftAction` fails validation if `confidence_score` > 1.0 or < 0.0.
   - `DraftAction.status` defaults to `"pending_vobo"`.
   - `AgentSwarm` registers agents, dispatches events correctly according to `EVENT_ROUTING_MAP`, and isolated errors if one agent fails.
   - `AgentSwarm.health_check()` accurately reflects agent readiness.
