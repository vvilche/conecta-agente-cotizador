"""
Odoo Ecosystem Core Module.
Provides multi-protocol connector, Pydantic v2 domain models, mock server, and audit staging.
"""

from odoo_ecosystem.models import (
    OdooBaseModel,
    ResPartner,
    CrmLead,
    SaleOrderLine,
    SaleOrder,
    AccountAnalyticAccount,
    ProjectProject,
    ProjectTask,
    CrossoveredBudgetLines,
    CrossoveredBudget,
    AccountMoveLine,
    AccountMove,
    AccountPayment,
)
from odoo_ecosystem.client import (
    OdooClient,
    OdooConfig,
    OdooClientError,
    OdooAuthenticationError,
    OdooConnectionError,
    OdooRPCError,
    OdooDraftError,
    OdooMaxRetriesExceededError,
)
from odoo_ecosystem.mock_server import (
    MockOdooDB,
    MockOdooServer,
    DomainEvaluator,
    FaultInjectionConfig,
)
from odoo_ecosystem.audit import (
    CredentialManager,
    AuditLogger,
    AuditLogEntry,
    DraftStager,
    DraftRecord,
    mask_sensitive_data,
)

__all__ = [
    "OdooBaseModel",
    "ResPartner",
    "CrmLead",
    "SaleOrderLine",
    "SaleOrder",
    "AccountAnalyticAccount",
    "ProjectProject",
    "ProjectTask",
    "CrossoveredBudgetLines",
    "CrossoveredBudget",
    "AccountMoveLine",
    "AccountMove",
    "AccountPayment",
    "OdooClient",
    "OdooConfig",
    "OdooClientError",
    "OdooAuthenticationError",
    "OdooConnectionError",
    "OdooRPCError",
    "OdooDraftError",
    "OdooMaxRetriesExceededError",
    "MockOdooDB",
    "MockOdooServer",
    "DomainEvaluator",
    "FaultInjectionConfig",
    "CredentialManager",
    "AuditLogger",
    "AuditLogEntry",
    "DraftStager",
    "DraftRecord",
    "mask_sensitive_data",
]
