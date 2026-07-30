"""
Supervisor Console Core Engine Module.
Manages the pending draft queue state, coordinates AgentSwarm output,
executes OdooClient commits upon supervisor VoBo approval, and records audit logs.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
import logging
import threading

from swarm_engine.base_agent import DraftAction
from swarm_engine.swarm import AgentSwarm
from odoo_ecosystem.client import OdooClient, OdooDraftError
from odoo_ecosystem.audit import mask_sensitive_data
from supervisor_ui.audit_logger import SupervisorAuditLogger

logger = logging.getLogger(__name__)


class DraftNotFoundError(Exception):
    """Raised when querying or approving a draft_id that does not exist."""
    pass


class InvalidDraftStateError(Exception):
    """Raised when attempting an invalid VoBo state transition (e.g. re-approving a rejected draft)."""
    pass


class SupervisorConsole:
    """
    Central Human-in-the-Loop Web Console Engine.
    Enforces 0% auto-execution compliance by managing staged DraftAction lifecycle state.
    """

    def __init__(
        self,
        swarm: Optional[AgentSwarm] = None,
        odoo_client: Optional[OdooClient] = None,
        audit_logger: Optional[SupervisorAuditLogger] = None
    ):
        self.odoo_client = odoo_client
        self.swarm = swarm or AgentSwarm(odoo_client=self.odoo_client)
        self.audit_logger = audit_logger or SupervisorAuditLogger()
        self._draft_queue: Dict[str, DraftAction] = {}
        self._lock = threading.RLock()

    # ==========================================
    # QUEUE MANAGEMENT & DRAFT REGISTRATION
    # ==========================================

    def register_draft(self, draft: DraftAction) -> DraftAction:
        """Registers a new DraftAction into the console pending queue store."""
        if not isinstance(draft, DraftAction):
            raise TypeError(f"Expected DraftAction instance, got {type(draft)}")
        
        with self._lock:
            self._draft_queue[draft.draft_id] = draft
            logger.info("Registered draft '%s' (agent: %s, model: %s) in SupervisorConsole queue",
                        draft.draft_id, draft.agent_name, draft.target_model)
            return draft

    def stage_operations_draft(self, draft_action: DraftAction) -> str:
        """
        Stages operations engine outputs (e.g. Payment Statement invoice drafts)
        into _draft_queue for supervisor VoBo approval.
        Returns the registered draft_id.
        """
        registered = self.register_draft(draft_action)
        return registered.draft_id

    def ingest_swarm_drafts(self, drafts: List[DraftAction]) -> List[DraftAction]:
        """Bulk ingests a list of DraftActions produced by AgentSwarm."""
        registered = []
        for d in drafts:
            registered.append(self.register_draft(d))
        return registered

    def get_draft_by_id(self, draft_id: str) -> DraftAction:
        """Retrieves a DraftAction by ID or raises DraftNotFoundError."""
        with self._lock:
            if draft_id not in self._draft_queue:
                raise DraftNotFoundError(f"Draft action '{draft_id}' not found in supervisor queue")
            return self._draft_queue[draft_id]

    def get_draft_detail(self, draft_id: str) -> Dict[str, Any]:
        """Returns comprehensive detail view for a specific draft."""
        with self._lock:
            draft = self.get_draft_by_id(draft_id)
            data = draft.model_dump()
            
            # Additional analysis metadata
            risk_level = "LOW" if draft.confidence_score >= 0.85 else "MEDIUM" if draft.confidence_score >= 0.7 else "HIGH"
            data["risk_assessment"] = {
                "score": risk_level,
                "confidence_score": draft.confidence_score,
                "reason": f"Confidence score {draft.confidence_score:.2f} maps to {risk_level} risk level."
            }
            data["current_odoo_state"] = None
            data["diff"] = {
                "type": "NEW_RECORD" if draft.action_type == "create" else "UPDATE",
                "proposed": mask_sensitive_data(draft.proposed_payload)
            }
            return data

    # ==========================================
    # VOBO WORKFLOW LIFECYCLE API
    # ==========================================

    def get_pending_drafts(
        self,
        agent_filter: Optional[str] = None,
        min_confidence: float = 0.0,
        status_filter: Optional[str] = "pending_vobo"
    ) -> List[DraftAction]:
        """
        Retrieves staged DraftActions filtered by agent name, minimum confidence threshold, and status.
        Defaults to status_filter='pending_vobo'.
        Returns list ordered by creation timestamp (newest first).
        """
        with self._lock:
            drafts = list(self._draft_queue.values())

            if agent_filter:
                drafts = [d for d in drafts if d.agent_name == agent_filter]

            if min_confidence > 0.0:
                drafts = [d for d in drafts if d.confidence_score >= min_confidence]

            if status_filter and status_filter != "all":
                drafts = [d for d in drafts if d.status == status_filter]

            # Sort newest first
            drafts.sort(key=lambda d: d.created_at, reverse=True)
            return drafts

    def approve_draft(
        self,
        draft_id: str,
        supervisor_id: str,
        justification: str = ""
    ) -> Dict[str, Any]:
        """
        Executes Supervisor VoBo approval for a pending draft.
        Commits payload to Odoo ERP (if client connected), updates status, and records audit entry.
        """
        if not supervisor_id or not supervisor_id.strip():
            raise ValueError("supervisor_id is required and cannot be empty")

        with self._lock:
            draft = self.get_draft_by_id(draft_id)

            if draft.status != "pending_vobo":
                raise InvalidDraftStateError(
                    f"Cannot approve draft '{draft_id}': current status is '{draft.status}', expected 'pending_vobo'"
                )

            now_utc = datetime.now(timezone.utc).isoformat()
            odoo_record_id: Optional[Union[int, List[int]]] = None
            final_status = "approved"

            # Execute Odoo write strictly upon VoBo approval if client available
            if self.odoo_client is not None:
                try:
                    if hasattr(self.odoo_client, "draft_stager") and draft_id in self.odoo_client.draft_stager.drafts:
                        res = self.odoo_client.commit_draft(draft_id=draft_id, approved_by=supervisor_id)
                        odoo_record_id = res.get("odoo_record_id") or res.get("record_id")
                    elif hasattr(self.odoo_client, "create"):
                        odoo_record_id = self.odoo_client.create(
                            model=draft.target_model,
                            values=draft.proposed_payload
                        )
                    final_status = "committed"
                except Exception as e:
                    logger.error("Failed to commit approved draft '%s' to Odoo model '%s': %s",
                                 draft_id, draft.target_model, e)
                    raise

            # Update draft state in queue
            draft.status = final_status
            audit_entry_info = {
                "timestamp": now_utc,
                "action": "approved",
                "supervisor_id": supervisor_id,
                "justification": justification,
                "odoo_record_id": odoo_record_id
            }
            draft.audit_trail.append(audit_entry_info)

            # Record in immutable supervisor audit logger
            self.audit_logger.log_supervisor_action(
                draft_id=draft_id,
                supervisor_id=supervisor_id,
                verdict="approved",
                odoo_model=draft.target_model,
                odoo_record_id=odoo_record_id,
                justification=justification or draft.justification,
                agent_name=draft.agent_name,
                proposed_payload=draft.proposed_payload
            )

            return {
                "status": final_status,
                "draft_id": draft_id,
                "supervisor_id": supervisor_id,
                "target_model": draft.target_model,
                "odoo_model": draft.target_model,
                "odoo_record_id": odoo_record_id,
                "timestamp": now_utc,
                "justification": justification
            }

    def reject_draft(
        self,
        draft_id: str,
        supervisor_id: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Executes Supervisor VoBo rejection for a pending draft.
        Prevents execution in Odoo ERP, updates status to 'rejected', and records audit log.
        """
        if not supervisor_id or not supervisor_id.strip():
            raise ValueError("supervisor_id is required and cannot be empty")

        with self._lock:
            draft = self.get_draft_by_id(draft_id)

            if draft.status != "pending_vobo":
                raise InvalidDraftStateError(
                    f"Cannot reject draft '{draft_id}': current status is '{draft.status}', expected 'pending_vobo'"
                )

            now_utc = datetime.now(timezone.utc).isoformat()
            draft.status = "rejected"

            audit_entry_info = {
                "timestamp": now_utc,
                "action": "rejected",
                "supervisor_id": supervisor_id,
                "reason": reason
            }
            draft.audit_trail.append(audit_entry_info)

            # Record in immutable supervisor audit logger
            self.audit_logger.log_supervisor_action(
                draft_id=draft_id,
                supervisor_id=supervisor_id,
                verdict="rejected",
                odoo_model=draft.target_model,
                odoo_record_id=None,
                justification=reason,
                agent_name=draft.agent_name,
                proposed_payload=draft.proposed_payload
            )

            return {
                "status": "rejected",
                "draft_id": draft_id,
                "supervisor_id": supervisor_id,
                "target_model": draft.target_model,
                "odoo_model": draft.target_model,
                "odoo_record_id": None,
                "timestamp": now_utc,
                "reason": reason
            }

    def get_audit_logs(
        self,
        supervisor_id: Optional[str] = None,
        draft_id: Optional[str] = None,
        verdict: Optional[str] = None,
        odoo_model: Optional[str] = None,
        limit: Optional[int] = 50
    ) -> List[Dict[str, Any]]:
        """Returns list of audit dictionaries logged by supervisor actions."""
        entries = self.audit_logger.query_logs(
            supervisor_id=supervisor_id,
            draft_id=draft_id,
            verdict=verdict,
            odoo_model=odoo_model,
            limit=limit
        )
        return [entry.to_dict() for entry in entries]

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistical overview of supervisor draft queue state."""
        with self._lock:
            drafts = list(self._draft_queue.values())
            status_counts = {"pending_vobo": 0, "approved": 0, "rejected": 0, "committed": 0}
            agent_counts: Dict[str, int] = {}
            model_counts: Dict[str, int] = {}

            for d in drafts:
                status_counts[d.status] = status_counts.get(d.status, 0) + 1
                agent_counts[d.agent_name] = agent_counts.get(d.agent_name, 0) + 1
                model_counts[d.target_model] = model_counts.get(d.target_model, 0) + 1

            return {
                "total_drafts": len(drafts),
                "by_status": status_counts,
                "by_agent": agent_counts,
                "by_model": model_counts
            }
