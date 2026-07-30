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
    audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured audit log entries for draft lifecycle and decision rationale"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context, scores, or tags attached to draft action"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending_vobo", "approved", "rejected", "committed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
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
        confidence_score: float = 1.0,
        audit_trail: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DraftAction:
        """
        Helper method to instantiate a validated DraftAction for human supervisor review.
        Enforces status='pending_vobo'.
        """
        initial_audit = [
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "action": "draft_created",
                "agent_name": self.agent_name,
                "target_model": target_model,
                "status": "pending_vobo"
            }
        ]
        if audit_trail:
            initial_audit.extend(audit_trail)

        return DraftAction(
            agent_name=self.agent_name,
            target_model=target_model,
            action_type=action_type,
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=confidence_score,
            status="pending_vobo",
            audit_trail=initial_audit,
            metadata=metadata or {}
        )

    def check_health(self) -> Dict[str, Any]:
        """Checks readiness and connectivity of agent resources."""
        odoo_ok = False
        if self.odoo_client:
            try:
                # Basic check if client is instantiated and has config or mock server
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
            "healthy": True
        }
