"""
Swarm Agentic Engine Package for Odoo ERP Integration.
Exposes BaseAgent, DraftAction, AgentSwarm, and the 6 specialized AI agents.
"""

from swarm_engine.base_agent import BaseAgent, DraftAction
from swarm_engine.swarm import AgentSwarm, KNOWN_AGENTS, EVENT_ROUTING_MAP
from swarm_engine.agents.rfq_prospeccion import RFQProspeccionAgent
from swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent
from swarm_engine.agents.operaciones_presupuesto import OperacionesPresupuestoAgent
from swarm_engine.agents.estados_pago import EstadosPagoAgent
from swarm_engine.agents.gestion_documental import GestionDocumentalAgent
from swarm_engine.agents.conciliador_contable import ConciliadorContableAgent

__all__ = [
    "BaseAgent",
    "DraftAction",
    "AgentSwarm",
    "KNOWN_AGENTS",
    "EVENT_ROUTING_MAP",
    "RFQProspeccionAgent",
    "CotizacionInventarioAgent",
    "OperacionesPresupuestoAgent",
    "EstadosPagoAgent",
    "GestionDocumentalAgent",
    "ConciliadorContableAgent",
]
