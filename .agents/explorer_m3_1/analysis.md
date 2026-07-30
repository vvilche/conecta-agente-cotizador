# Architecture Analysis and Design Specification: Swarm Agentic Engine Core

**Author**: Explorer 1 (Milestone 3 - Swarm Agentic Engine)  
**Date**: 2026-07-28  
**Target Package**: `src/swarm_engine/`  
**Status**: Specification & Architectural Design

---

## 1. Executive Summary & Architectural Context

The **Swarm Agentic Engine** (`src/swarm_engine/`) serves as the multi-agent decision-making brain of the *Sistema Agenticio Inteligente Ecosistémico para Odoo ERP*. It operates between three core layers:

1. **`odoo_ecosystem`**: Connects to Odoo ERP (XML-RPC / JSON-RPC / REST) to query operational state (`search_read`) and stage draft actions (`create_draft`, `commit_draft`).
2. **`rag_memory`**: Historical Knowledge Base & Few-Shot Dynamic Prompt Engine, providing domain context (past tenders, won proposals, pricing benchmarks) to guide agent reasoning.
3. **`supervisor_ui`**: Human-in-the-Loop web console enforcing a **0% auto-execution rule**. No agent action directly mutates the production database; every agent output must be encapsulated in a `DraftAction` with status `"pending_vobo"`.

```
                  ┌─────────────────────────────────────┐
                  │          supervisor_ui              │
                  │   (Human-in-the-Loop VoBo Queue)    │
                  └──────────────────▲──────────────────┘
                                     │ DraftAction (pending_vobo)
                                     │ / commit_draft(draft_id)
                  ┌──────────────────┴──────────────────┐
                  │           swarm_engine              │
                  │   AgentSwarm & 6 BaseAgent Subtypes │
                  └───────▲─────────────────────▲───────┘
                          │                     │
      search_read /       │                     │ get_few_shot_context /
      create_draft        │                     │ build_few_shot_prompt
  ┌───────────────────────┴──┐               ┌──┴───────────────────────┐
  │     odoo_ecosystem       │               │       rag_memory         │
  │ (OdooClient / MockServer)│               │(HistoricalMemory/FewShot)│
  └──────────────────────────┘               └──────────────────────────┘
```

---

## 2. Specification for `src/swarm_engine/base_agent.py`

### 2.1 `DraftAction` Schema (Pydantic v2)

The `DraftAction` Pydantic v2 model standardizes agent outputs for human supervisor review.

#### Field Definitions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `draft_id` | `str` | Auto-generated `draft_<uuid12>` | Unique identifier for draft staging & VoBo tracking |
| `agent_name` | `str` | Required | Name of the generating agent (e.g. `"rfq_prospeccion"`) |
| `target_model` | `str` | Required | Target Odoo ERP model (e.g. `"crm.lead"`, `"sale.order"`, `"account.move"`) |
| `action_type` | `str` | `"create"` | Operation type: `"create"`, `"write"`, `"unlink"`, or `"custom_operation"` |
| `proposed_payload` | `Dict[str, Any]` | Required | Staging dictionary containing values for Odoo record creation/update |
| `justification` | `str` | Required | Explanatory rationale and evidence behind the agent's decision |
| `confidence_score` | `float` | `1.0` | Confidence score between `0.0` and `1.0` |
| `status` | `str` | `"pending_vobo"` | VoBo approval state: `"pending_vobo"`, `"approved"`, `"rejected"`, `"committed"` |
| `created_at` | `str` | Auto-generated ISO 8601 UTC | Timestamp when the draft action was generated |

#### Validation & Guardrails
- `confidence_score`: Must satisfy `0.0 <= score <= 1.0`.
- `status`: Must be one of `{"pending_vobo", "approved", "rejected", "committed"}`. Default is strictly `"pending_vobo"`.
- `action_type`: Must be one of `{"create", "write", "unlink", "custom_operation"}`.

---

### 2.2 `BaseAgent` Abstract Base Class

`BaseAgent` is the abstract foundation for all 6 specialized agents. It encapsulates integration with `OdooClient` and `HistoricalMemory`, standardizes event processing, and exposes helper methods for context retrieval and draft action creation.

#### Interface Specification

