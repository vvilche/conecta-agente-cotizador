# Architectural Analysis & Concrete Design Specification: Supervisor Human-in-the-Loop Web Console (Milestone 4)

**Author**: Explorer 1 (Milestone 4)  
**Date**: 2026-07-28  
**Working Directory**: `.agents/explorer_m4_1/`  
**Target Module Scope**: `src/supervisor_ui/console.py` and `src/supervisor_ui/audit_logger.py`

---

## 1. Executive Summary & Architectural Scope

The **Supervisor Human-in-the-Loop Web Console** serves as the central control plane and safety gateway for the entire *Sistema Agenticio Inteligente Ecosistémico para Odoo ERP*. 

### Key Architectural Invariant: 0% Auto-Execution Enforcement
As specified in `PROJECT.md` and `ORIGINAL_REQUEST.md`, **no specialized agent in `swarm_engine` is permitted to execute write/create/unlink operations directly on the Odoo ERP database**. All operational actions proposed by agents are packaged as staged `DraftAction` instances with initial status strictly defaulting to `"pending_vobo"`.

The Supervisor Web Console is the **sole authorization mechanism** capable of approving (`approve_draft`) or rejecting (`reject_draft`) staged actions.

### Mission & Deliverables
This analysis defines the backend architecture, object model, thread-safe persistence mechanics, and exact code specification for two primary core classes:
1. **`SupervisorConsole`** (`src/supervisor_ui/console.py`): The central engine managing pending draft queue state, querying staged `DraftAction` items from `AgentSwarm` or persistent draft stores, executing `OdooClient.commit_draft(...)` upon approval, and enforcing VoBo lifecycle state transitions.
2. **`AuditLogger`** (`src/supervisor_ui/audit_logger.py`): Immutable, persistent JSONL storage recording all supervisor VoBo verdicts (`draft_id`, `supervisor_id`, `verdict`, `timestamp`, `odoo_model`, `odoo_record_id`, `justification`) with thread safety and credential masking.

---

## 2. Interface Contracts & Data Flow

### 2.1 System Integration Topology

```
+-------------------------------------------------------------------------+
|                        Swarm Agentic Engine                             |
|  (RFQ, Cotización, Operaciones, Estados Pago, Doc, Conciliador)        |
+-------------------------------------------------------------------------+
                                    |
                                    | Generates DraftAction (status="pending_vobo")
                                    v
+-------------------------------------------------------------------------+
|                   SupervisorConsole (console.py)                        |
|                                                                         |
|  - Pending Queue State Management (in-memory + DraftStager persistence)|
|  - get_pending_drafts(agent_filter, status_filter)                      |
|  - approve_draft(draft_id, supervisor_id, justification)                |
|  - reject_draft(draft_id, supervisor_id, reason)                        |
+-------------------------------------------------------------------------+
                 |                                          |
                 | Executes OdooClient.commit_draft(...)    | Logs VoBo Audit Entry
                 v                                          v
+-----------------------------------+     +-----------------------------------+
|      OdooClient (client.py)       |     |  Supervisor AuditLogger (jsonl)   |
|                                   |     |                                   |
| Writes record to Odoo DB on VoBo  |     | Immutable JSONL append log for    |
| approval; returns record_id       |     | supervisor accountability & audit |
+-----------------------------------+     +-----------------------------------+
```

### 2.2 Domain Entities & Schemas

#### A. Existing `DraftAction` Schema (`swarm_engine.base_agent`)
- `draft_id`: `str` (e.g. `"draft_a1b2c3d4e5f6"`)
- `agent_name`: `str` (e.g. `"rfq_prospeccion"`, `"cotizacion_inventario"`)
- `target_model`: `str` (e.g. `"crm.lead"`, `"sale.order"`, `"account.move"`)
- `action_type`: `Literal["create", "write", "unlink", "custom_operation"]`
- `proposed_payload`: `Dict[str, Any]`
- `justification`: `str`
- `confidence_score`: `float` (0.0 to 1.0)
- `status`: `Literal["pending_vobo", "approved", "rejected", "committed"]`
- `created_at`: `str` (ISO 8601 UTC)
- `audit_trail`: `List[Dict[str, Any]]`
- `metadata`: `Dict[str, Any]`

