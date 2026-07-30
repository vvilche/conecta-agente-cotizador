"""
AgentSwarm Registry, Event Routing, and Health Management Engine.
Manages the 6 specialized AI agents, routes business events, and tracks agent lifecycle status.
"""

from typing import Any, Dict, List, Optional
import logging

from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory
from swarm_engine.base_agent import BaseAgent, DraftAction
from swarm_engine.agents.rfq_prospeccion import RFQProspeccionAgent
from swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent
from swarm_engine.agents.operaciones_presupuesto import OperacionesPresupuestoAgent
from swarm_engine.agents.estados_pago import EstadosPagoAgent
from swarm_engine.agents.gestion_documental import GestionDocumentalAgent
from swarm_engine.agents.conciliador_contable import ConciliadorContableAgent

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
    "process_rfq": ["rfq_prospeccion"],
    "lead_prospecting": ["rfq_prospeccion"],
    "tender_analysis": ["rfq_prospeccion"],
    "lead_evaluate": ["rfq_prospeccion"],

    "quote_request": ["cotizacion_inventario"],
    "process_quote": ["cotizacion_inventario"],
    "quotation_requested": ["cotizacion_inventario"],
    "inventory_check": ["cotizacion_inventario"],
    "pricing_request": ["cotizacion_inventario"],

    "audit_budget_overrun": ["operaciones_presupuesto"],
    "project_health_check": ["operaciones_presupuesto"],
    "budget_review": ["operaciones_presupuesto"],
    "project_milestone": ["operaciones_presupuesto"],
    "cost_deviation": ["operaciones_presupuesto"],
    "audit_operational_delays": ["operaciones_presupuesto"],
    "create_project_task": ["operaciones_presupuesto"],

    "generate_progress_invoice": ["estados_pago"],
    "task_completion_billing": ["estados_pago"],
    "progress_invoice_request": ["estados_pago"],
    "payment_milestone": ["estados_pago"],
    "billing_stage": ["estados_pago"],

    "verify_contractor_compliance": ["gestion_documental"],
    "pre_payment_audit": ["gestion_documental"],
    "document_verification": ["gestion_documental"],
    "accreditation_check": ["gestion_documental"],
    "f30_1_audit": ["gestion_documental"],

    "process_dte": ["conciliador_contable"],
    "reconcile_vendor_bill": ["conciliador_contable"],
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

        if agents is not None:
            for agent in agents:
                self.register_agent(agent)
        else:
            # Instantiate all 6 default agents
            default_agents = [
                RFQProspeccionAgent(odoo_client=self.odoo_client, memory=self.memory),
                CotizacionInventarioAgent(odoo_client=self.odoo_client, memory=self.memory),
                OperacionesPresupuestoAgent(odoo_client=self.odoo_client, memory=self.memory),
                EstadosPagoAgent(odoo_client=self.odoo_client, memory=self.memory),
                GestionDocumentalAgent(odoo_client=self.odoo_client, memory=self.memory),
                ConciliadorContableAgent(odoo_client=self.odoo_client, memory=self.memory),
            ]
            for agent in default_agents:
                self.register_agent(agent)

    def register_agent(self, agent: BaseAgent) -> None:
        """Registers a specialized agent into the swarm registry."""
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Agent must be an instance of BaseAgent, got {type(agent)}")

        # Inject default dependencies if agent lacks them
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
        Includes broadcast support and error isolation.
        """
        is_broadcast = event_type in ("broadcast_audit", "broadcast", "*", "all")
        if is_broadcast:
            target_agent_names = list(self.agents.keys())
        else:
            target_agent_names = EVENT_ROUTING_MAP.get(event_type, [])

        if not target_agent_names and not is_broadcast:
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
            if report.get("healthy", False) and agent.status != "error":
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
