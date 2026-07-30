"""
Operations & Budget Control Agent (OperacionesPresupuestoAgent).
Tracks project execution, analytic account budgets (account.analytic.account & crossovered.budget.lines),
detects budget overruns (>10% threshold) and operational delays, and drafts budget adjustments or project tasks.
"""

from typing import Any, Dict, List, Optional
import logging
from swarm_engine.base_agent import BaseAgent, DraftAction
from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory

logger = logging.getLogger(__name__)


class OperacionesPresupuestoAgent(BaseAgent):
    """
    Specialized agent for monitoring operational performance, task execution, and analytic budget variances.
    """

    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="operaciones_presupuesto",
            domain="operations_budget",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        """
        Processes budget audit or project milestone events to generate staged DraftActions.
        """
        supported_events = {
            "audit_budget_overrun", "project_health_check", "budget_review",
            "project_milestone", "cost_deviation", "process_task", "audit_operational_delays",
            "create_project_task"
        }
        if event_type not in supported_events:
            logger.warning("Agent '%s' received unmapped event type '%s'", self.agent_name, event_type)

        if event_type in ("create_project_task", "project_milestone") and "task_name" in payload:
            return self._handle_task_creation(payload)
        return self._handle_budget_audit(payload)

    def _handle_budget_audit(self, payload: Dict[str, Any]) -> DraftAction:
        analytic_id = payload.get("analytic_account_id") or payload.get("project_id") or 300
        threshold_pct = float(payload.get("threshold_pct") or 10.0)

        planned_amount = float(payload.get("planned_amount", 100000.0))
        practical_amount = float(payload.get("practical_amount", 118500.0))

        # Query Odoo if client is available
        line_id = 1
        if self.odoo_client and analytic_id:
            lines = self.query_odoo(
                "crossovered.budget.lines",
                domain=[["analytic_account_id", "=", analytic_id]],
                fields=["id", "planned_amount", "practical_amount", "percentage"]
            )
            if lines:
                line_rec = lines[0]
                line_id = line_rec.get("id", 1)
                planned_amount = float(line_rec.get("planned_amount", planned_amount))
                practical_amount = float(line_rec.get("practical_amount", practical_amount))

        variance_pct = 0.0
        if planned_amount > 0 and practical_amount > planned_amount:
            variance_pct = ((practical_amount - planned_amount) / planned_amount) * 100.0

        overrun_detected = variance_pct >= threshold_pct
        proposed_planned = max(planned_amount, practical_amount * 1.05)

        proposed_payload = {
            "id": line_id,
            "analytic_account_id": analytic_id,
            "planned_amount": proposed_planned,
            "practical_amount": practical_amount
        }

        if overrun_detected:
            justification = (
                f"ALERTA DE SOBRECOSTO OPERATIVO: Centro de costo ID #{analytic_id} presenta una sobreejecución "
                f"del {variance_pct:.1f}% (${practical_amount:,.0f} CLP ejecutados vs ${planned_amount:,.0f} CLP planificados, "
                f"superando el umbral tolerable de {threshold_pct}%). "
                f"Se propone ajustar el presupuesto planificado a ${proposed_planned:,.0f} CLP."
            )
        else:
            justification = (
                f"Auditoría presupuestaria para Centro de costo ID #{analytic_id}: Ejecución dentro de norma "
                f"(Variación: {variance_pct:.1f}% <= Umbral: {threshold_pct}%). "
                f"Monto ejecutado: ${practical_amount:,.0f} CLP / Planificado: ${planned_amount:,.0f} CLP."
            )

        return self.create_draft_action(
            target_model="crossovered.budget.lines",
            action_type="write",
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=0.95 if overrun_detected else 0.88,
            metadata={
                "analytic_id": analytic_id,
                "planned_amount": planned_amount,
                "practical_amount": practical_amount,
                "variance_pct": variance_pct,
                "overrun_detected": overrun_detected
            }
        )

    def _handle_task_creation(self, payload: Dict[str, Any]) -> DraftAction:
        project_id = payload.get("project_id", 200)
        task_name = payload.get("task_name", "Nueva Tarea de Corrección Presupuestaria")
        planned_hours = float(payload.get("planned_hours", 10.0))

        proposed_payload = {
            "name": task_name,
            "project_id": project_id,
            "planned_hours": planned_hours,
            "kanban_state": "normal"
        }

        justification = (
            f"Propuesta de creación de tarea operativa '{task_name}' para el proyecto #{project_id}. "
            f"Horas planificadas: {planned_hours}h."
        )

        return self.create_draft_action(
            target_model="project.task",
            action_type="create",
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=0.90
        )
