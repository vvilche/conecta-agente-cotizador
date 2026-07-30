"""
Document Compliance Agent (GestionDocumentalAgent).
Audits subcontracts and partners for statutory compliance under Chilean labor & electrical regulations (F30-1, Mutualidad, PreviRed, SEC certifications),
flagging accreditation gaps and drafting compliance hold/task actions.
"""

from typing import Any, Dict, List, Optional
import logging
from swarm_engine.base_agent import BaseAgent, DraftAction
from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory

logger = logging.getLogger(__name__)


class GestionDocumentalAgent(BaseAgent):
    """
    Specialized agent for auditing contractor documentation and statutory compliance.
    """

    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="gestion_documental",
            domain="document_compliance",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        """
        Processes compliance audits and document verification events to generate staged DraftActions.
        """
        supported_events = {
            "verify_contractor_compliance", "pre_payment_audit",
            "document_verification", "accreditation_check",
            "f30_1_audit", "process_task"
        }
        if event_type not in supported_events:
            logger.warning("Agent '%s' received unmapped event type '%s'", self.agent_name, event_type)

        return self._handle_compliance_audit(payload)

    def _handle_compliance_audit(self, payload: Dict[str, Any]) -> DraftAction:
        partner_id = payload.get("partner_id") or payload.get("contractor_id") or 1
        documents = payload.get("documents") or payload.get("compliance_docs") or []
        project_id = payload.get("project_id") or 200

        required_docs = {"F30-1", "MUTUALIDAD", "PREVIRED"}
        if payload.get("sec_required"):
            required_docs.add("SEC")

        present_valid_docs = set()
        missing_or_expired = []

        for doc in documents:
            dtype = doc.get("doc_type", "").upper()
            status = doc.get("status", "").lower()
            if status in ("valid", "vigente", "approved"):
                if "F30" in dtype:
                    present_valid_docs.add("F30-1")
                elif "MUTUAL" in dtype:
                    present_valid_docs.add("MUTUALIDAD")
                elif "PREVIRED" in dtype:
                    present_valid_docs.add("PREVIRED")
                elif "SEC" in dtype:
                    present_valid_docs.add("SEC")
            else:
                missing_or_expired.append(f"{dtype} ({status})")

        missing_docs = required_docs - present_valid_docs
        is_compliant = len(missing_docs) == 0 and len(missing_or_expired) == 0

        if is_compliant:
            action_type = "write"
            target_model = "res.partner"
            proposed_payload = {
                "id": partner_id,
                "active": True
            }
            justification = (
                f"Acreditación laboral y normativa de Contratista ID #{partner_id} CONFORME. "
                f"Todos los documentos obligatorios ({', '.join(sorted(required_docs))}) se encuentran al día y auditados."
            )
            confidence = 0.96
        else:
            action_type = "create"
            target_model = "project.task"
            gaps = sorted(list(missing_docs | set(missing_or_expired)))
            proposed_payload = {
                "name": f"Regularización Documental: {', '.join(gaps)}",
                "project_id": project_id,
                "partner_id": partner_id,
                "kanban_state": "blocked",
                "description": f"Documentos faltantes o vencidos: {', '.join(gaps)}"
            }
            justification = (
                f"ALERTA DE INCUMPLIMIENTO DOCUMENTAL: Contratista ID #{partner_id} presenta brechas de acreditación. "
                f"Documentos faltantes/vencidos: {', '.join(gaps)}. "
                f"Se retiene aprobación de pago según Ley 20.123 de Subcontratación y se genera tarea de regularización."
            )
            confidence = 0.95

        return self.create_draft_action(
            target_model=target_model,
            action_type=action_type,
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=confidence,
            metadata={
                "partner_id": partner_id,
                "is_compliant": is_compliant,
                "missing_docs": sorted(list(missing_docs)),
                "expired_docs": missing_or_expired
            }
        )