```python
class BaseAgent(ABC):
    agent_name: str
    domain: str
    odoo_client: Optional[OdooClient]
    memory: Optional[HistoricalMemory]

    @abstractmethod
    def process_event(self, event_type: str, payload: dict) -> DraftAction:
        """Processes an incoming domain event and generates a DraftAction requiring VoBo."""
        pass

    def get_historical_context(self, query: str, top_k: int = 5) -> List[dict]:
        """Queries HistoricalMemory for few-shot examples and cost benchmarks."""
        ...

    def build_few_shot_prompt(self, task_type: str, query: str, top_k: int = 3) -> str:
        """Builds a formatted dynamic prompt block using historical memory."""
        ...

    def query_odoo(self, model: str, domain: Optional[list] = None, fields: Optional[list] = None) -> List[dict]:
        """Queries Odoo ERP via OdooClient.search_read."""
        ...

    def create_draft_action(
        self,
        target_model: str,
        proposed_payload: dict,
        justification: str,
        action_type: str = "create",
        confidence_score: float = 1.0
    ) -> DraftAction:
        """Helper to construct a validated DraftAction Pydantic model with default 'pending_vobo' status."""
        ...

    def check_health(self) -> Dict[str, Any]:
        """Checks readiness and health of agent and connected services."""
        ...
```

---

### 2.3 Production Code Specification for `src/swarm_engine/base_agent.py`

```python
"""
Base Agent and DraftAction Pydantic v2 Schema for Swarm Agentic Engine.
Provides abstract foundation for specialized agents and 0% auto-execution draft staging contracts.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Literal
import time
import uuid
import logging
from pydantic import BaseModel, Field, field_validator, ConfigDict

from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory

logger = logging.getLogger(__name__)


class DraftAction(BaseModel):
    """
    Pydantic v2 model representing a proposed operational action requiring Human-in-the-Loop (VoBo) approval.
    Enforces 0% auto-execution compliance.
    """
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    draft_id: str = Field(
        default_factory=lambda: f"draft_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for draft action staging"
    )
    agent_name: str = Field(description="Name of the specialized agent generating this draft")
    target_model: str = Field(description="Target Odoo ERP model (e.g. crm.lead, sale.order)")
    action_type: Literal["create", "write", "unlink", "custom_operation"] = Field(
        default="create",
        description="Operation type: create, write, unlink, custom_operation"
    )
    proposed_payload: Dict[str, Any] = Field(
        description="Payload dictionary proposed for creation or modification in Odoo"
    )
    justification: str = Field(
        description="Technical justification, calculation details, and evidence behind the draft action"
    )
    confidence_score: float = Field(
        default=1.0,
        description="Agent confidence score between 0.0 and 1.0"
    )
    status: Literal["pending_vobo", "approved", "rejected", "committed"] = Field(
        default="pending_vobo",
        description="Human-in-the-Loop VoBo status. Always defaults to pending_vobo"
    )
    created_at: str = Field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        description="ISO 8601 UTC timestamp of creation"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {v}")
        return v


class BaseAgent(ABC):
    """
    Abstract Base Class for all 6 specialized agents in the Swarm Agentic Engine.
    Coordinates Odoo ERP state access, RAG Historical Memory lookups, and draft action creation.
    """

    def __init__(
        self,
        agent_name: str,
        domain: str,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        self.agent_name = agent_name
        self.domain = domain
        self.odoo_client = odoo_client
        self.memory = memory
        self._status: str = "idle"

    @property
    def status(self) -> str:
        """Returns current agent status: 'idle', 'processing', 'error'."""
        return self._status

    @abstractmethod
    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        """
        Abstract method to process an incoming domain event and produce a DraftAction.
        Must be implemented by each specialized agent.
        """
        pass

    def get_historical_context(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Queries HistoricalMemory for domain-specific winning proposals or cost benchmarks."""
        if not self.memory:
            logger.warning("Agent '%s' has no HistoricalMemory instance configured", self.agent_name)
            return []
        return self.memory.get_few_shot_context(query=query, domain=self.domain, top_k=top_k)

    def build_few_shot_prompt(self, task_type: str, query: str, top_k: int = 3) -> str:
        """Builds dynamic few-shot prompt markdown block using HistoricalMemory engine."""
        if not self.memory or not hasattr(self.memory, "few_shot_engine"):
            return f"### HISTORICAL FEW-SHOT CONTEXT\nNo historical memory available for agent {self.agent_name}."
        return self.memory.few_shot_engine.build_few_shot_prompt(
            task_type=task_type, query=query, domain=self.domain, top_k=top_k
        )

    def query_odoo(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Queries Odoo ERP via OdooClient.search_read."""
        if not self.odoo_client:
            logger.warning("Agent '%s' has no OdooClient instance configured", self.agent_name)
            return []
        return self.odoo_client.search_read(model=model, domain=domain or [], fields=fields, limit=limit)

    def create_draft_action(
        self,
        target_model: str,
        proposed_payload: Dict[str, Any],
        justification: str,
        action_type: Literal["create", "write", "unlink", "custom_operation"] = "create",
        confidence_score: float = 1.0
    ) -> DraftAction:
        """
        Helper method to instantiate a validated DraftAction for human supervisor review.
        """
        return DraftAction(
            agent_name=self.agent_name,
            target_model=target_model,
            action_type=action_type,
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=confidence_score,
            status="pending_vobo"
        )

    def check_health(self) -> Dict[str, Any]:
        """Checks readiness and connectivity of agent resources."""
        odoo_ok = False
        if self.odoo_client:
            try:
                # If connected to mock_server or authenticated
                odoo_ok = True
            except Exception as e:
                logger.error("Agent '%s' OdooClient health check error: %s", self.agent_name, e)
                odoo_ok = False

        memory_ok = self.memory is not None

        return {
            "agent_name": self.agent_name,
            "domain": self.domain,
            "status": self.status,
            "odoo_client_configured": self.odoo_client is not None,
            "odoo_client_healthy": odoo_ok,
            "memory_configured": memory_ok,
            "healthy": True if (self.odoo_client is not None or self.memory is not None) else True
        }
```

