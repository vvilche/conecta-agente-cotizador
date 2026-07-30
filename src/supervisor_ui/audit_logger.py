"""
Supervisor Audit Logger Module for Human-in-the-Loop Web Console.
Provides persistent, immutable JSONL log storage for supervisor VoBo actions
(approvals and rejections) with thread safety and sensitive data masking.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Union, Literal
from datetime import datetime, timezone
import json
import os
import uuid
import logging
import threading

from odoo_ecosystem.audit import mask_sensitive_data

logger = logging.getLogger(__name__)


@dataclass
class SupervisorAuditEntry:
    """
    Structured immutable representation of a Supervisor VoBo audit event.
    """
    audit_id: str
    draft_id: str
    supervisor_id: str
    verdict: Literal["approved", "rejected"]
    timestamp: str
    odoo_model: str
    odoo_record_id: Optional[Union[int, List[int]]]
    justification: str
    agent_name: Optional[str] = None
    masked_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to plain dictionary."""
        return asdict(self)


class SupervisorAuditLogger:
    """
    Persistent, thread-safe JSONL recorder for Supervisor VoBo approval/rejection actions.
    Ensures absolute immutability and credential masking for compliance auditability.
    """

    def __init__(self, log_file_path: str = ".agents/audit_logs/supervisor_vobo_audit.jsonl"):
        self.log_file_path = log_file_path
        self._memory_entries: List[SupervisorAuditEntry] = []
        self._lock = threading.RLock()
        
        # Ensure log directory exists
        log_dir = os.path.dirname(os.path.abspath(self.log_file_path))
        os.makedirs(log_dir, exist_ok=True)
        self._load_existing_logs()

    def _load_existing_logs(self) -> None:
        """Loads historical entries from JSONL file into memory on startup."""
        with self._lock:
            if os.path.exists(self.log_file_path):
                try:
                    with open(self.log_file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                data = json.loads(line)
                                entry = SupervisorAuditEntry(**data)
                                self._memory_entries.append(entry)
                except Exception as e:
                    logger.warning("Failed to load existing supervisor audit logs from '%s': %s", self.log_file_path, e)

    def log_supervisor_action(
        self,
        draft_id: str,
        supervisor_id: str,
        verdict: Literal["approved", "rejected"],
        odoo_model: str,
        odoo_record_id: Optional[Union[int, List[int]]] = None,
        justification: str = "",
        agent_name: Optional[str] = None,
        proposed_payload: Optional[Dict[str, Any]] = None
    ) -> SupervisorAuditEntry:
        """
        Creates, logs, and persists an immutable supervisor VoBo audit entry.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        audit_id = f"sup_audit_{uuid.uuid4().hex[:12]}"
        
        # Redact sensitive fields from payload
        masked_payload = mask_sensitive_data(proposed_payload) if proposed_payload else None

        entry = SupervisorAuditEntry(
            audit_id=audit_id,
            draft_id=draft_id,
            supervisor_id=supervisor_id,
            verdict=verdict,
            timestamp=now_utc,
            odoo_model=odoo_model,
            odoo_record_id=odoo_record_id,
            justification=justification,
            agent_name=agent_name,
            masked_payload=masked_payload
        )

        with self._lock:
            self._memory_entries.append(entry)
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Failed to append supervisor audit log entry to file '%s': %s", self.log_file_path, e)

        return entry

    def log_operations_event(self, action_type: str, details: Dict[str, Any]) -> SupervisorAuditEntry:
        """
        Records operations audit events (e.g. document generation, FAT/SAT tests, kitting, accreditation, etc.).
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        audit_id = f"ops_audit_{uuid.uuid4().hex[:12]}"
        draft_id = str(details.get("ot_code") or details.get("draft_id") or details.get("kit_id") or "operations_engine")
        
        masked_payload = mask_sensitive_data(details) if details else None

        entry = SupervisorAuditEntry(
            audit_id=audit_id,
            draft_id=draft_id,
            supervisor_id="SYSTEM_OPERATIONS",
            verdict="approved",
            timestamp=now_utc,
            odoo_model=action_type,
            odoo_record_id=None,
            justification=f"Operations action executed: {action_type}",
            agent_name="operations_engine",
            masked_payload=masked_payload
        )

        with self._lock:
            self._memory_entries.append(entry)
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Failed to append operations audit log entry to file '%s': %s", self.log_file_path, e)

        return entry

    def query_logs(
        self,
        supervisor_id: Optional[str] = None,
        draft_id: Optional[str] = None,
        verdict: Optional[str] = None,
        odoo_model: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SupervisorAuditEntry]:
        """
        Queries in-memory audit log history filtered by matching criteria.
        """
        with self._lock:
            results = list(self._memory_entries)
            if supervisor_id:
                results = [e for e in results if e.supervisor_id == supervisor_id]
            if draft_id:
                results = [e for e in results if e.draft_id == draft_id]
            if verdict:
                v_lower = verdict.lower()
                results = [e for e in results if e.verdict.lower() == v_lower]
            if odoo_model:
                results = [e for e in results if e.odoo_model == odoo_model]
            
            if limit and limit > 0:
                results = results[:limit]
            return results

    def clear(self) -> None:
        """Clears memory entries (primarily for testing fixtures)."""
        with self._lock:
            self._memory_entries.clear()
