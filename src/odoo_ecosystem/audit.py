"""
Security Credential Management, Audit Logger, and Draft Staging Engine.
Enforces credential masking, structured JSONL audit logging, and 0% auto-execution draft staging.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
import json
import os
import uuid
import logging
import threading

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "authorization",
    "cookie", "pwd", "pass", "private_key"
}


def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive credential keys in dictionaries, lists, and tuples."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in SENSITIVE_KEYS):
                masked[k] = "***REDACTED***"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, (list, tuple)):
        return [mask_sensitive_data(item) for item in data]
    return data


class CredentialManager:
    """Manages Odoo connection credentials with automatic masking."""

    def __init__(self, env_dict: Optional[Dict[str, str]] = None):
        self.env = env_dict or dict(os.environ)

    def get_credentials(self) -> Dict[str, Any]:
        url = self.env.get("ODOO_URL", "http://localhost:8069")
        db = self.env.get("ODOO_DB", "odoo_db")
        username = self.env.get("ODOO_USERNAME", "admin")
        password = self.env.get("ODOO_PASSWORD", "admin")
        api_key = self.env.get("ODOO_API_KEY", None)

        raw = {
            "url": url,
            "db": db,
            "username": username,
            "password": password,
            "api_key": api_key
        }
        return raw

    def get_masked_credentials(self) -> Dict[str, Any]:
        """Return credentials with sensitive fields redacted."""
        return mask_sensitive_data(self.get_credentials())


@dataclass
class AuditLogEntry:
    """Structured representation of an Odoo API call audit log entry."""
    request_id: str
    timestamp: str
    protocol: str
    odoo_version: str
    endpoint: str
    model: str
    method: str
    domain: Optional[List[Any]]
    fields: Optional[List[str]]
    payload_size_bytes: int
    response_time_ms: float
    status: str  # SUCCESS, RATE_LIMITED, AUTH_ERROR, SERVER_ERROR, ERROR
    http_status_code: int
    user_agent_id: str
    error_details: Optional[str] = None


class AuditLogger:
    """JSONL Recorder for outgoing Odoo RPC/REST calls with credential redaction."""

    def __init__(self, log_file_path: str = ".agents/audit_logs/odoo_api.jsonl"):
        self.log_file_path = log_file_path
        self.memory_entries: List[AuditLogEntry] = []
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

    def log_call(self, entry: AuditLogEntry):
        # Mask sensitive info inside domain or error details
        entry.domain = mask_sensitive_data(entry.domain)
        if entry.error_details:
            entry.error_details = str(mask_sensitive_data(entry.error_details))

        with self._lock:
            self.memory_entries.append(entry)
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning("Failed to write audit log to file: %s", str(e))

    def get_entries_by_model(self, model: str) -> List[AuditLogEntry]:
        with self._lock:
            return [e for e in self.memory_entries if e.model == model]

    def clear(self):
        with self._lock:
            self.memory_entries.clear()


@dataclass
class DraftRecord:
    """Dataclass representing a staged draft mutation pending VoBo approval."""
    draft_id: str
    created_at: str
    agent_id: str
    target_model: str
    operation_type: str  # create, write, unlink
    payload: Dict[str, Any]
    state: str  # PENDING_APPROVAL, APPROVED, REJECTED, COMMITTED
    vobo_details: Optional[Dict[str, Any]] = None
    committed_at: Optional[str] = None
    odoo_record_id: Optional[Union[int, List[int]]] = None


class DraftStager:
    """0% Auto-Execution Draft Staging Engine."""

    def __init__(self, storage_path: str = ".agents/drafts/staged_drafts.json"):
        self.storage_path = storage_path
        self.drafts: Dict[str, DraftRecord] = {}
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._load_drafts()

    def _load_drafts(self):
        with self._lock:
            if os.path.exists(self.storage_path):
                try:
                    with open(self.storage_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for draft_id, item in data.items():
                            self.drafts[draft_id] = DraftRecord(**item)
                except Exception as e:
                    logger.warning("Failed to load staged drafts: %s", str(e))

    def _save_drafts(self):
        with self._lock:
            try:
                data = {k: asdict(v) for k, v in self.drafts.items()}
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning("Failed to save staged drafts: %s", str(e))

    def create_draft(self, agent_id: str, model: str, operation_type: str, payload: Dict[str, Any]) -> DraftRecord:
        with self._lock:
            draft_id = f"draft_{uuid.uuid4().hex[:12]}"
            now_str = datetime.now(timezone.utc).isoformat()
            draft = DraftRecord(
                draft_id=draft_id,
                created_at=now_str,
                agent_id=agent_id,
                target_model=model,
                operation_type=operation_type,
                payload=mask_sensitive_data(payload),
                state="PENDING_APPROVAL"
            )
            self.drafts[draft_id] = draft
            self._save_drafts()
            return draft

    def approve_draft(self, draft_id: str, approved_by: str, vobo_notes: str = "") -> DraftRecord:
        with self._lock:
            if draft_id not in self.drafts:
                raise KeyError(f"Draft ID {draft_id} not found in staged store")
            draft = self.drafts[draft_id]
            if draft.state == "COMMITTED":
                raise ValueError(f"Draft {draft_id} is already committed")
            draft.state = "APPROVED"
            draft.vobo_details = {
                "approved_by": approved_by,
                "vobo_notes": vobo_notes,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._save_drafts()
            return draft

    def reject_draft(self, draft_id: str, rejected_by: str, reason: str = "") -> DraftRecord:
        with self._lock:
            if draft_id not in self.drafts:
                raise KeyError(f"Draft ID {draft_id} not found in staged store")
            draft = self.drafts[draft_id]
            draft.state = "REJECTED"
            draft.vobo_details = {
                "rejected_by": rejected_by,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._save_drafts()
            return draft