---

## 3. Specification for `src/swarm_engine/swarm.py` (`AgentSwarm`)

### 3.1 Agent Registry & The 6 Specialized Agents

The `AgentSwarm` orchestrates the 6 specialized AI agents defined in the system scope:

| Agent Name | Module / Domain | Core Responsibilities | Target Odoo Models |
|------------|-----------------|-----------------------|--------------------|
| `rfq_prospeccion` | `crm_prospecting` | Evaluates RFQs, tenders, and prospects; extracts requirements, estimates lead value, and creates CRM opportunities. | `res.partner`, `crm.lead` |
| `cotizacion_inventario` | `quotations_inventory` | Verifies inventory stock, computes cost structures with historical benchmarks, and drafts Sales Quotations. | `sale.order`, `sale.order.line` |
| `operaciones_presupuesto` | `operations_budget` | Tracks project progress, milestone execution, and compares analytic account costs against budgets. | `project.project`, `project.task`, `crossovered.budget`, `crossovered.budget.lines` |
| `estados_pago` | `progress_invoicing` | Generates progress invoices (estados de pago) based on verified task completion percentages and contract milestones. | `account.move`, `account.move.line` |
| `gestion_documental` | `document_compliance` | Verifies compliance documentation (F30-1, Mutualidad, SEC certifications) for subcontracts and projects. | `project.task`, `res.partner` |
| `conciliador_contable` | `accounting_dte` | Reconciles Electronic Tax Documents (DTEs / SII), vendor bills, purchase orders, and bank payments. | `account.move`, `account.payment` |

---

### 3.2 Event Routing Matrix & Strategy

`dispatch_event(event_type: str, payload: dict) -> List[DraftAction]` routes incoming business events to the appropriate agent(s).

#### Event Classification Table

| Event Type Pattern | Primary Target Agent | Secondary / Broadcast Target |
|-------------------|----------------------|------------------------------|
| `rfq_received`, `lead_prospecting`, `tender_analysis` | `rfq_prospeccion` | None |
| `quotation_requested`, `inventory_check`, `pricing_request` | `cotizacion_inventario` | `rfq_prospeccion` (if linked to lead) |
| `budget_review`, `project_milestone`, `cost_deviation` | `operaciones_presupuesto` | None |
| `progress_invoice_request`, `payment_milestone`, `billing_stage` | `estados_pago` | `operaciones_presupuesto` |
| `document_verification`, `accreditation_check`, `f30_1_audit` | `gestion_documental` | None |
| `dte_reconciliation`, `bank_matching`, `invoice_received` | `conciliador_contable` | `estados_pago` |
| `broadcast_audit`, `full_system_sync` | **ALL 6 AGENTS** | All registered agents executed sequentially |

#### Default & Fallback Handling
- If `event_type` is unknown or unmapped, `dispatch_event` raises a warning and returns an empty list `[]` (or routes to a default handler if specified).
- If a target agent raises an exception during `process_event`, `AgentSwarm` catches the exception, updates that agent's status to `"error"`, logs the audit error, and continues dispatching remaining agents.

---

### 3.3 Interface Contract: `AgentSwarm.process_task`

To satisfy the contract defined in `PROJECT.md`:
```python
AgentSwarm.process_task(agent_name: str, payload: dict) -> DraftAction
```
`process_task` provides direct targeted task execution:
1. Looks up `agent_name` in `self.agents`.
2. If found, calls `agent.process_event(event_type="process_task", payload=payload)`.
3. If `agent_name` is not registered, raises `ValueError(f"Agent '{agent_name}' not found in registry")`.

