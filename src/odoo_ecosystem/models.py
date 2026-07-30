"""
Pydantic v2 Models for Odoo Ecosystem Abstractions.
Covers CRM & Sales, Projects & Operations, and Finance & Budgets.
"""

from typing import List, Optional, Union, Tuple, Any, Dict
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


def extract_m2o_id(val: Any) -> Optional[int]:
    """Helper to extract integer ID from Odoo Many2one field ([id, name] or int)."""
    if isinstance(val, (list, tuple)) and len(val) > 0:
        return int(val[0])
    elif isinstance(val, int):
        return val
    return None


def extract_m2o_name(val: Any) -> Optional[str]:
    """Helper to extract display name string from Odoo Many2one field ([id, name])."""
    if isinstance(val, (list, tuple)) and len(val) > 1:
        return str(val[1])
    return None


class OdooBaseModel(BaseModel):
    """Base class for all Odoo entity abstractions."""
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[int] = Field(default=None, description="Odoo Database Primary Key ID")

    def to_odoo_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert model into dict suitable for Odoo RPC calls."""
        raw = self.model_dump(exclude_none=exclude_none)
        out = {}
        for k, v in raw.items():
            if isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], int) and isinstance(v[1], str):
                # Many2one field tuple [id, name] -> extract ID for write/create
                out[k] = v[0]
            elif isinstance(v, (date, datetime)):
                out[k] = v.isoformat()
            else:
                out[k] = v
        return out

    @classmethod
    def from_odoo_dict(cls, raw: Dict[str, Any]) -> "OdooBaseModel":
        """Construct model instance from Odoo dictionary response."""
        cleaned = {}
        fields_map = cls.model_fields
        for field_name, val in raw.items():
            if field_name in fields_map:
                # Handle False returned by Odoo for unset fields
                if val is False:
                    cleaned[field_name] = None
                else:
                    cleaned[field_name] = val
        return cls(**cleaned)


# ==========================================
# 1. CRM & SALES DOMAIN
# ==========================================

class ResPartner(OdooBaseModel):
    """Abstraction for res.partner (Customers, Vendors, Contacts)."""
    name: str = Field(..., description="Partner Name or Company Name")
    is_company: bool = Field(default=False, description="True if partner is a legal entity")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    vat: Optional[str] = Field(default=None, description="Tax ID / RUT")
    street: Optional[str] = Field(default=None, description="Street Address")
    city: Optional[str] = Field(default=None, description="City")
    country_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Country Many2one")
    credit_limit: float = Field(default=0.0, description="Credit Limit")
    active: bool = Field(default=True, description="Active status")


class CrmLead(OdooBaseModel):
    """Abstraction for crm.lead (Opportunities & Leads)."""
    name: str = Field(..., description="Lead / Opportunity Subject")
    partner_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Associated Customer Many2one")
    email_from: Optional[str] = Field(default=None, description="Contact Email")
    phone: Optional[str] = Field(default=None, description="Contact Phone")
    expected_revenue: float = Field(default=0.0, description="Expected Revenue")
    probability: float = Field(default=0.0, description="Win Probability Percentage")
    stage_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Pipeline Stage Many2one")
    user_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Assigned Salesperson Many2one")
    description: Optional[str] = Field(default=None, description="Internal Notes / Scope")
    type: str = Field(default="opportunity", description="Type: 'lead' or 'opportunity'")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = ("lead", "opportunity")
        if v not in valid_types:
            raise ValueError(f"Invalid lead type '{v}'. Must be one of {valid_types}")
        return v


class SaleOrderLine(OdooBaseModel):
    """Abstraction for sale.order.line."""
    order_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Parent Order Many2one")
    product_id: Union[int, Tuple[int, str], List[Any]] = Field(..., description="Product Many2one")
    name: str = Field(..., description="Line Description")
    product_uom_qty: float = Field(default=1.0, description="Quantity Ordered")
    price_unit: float = Field(default=0.0, description="Unit Price")
    price_subtotal: float = Field(default=0.0, description="Subtotal without taxes")
    price_total: float = Field(default=0.0, description="Total with taxes")


class SaleOrder(OdooBaseModel):
    """Abstraction for sale.order (Quotations / Sales Orders)."""
    name: str = Field(default="/", description="Order Reference (e.g. SO001)")
    partner_id: Union[int, Tuple[int, str], List[Any]] = Field(..., description="Customer Many2one")
    date_order: Optional[Union[datetime, date, str]] = Field(default=None, description="Order Date")
    state: str = Field(default="draft", description="Order State: draft | sent | sale | done | cancel")
    amount_untaxed: float = Field(default=0.0, description="Untaxed Amount")
    amount_tax: float = Field(default=0.0, description="Tax Amount")
    amount_total: float = Field(default=0.0, description="Total Amount")
    order_line: List[Union[int, SaleOrderLine, Dict[str, Any]]] = Field(default_factory=list, description="Order Lines")
    analytic_account_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Analytic Account Many2one")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = ("draft", "sent", "sale", "done", "cancel")
        if v not in valid_states:
            raise ValueError(f"Invalid SaleOrder state '{v}'. Must be one of {valid_states}")
        return v


# ==========================================
# 2. PROJECTS & OPERATIONS DOMAIN
# ==========================================

class AccountAnalyticAccount(OdooBaseModel):
    """Abstraction for account.analytic.account (Cost Centers / Operational Accounts)."""
    name: str = Field(..., description="Analytic Account Name")
    code: Optional[str] = Field(default=None, description="Code / Reference")
    partner_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Customer Many2one")
    balance: float = Field(default=0.0, description="Current Balance")
    debit: float = Field(default=0.0, description="Cumulative Debit")
    credit: float = Field(default=0.0, description="Cumulative Credit")


class ProjectProject(OdooBaseModel):
    """Abstraction for project.project."""
    name: str = Field(..., description="Project Name")
    partner_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Customer Many2one")
    user_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Project Manager Many2one")
    analytic_account_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Linked Analytic Account Many2one")
    privacy_visibility: str = Field(default="portal", description="Visibility: portal | employees | followers")
    active: bool = Field(default=True, description="Active status")
    date_start: Optional[Union[date, str]] = Field(default=None, description="Start Date")
    date: Optional[Union[date, str]] = Field(default=None, description="End Date")


class ProjectTask(OdooBaseModel):
    """Abstraction for project.task."""
    name: str = Field(..., description="Task Name")
    project_id: Union[int, Tuple[int, str], List[Any]] = Field(..., description="Parent Project Many2one")
    partner_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Customer Many2one")
    user_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Assigned Employee Many2one")
    stage_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Task Stage Many2one")
    planned_hours: float = Field(default=0.0, description="Planned Hours")
    effective_hours: float = Field(default=0.0, description="Executed Hours")
    remaining_hours: float = Field(default=0.0, description="Remaining Hours")
    kanban_state: str = Field(default="normal", description="State: normal | blocked | done")
    progress: float = Field(default=0.0, description="Progress Percentage")
    description: Optional[str] = Field(default=None, description="Detailed Description")

    @field_validator("kanban_state")
    @classmethod
    def validate_kanban_state(cls, v: str) -> str:
        valid_states = ("normal", "blocked", "done")
        if v not in valid_states:
            raise ValueError(f"Invalid kanban_state '{v}'. Must be one of {valid_states}")
        return v


# ==========================================
# 3. FINANCE & BUDGETS DOMAIN
# ==========================================

class CrossoveredBudgetLines(OdooBaseModel):
    """Abstraction for crossovered.budget.lines."""
    crossovered_budget_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Parent Budget Many2one")
    analytic_account_id: Union[int, Tuple[int, str], List[Any]] = Field(..., description="Analytic Cost Center Many2one")
    general_budget_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Budget Position Many2one")
    date_from: Union[date, str] = Field(..., description="Line Start Date")
    date_to: Union[date, str] = Field(..., description="Line End Date")
    planned_amount: float = Field(default=0.0, description="Planned Amount")
    practical_amount: float = Field(default=0.0, description="Executed Practical Amount")
    theoritical_amount: float = Field(default=0.0, description="Theoretical Progress Amount")
    percentage: float = Field(default=0.0, description="Achievement Percentage")


class CrossoveredBudget(OdooBaseModel):
    """Abstraction for crossovered.budget."""
    name: str = Field(..., description="Budget Title / Period")
    user_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Responsible Manager Many2one")
    date_from: Union[date, str] = Field(..., description="Budget Period Start")
    date_to: Union[date, str] = Field(..., description="Budget Period End")
    state: str = Field(default="draft", description="State: draft | confirm | validate | done | cancel")
    crossovered_budget_line: List[Union[int, CrossoveredBudgetLines, Dict[str, Any]]] = Field(default_factory=list, description="Budget Lines")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = ("draft", "confirm", "validate", "done", "cancel")
        if v not in valid_states:
            raise ValueError(f"Invalid CrossoveredBudget state '{v}'. Must be one of {valid_states}")
        return v


class AccountMoveLine(OdooBaseModel):
    """Abstraction for account.move.line (Invoice & DTE Lines)."""
    move_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Parent Move/Invoice Many2one")
    name: str = Field(..., description="Item / Service Label")
    product_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Product Many2one")
    quantity: float = Field(default=1.0, description="Quantity")
    price_unit: float = Field(default=0.0, description="Unit Price")
    debit: float = Field(default=0.0, description="Debit Amount")
    credit: float = Field(default=0.0, description="Credit Amount")
    price_subtotal: float = Field(default=0.0, description="Subtotal Amount")
    analytic_account_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Analytic Account Many2one")


class AccountMove(OdooBaseModel):
    """Abstraction for account.move (Invoices, Credit Notes, DTEs)."""
    name: str = Field(default="/", description="Invoice Number / DTE Folio")
    ref: Optional[str] = Field(default=None, description="Reference / PO Number")
    move_type: str = Field(..., description="Type: out_invoice | out_refund | in_invoice | in_refund | entry")
    partner_id: Union[int, Tuple[int, str], List[Any]] = Field(..., description="Partner Many2one")
    invoice_date: Optional[Union[date, str]] = Field(default=None, description="Invoice Date")
    state: str = Field(default="draft", description="State: draft | posted | cancel")
    amount_untaxed: float = Field(default=0.0, description="Untaxed Amount")
    amount_tax: float = Field(default=0.0, description="Tax Amount")
    amount_total: float = Field(default=0.0, description="Total Amount")
    payment_state: str = Field(default="not_paid", description="Payment Status: not_paid | in_payment | paid | partial")
    invoice_line_ids: List[Union[int, AccountMoveLine, Dict[str, Any]]] = Field(default_factory=list, description="Invoice Lines")

    @field_validator("move_type")
    @classmethod
    def validate_move_type(cls, v: str) -> str:
        valid_types = ("out_invoice", "out_refund", "in_invoice", "in_refund", "entry")
        if v not in valid_types:
            raise ValueError(f"Invalid move_type '{v}'. Must be one of {valid_types}")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = ("draft", "posted", "cancel")
        if v not in valid_states:
            raise ValueError(f"Invalid AccountMove state '{v}'. Must be one of {valid_states}")
        return v


class AccountPayment(OdooBaseModel):
    """Abstraction for account.payment."""
    name: str = Field(default="/", description="Payment Reference")
    payment_type: str = Field(..., description="Type: inbound | outbound")
    partner_type: str = Field(default="customer", description="Partner Type: customer | supplier")
    partner_id: Union[int, Tuple[int, str], List[Any]] = Field(..., description="Partner Many2one")
    amount: float = Field(..., description="Payment Amount")
    currency_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Currency Many2one")
    date: Union[date, str] = Field(..., description="Payment Date")
    state: str = Field(default="draft", description="State: draft | posted | reconciled | cancelled")
    ref: Optional[str] = Field(default=None, description="Memo / Bank Voucher Reference")
    journal_id: Optional[Union[int, Tuple[int, str], List[Any]]] = Field(default=None, description="Payment Journal Many2one")

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        valid_types = ("inbound", "outbound")
        if v not in valid_types:
            raise ValueError(f"Invalid payment_type '{v}'. Must be one of {valid_types}")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = ("draft", "posted", "reconciled", "cancelled")
        if v not in valid_states:
            raise ValueError(f"Invalid AccountPayment state '{v}'. Must be one of {valid_states}")
        return v
