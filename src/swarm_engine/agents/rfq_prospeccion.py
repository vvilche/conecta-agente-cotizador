"""
RFQ & Commercial Prospecting Agent (RFQProspeccionAgent).
Evaluates RFQs, tenders, and prospects; extracts requirements, estimates lead value and win probability using RAG historical context, and creates draft CRM opportunities.
"""

from typing import Any, Dict, List, Optional
import logging
from swarm_engine.base_agent import BaseAgent, DraftAction
from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory

logger = logging.getLogger(__name__)


class RFQProspeccionAgent(BaseAgent):
    """
    Specialized agent for RFQ evaluation and CRM lead prospecting.
    Integrates Odoo res.partner lookups and RAG Historical Memory of past winning proposals.
    """

    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="rfq_prospeccion",
            domain="crm_prospecting",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        """
        Processes RFQ/Lead events and constructs a staged DraftAction for crm.lead creation.
        """
        supported_events = {
            "rfq_received", "process_rfq", "lead_prospecting",
            "tender_analysis", "process_task", "lead_evaluate"
        }
        if event_type not in supported_events:
            logger.warning("Agent '%s' received unmapped event type '%s'", self.agent_name, event_type)

        return self._handle_rfq_evaluation(payload)

    def _handle_rfq_evaluation(self, payload: Dict[str, Any]) -> DraftAction:
        client_name = payload.get("client_name") or payload.get("client") or "Cliente Desconocido"
        vat = payload.get("vat")
        title = payload.get("title") or payload.get("name") or payload.get("opportunity_title") or "Oportunidad Comercial RFQ"
        description = payload.get("description") or payload.get("raw_content") or ""
        domain_tag = payload.get("domain") or "edac_erag"
        budget_estimate = payload.get("budget_estimate") or payload.get("expected_revenue")

        # 1. Look up res.partner in Odoo ERP
        partner_id = None
        if self.odoo_client:
            partners = []
            if vat:
                partners = self.query_odoo("res.partner", domain=[["vat", "=", vat]], fields=["id", "name"])
            if not partners and client_name:
                partners = self.query_odoo("res.partner", domain=[["name", "ilike", client_name]], fields=["id", "name"])

            if partners:
                partner_id = partners[0]["id"]
                client_name = partners[0].get("name", client_name)

        # 2. Query HistoricalMemory RAG context for winning proposals
        query_text = f"{title} {description}"
        winning_examples = self.get_historical_context(query=query_text, top_k=3)

        # 3. Win Probability & Revenue Estimation Logic
        won_cases = [e for e in winning_examples if e.get("outcome") == "won" or "won" in e.get("tags", [])]
        base_probability = 60.0
        if won_cases:
            base_probability = min(95.0, 60.0 + len(won_cases) * 10.0)

        calculated_revenue = 0.0
        if budget_estimate is not None and float(budget_estimate) > 0:
            calculated_revenue = float(budget_estimate)
        elif won_cases and won_cases[0].get("price"):
            calculated_revenue = float(won_cases[0]["price"])
        else:
            calculated_revenue = 15000000.0

        # 4. Formulate staged crm.lead proposed payload
        proposed_payload = {
            "name": title,
            "partner_id": partner_id or client_name,
            "expected_revenue": float(calculated_revenue),
            "probability": float(base_probability),
            "type": "opportunity",
            "description": f"Propuesta estructurada basada en {len(won_cases)} casos ganados históricos.\n{description[:250]}"
        }

        justification = (
            f"Oportunidad CRM generada por evaluación de RFQ para cliente '{client_name}'. "
            f"Búsqueda RAG identificó {len(winning_examples)} referencias históricas ({len(won_cases)} propuestas ganadas). "
            f"Probabilidad de adjudicación estimada en {base_probability:.1f}%. "
            f"Monto estimado: ${calculated_revenue:,.0f} CLP."
        )

        return self.create_draft_action(
            target_model="crm.lead",
            action_type="create",
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=0.88 if winning_examples else 0.75,
            metadata={
                "client_name": client_name,
                "vat": vat,
                "domain_tag": domain_tag,
                "rag_references_count": len(winning_examples),
                "won_cases_count": len(won_cases)
            }
        )