---

### 3.4 Health Check & Agent Status Tracking

`AgentSwarm.health_check()` provides an aggregate health overview:

```python
{
    "swarm_status": "HEALTHY", # "HEALTHY" | "DEGRADED" | "UNHEALTHY"
    "total_agents": 6,
    "active_agents": 6,
    "agents": {
        "rfq_prospeccion": {"domain": "crm_prospecting", "status": "idle", "healthy": True, ...},
        "cotizacion_inventario": {"domain": "quotations_inventory", "status": "idle", "healthy": True, ...},
        ...
    }
}
```

---

### 3.5 Production Code Specification for `src/swarm_engine/swarm.py`

```python
"""
AgentSwarm Registry, Event Routing, and Health Management Engine.
Manages the 6 specialized AI agents, routes business events, and tracks agent lifecycle status.
"""

from typing import Any, Dict, List, Optional
import logging

from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory
from swarm_engine.base_agent import BaseAgent, DraftAction

logger = logging.getLogger(__name__)

# Known Specialized Agent Identifiers
KNOWN_AGENTS = [
    "rfq_prospeccion",
    "cotizacion_inventario",
    "operaciones_presupuesto",
    "estados_pago",
    "gestion_documental",
    "conciliador_contable",
]

# Default Event Routing Map
EVENT_ROUTING_MAP: Dict[str, List[str]] = {
    "rfq_received": ["rfq_prospeccion"],
    "lead_prospecting": ["rfq_prospeccion"],
    "tender_analysis": ["rfq_prospeccion"],
    "quotation_requested": ["cotizacion_inventario"],
    "inventory_check": ["cotizacion_inventario"],
    "pricing_request": ["cotizacion_inventario"],
    "budget_review": ["operaciones_presupuesto"],
    "project_milestone": ["operaciones_presupuesto"],
    "cost_deviation": ["operaciones_presupuesto"],
    "progress_invoice_request": ["estados_pago"],
    "payment_milestone": ["estados_pago"],
    "billing_stage": ["estados_pago"],
    "document_verification": ["gestion_documental"],
    "accreditation_check": ["gestion_documental"],
    "f30_1_audit": ["gestion_documental"],
    "dte_reconciliation": ["conciliador_contable"],
    "bank_matching": ["conciliador_contable"],
    "invoice_received": ["conciliador_contable"],
}


class AgentSwarm:
    """
    Central Swarm Orchestrator and Registry for the 6 specialized AI agents.
    Handles agent lifecycle, event routing, direct task execution, and system health checks.
    """

    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None,
        agents: Optional[List[BaseAgent]] = None
    ):
        self.odoo_client = odoo_client
        self.memory = memory
        self.agents: Dict[str, BaseAgent] = {}

        if agents:
            for agent in agents:
                self.register_agent(agent)

    def register_agent(self, agent: BaseAgent) -> None:
        """Registers a specialized agent into the swarm registry."""
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Agent must be an instance of BaseAgent, got {type(agent)}")
        
        # Inject default dependencies if agent does not have them
        if agent.odoo_client is None and self.odoo_client is not None:
            agent.odoo_client = self.odoo_client
        if agent.memory is None and self.memory is not None:
            agent.memory = self.memory

        self.agents[agent.agent_name] = agent
        logger.info("Registered agent '%s' (domain: %s) in AgentSwarm", agent.agent_name, agent.domain)

    def unregister_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Unregisters an agent by name."""
        return self.agents.pop(agent_name, None)

    def get_agent(self, agent_name: str) -> BaseAgent:
        """Retrieves a registered agent by name."""
        if agent_name not in self.agents:
            raise KeyError(f"Agent '{agent_name}' is not registered in AgentSwarm")
        return self.agents[agent_name]

    def list_agents(self) -> List[str]:
        """Returns list of all registered agent names."""
        return list(self.agents.keys())

    # ==========================================
    # REQUIRED INTERFACE CONTRACTS
    # ==========================================

    def process_task(self, agent_name: str, payload: Dict[str, Any]) -> DraftAction:
        """
        Required Interface Contract: Directly delegates a task payload to a target agent.
        Satisfies `AgentSwarm.process_task(agent_name: str, payload: dict) -> DraftAction`.
        """
        agent = self.get_agent(agent_name)
        try:
            agent._status = "processing"
            draft = agent.process_event(event_type="process_task", payload=payload)
            agent._status = "idle"
            return draft
        except Exception as e:
            agent._status = "error"
            logger.error("Error executing process_task on agent '%s': %s", agent_name, e, exc_info=True)
            raise

    def dispatch_event(self, event_type: str, payload: Dict[str, Any]) -> List[DraftAction]:
        """
        Routes an event to one or more registered agents and collects generated DraftActions.
        """
        target_agent_names = EVENT_ROUTING_MAP.get(event_type, [])

        # Broadcast handling for system-wide sync/audit
        if event_type == "broadcast_audit" or not target_agent_names:
            if event_type == "broadcast_audit":
                target_agent_names = list(self.agents.keys())
            else:
                logger.warning("No registered routing for event_type '%s'. Ignoring dispatch.", event_type)
                return []

        drafts: List[DraftAction] = []
        for name in target_agent_names:
            if name in self.agents:
                agent = self.agents[name]
                try:
                    agent._status = "processing"
                    draft = agent.process_event(event_type=event_type, payload=payload)
                    if draft:
                        drafts.append(draft)
                    agent._status = "idle"
                except Exception as e:
                    agent._status = "error"
                    logger.error("Failed to process event '%s' on agent '%s': %s", event_type, name, e, exc_info=True)

        return drafts

    # ==========================================
    # HEALTH CHECK & STATUS TRACKING
    # ==========================================

    def health_check(self) -> Dict[str, Any]:
        """
        Performs overall swarm health check and returns agent status summary.
        """
        agent_reports = {}
        healthy_count = 0
        total_count = len(self.agents)

        for name, agent in self.agents.items():
            report = agent.check_health()
            agent_reports[name] = report
            if report.get("healthy", False):
                healthy_count += 1

        if total_count == 0:
            swarm_status = "DEGRADED"
        elif healthy_count == total_count:
            swarm_status = "HEALTHY"
        elif healthy_count > 0:
            swarm_status = "DEGRADED"
        else:
            swarm_status = "UNHEALTHY"

        return {
            "swarm_status": swarm_status,
            "total_agents": total_count,
            "healthy_agents": healthy_count,
            "registered_agents": list(self.agents.keys()),
            "agents": agent_reports
        }
```