#### B. Supervisor Audit Entry Schema (`SupervisorAuditEntry`)
- `audit_id`: `str` (e.g. `"sup_audit_1a2b3c4d"`)
- `draft_id`: `str`
- `supervisor_id`: `str` (ID/email/name of supervisor performing VoBo)
- `verdict`: `Literal["approved", "rejected"]`
- `timestamp`: `str` (ISO 8601 UTC timestamp)
- `odoo_model`: `str` (Target ERP model name)
- `odoo_record_id`: `Optional[Union[int, List[int]]]` (Returned ID from Odoo commit, or None if rejected)
- `justification`: `str` (Explanation or notes provided by supervisor)
- `agent_name`: `Optional[str]` (Agent that created the original draft)
- `masked_payload`: `Optional[Dict[str, Any]]` (Sanitized copy of proposed payload)

---

## 3. VoBo Workflow Lifecycle & State Machine

### 3.1 State Diagram

```
                 [ Agent Swarm Event ]
                           |
                           v
                    +--------------+
                    | pending_vobo | <--- Initial state for all drafts
                    +--------------+
                       /        \
       Supervisor     /          \     Supervisor
     approve_draft() /            \   reject_draft()
                    v              v
             +----------+    +----------+
             | approved |    | rejected |
             +----------+    +----------+
                  |               |
       OdooClient |               | No Odoo DB write
     commit_draft |               | Audit logged
                  v               v
            +-----------+      [ TERMINAL ]
            | committed |
            +-----------+
                  |
             [ TERMINAL ]
```

### 3.2 Method Contracts & Operational Semantics

#### 1. `get_pending_drafts(agent_filter: Optional[str] = None, status_filter: str = "pending_vobo") -> list[DraftAction]`
- **Behavior**: Filters the active draft queue by `agent_name` (if specified) and `status` (defaults to `"pending_vobo"`).
- **Sorting**: Returns drafts ordered by `created_at` descending (newest first).
- **Validation**: If `status_filter` is `"all"` or `None`, returns all drafts regardless of status.

#### 2. `approve_draft(draft_id: str, supervisor_id: str, justification: str = "") -> dict`
- **Preconditions**:
  1. Draft `draft_id` must exist in memory/store.
  2. Draft status must be `"pending_vobo"` (cannot re-approve an already approved or rejected draft).
  3. `supervisor_id` must be non-empty string.
- **Execution Steps**:
  1. Update draft status to `"approved"`.
  2. If `OdooClient` is present:
     - Invoke `odoo_client.commit_draft(draft_id=draft_id, approved_by=supervisor_id)` or `odoo_client.create(model=draft.target_model, values=draft.proposed_payload)`.
     - Capture returned `odoo_record_id`.
     - Update draft status to `"committed"`.
  3. Record audit log via `AuditLogger.log_supervisor_action(...)` with `verdict="approved"`.
  4. Append entry to `draft.audit_trail`.
- **Return Value**:
  ```python
  {
      "status": "approved" | "committed",
      "draft_id": draft_id,
      "supervisor_id": supervisor_id,
      "odoo_model": target_model,
      "odoo_record_id": record_id,
      "timestamp": iso_timestamp,
      "justification": justification
  }
  ```

#### 3. `reject_draft(draft_id: str, supervisor_id: str, reason: str = "") -> dict`
- **Preconditions**:
  1. Draft `draft_id` must exist.
  2. Draft status must be `"pending_vobo"`.
  3. `supervisor_id` must be non-empty string.
- **Execution Steps**:
  1. Update draft status to `"rejected"`.
  2. **Guarantee**: NO write operations sent to `OdooClient`.
  3. Record audit log via `AuditLogger.log_supervisor_action(...)` with `verdict="rejected"`.
  4. Append entry to `draft.audit_trail`.
- **Return Value**:
  ```python
  {
      "status": "rejected",
      "draft_id": draft_id,
      "supervisor_id": supervisor_id,
      "odoo_model": target_model,
      "odoo_record_id": None,
      "timestamp": iso_timestamp,
      "reason": reason
  }
  ```

