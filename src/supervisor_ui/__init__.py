"""
Supervisor Human-in-the-Loop Web Console Package.
Enforces 0% auto-execution compliance for specialized agent operational drafts,
provides supervisor VoBo approval workflows, JSONL audit logging, and REST API UI.
"""

from supervisor_ui.audit_logger import SupervisorAuditLogger, SupervisorAuditEntry
from supervisor_ui.console import SupervisorConsole, DraftNotFoundError, InvalidDraftStateError
from supervisor_ui.app import create_app

__all__ = [
    "SupervisorConsole",
    "SupervisorAuditLogger",
    "SupervisorAuditEntry",
    "DraftNotFoundError",
    "InvalidDraftStateError",
    "create_app"
]