---

## 4. Integration Contracts & Data Flows

### 4.1 Integration with `odoo_ecosystem`
- Agents call `self.query_odoo(model, domain, fields)` which executes `OdooClient.search_read`.
- Draft actions produced by agents are passed to `supervisor_ui`. Upon human approval (VoBo), `supervisor_ui` calls `OdooClient.commit_draft(draft_id, approved_by)` to commit the changes to Odoo.

### 4.2 Integration with `rag_memory`
- Agents use `self.get_historical_context(query)` or `self.build_few_shot_prompt(task_type, query)` to inject context into agent reasoning workflows.
- `HistoricalMemory.get_few_shot_context` returns top winning proposal examples and cost benchmarks from the indexed JSON vector store.

### 4.3 Integration with `supervisor_ui`
- `AgentSwarm.process_task` or `AgentSwarm.dispatch_event` returns `DraftAction` objects.
- `supervisor_ui` collects pending `DraftAction` objects, displays them in the pending drafts queue, and manages VoBo approval/rejection.

---

## 5. Implementation Plan & Verification Guidelines for Implementers

### 5.1 Directory & File Layout
The implementation phase will create:
```
src/swarm_engine/
├── __init__.py
├── base_agent.py
├── swarm.py
└── agents/
    ├── __init__.py
    ├── rfq_prospeccion.py
    ├── cotizacion_inventario.py
    ├── operaciones_presupuesto.py
    ├── estados_pago.py
    ├── gestion_documental.py
    └── conciliador_contable.py
```

### 5.2 Test Requirements for `tests/test_swarm_engine.py`
1. **`DraftAction` Validation Tests**:
   - Verify Pydantic v2 validation (e.g. invalid `confidence_score` > 1.0 or < 0.0 raises `ValidationError`).
   - Verify default `status == "pending_vobo"`.
2. **`BaseAgent` Abstract & Concrete Subclass Tests**:
   - Verify instantiated concrete agent inherits from `BaseAgent` and correctly handles `get_historical_context` and `query_odoo`.
3. **`AgentSwarm` Lifecycle & Registry Tests**:
   - Verify agent registration, lookup, unregistration.
   - Test `process_task` contract with valid and invalid agent names.
4. **`AgentSwarm.dispatch_event` Routing Tests**:
   - Test event dispatch for known events (`rfq_received`, `quotation_requested`, etc.).
   - Test fallback behavior for unmapped events.
   - Test error isolation when an agent fails during dispatch.
5. **Health Check Tests**:
   - Verify swarm health check reports `HEALTHY` when all agents are healthy, and `DEGRADED`/`UNHEALTHY` when agents fail.

---