---

## 4. Concrete Code Specification

Below are the exact production-ready Python implementations for `src/supervisor_ui/audit_logger.py` and `src/supervisor_ui/console.py`.

### 4.1 Specification for `src/supervisor_ui/audit_logger.py`

```python
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

    def query_logs(
        self,
        supervisor_id: Optional[str] = None,
        draft_id: Optional[str] = None,
        verdict: Optional[str] = None,
        odoo_model: Optional[str] = None
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
                results = [e for e in results if e.verdict == verdict]
            if odoo_model:
                results = [e for e in results if e.odoo_model == odoo_model]
            return results

    def clear(self) -> None:
        """Clears memory entries (primarily for testing fixtures)."""
        with self._lock:
            self._memory_entries.clear()
```

---

### 4.2 Specification for `src/supervisor_ui/console.py`

```python
"""
Supervisor Console Core Engine Module.
Manages the pending draft queue state, coordinates AgentSwarm output,
executes OdooClient commits upon supervisor VoBo approval, and records audit logs.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
import threading

from swarm_engine.base_agent import DraftAction
from swarm_engine.swarm import AgentSwarm
from odoo_ecosystem.client import OdooClient, OdooDraftError
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
        self.swarm = swarm
        self.odoo_client = odoo_client
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

    # ==========================================
    # VOBO WORKFLOW LIFECYCLE API
    # ==========================================

    def get_pending_drafts(
        self,
        agent_filter: Optional[str] = None,
        status_filter: Optional[str] = "pending_vobo"
    ) -> List[DraftAction]:
        """
        Retrieves staged DraftActions filtered by agent name and status.
        Defaults to status_filter='pending_vobo'.
        Returns list ordered by creation timestamp (newest first).
        """
        with self._lock:
            drafts = list(self._draft_queue.values())

            if agent_filter:
                drafts = [d for d in drafts if d.agent_name == agent_filter]

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
                    # Attempt commit_draft if present in client's draft_stager, else direct create
                    if hasattr(self.odoo_client, "create"):
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
                "odoo_record_id": None,
                "timestamp": now_utc,
                "reason": reason
            }

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
```

---

## 5. Verification Plan & Test Matrix

To ensure Tier 1–5 compliance, the implementation will be tested against the following test cases in `tests/test_supervisor_ui.py`:

| # | Test Name | Purpose | Expected Outcome |
|---|-----------|---------|------------------|
| 1 | `test_supervisor_audit_logger_persistence` | Verify `SupervisorAuditLogger` writes entries to JSONL file and reloads them accurately | File created, entries parsed match recorded events |
| 2 | `test_supervisor_audit_logger_credential_masking` | Verify sensitive fields in proposed payload are masked in audit log | `password` / `token` fields replaced with `"***REDACTED***"` |
| 3 | `test_get_pending_drafts_filtering` | Test filtering queue by `agent_filter` and `status_filter` | Only matching `DraftAction` items returned in creation order |
| 4 | `test_approve_draft_success_with_odoo` | Test `approve_draft` commits to Odoo via mock server and updates status | Status changes to `committed`, `odoo_record_id` returned |
| 5 | `test_approve_draft_without_odoo` | Test `approve_draft` when `odoo_client=None` | Status changes to `approved`, audit entry logged |
| 6 | `test_reject_draft_lifecycle` | Test `reject_draft` cancels execution and logs rejection reason | Status changes to `rejected`, NO write to Odoo DB |
| 7 | `test_prevent_double_approval_or_rejection` | Attempt to re-approve an approved or rejected draft | Raises `InvalidDraftStateError` |
| 8 | `test_missing_supervisor_id_validation` | Pass empty string for `supervisor_id` | Raises `ValueError` |
| 9 | `test_zero_auto_execution_supervisor_gate` | End-to-end check that agent outputs sit in queue until supervisor approves | DB record count unchanged until `approve_draft` is called |
| 10| `test_supervisor_console_thread_safety` | Concurrent approval requests on multiple threads | No race conditions or queue corruption |

---
