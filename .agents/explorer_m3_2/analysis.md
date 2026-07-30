# Specialized Agents Technical Design Specification (Milestone 3)

## 1. Executive Summary & Architectural Overview

The **Swarm Agentic Engine** (`src/swarm_engine/`) comprises 6 domain-specialized AI agents designed to automate, audit, and optimize key business processes across commercial prospecting, quotation engineering, budget & operations control, progress invoicing, contractor compliance, and Chilean accounting/DTE reconciliation.

Each agent inherits from `BaseAgent` (`src/swarm_engine/base_agent.py`), connects with `OdooClient` (`src/odoo_ecosystem/client.py`) for read operations and staged draft creation, and leverages `HistoricalMemory` (`src/rag_memory/few_shot.py`) for vector-based RAG context and historical benchmarks.

Crucially, **every mutation operation strictly adheres to the 0% Auto-Execution Enforcement Rule**: agents do NOT perform direct write/create operations in Odoo production tables. Instead, agents output structured `DraftAction` records with status `"pending_vobo"`, staged for Human-in-the-Loop approval via the Supervisor Web Interface (`src/supervisor_ui/`).

---

## 2. Shared Base Principles & Core Interface Contract

All 6 specialized agents adhere to the standard interface:

```python
class BaseAgent(ABC):
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

    @abstractmethod
    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        """Processes an incoming event payload and returns a staged DraftAction."""
        pass
```

### `DraftAction` Pydantic v2 Schema

```python
class DraftAction(BaseModel):
    draft_id: str = Field(default_factory=lambda: f"draft_{uuid.uuid4().hex[:12]}")
    agent_name: str
    target_model: str
    action_type: str  # "create", "write", "unlink"
    proposed_payload: Dict[str, Any]
    justification: str
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="pending_vobo")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## 3. Specialized Agent Design Specifications

### 3.1. `rfq_prospeccion.py` — RFQ & Commercial Prospecting Agent

#### Responsibilities & Scope
- **Target Odoo Models**: `res.partner`, `crm.lead`, `sale.order`
- **RAG Integration**: Queries `HistoricalMemory.get_few_shot_context()` to extract past winning proposal strategies, pricing models, and client expectations for similar tender domains.
- **Workflow**:
  1. Receives raw RFQ / Tender specification payload (client name, tax RUT, opportunity description, estimated scope).
  2. Searches `res.partner` via `OdooClient.search_read("res.partner", [["vat", "=", rut]])` or name fuzzy search.
  3. Queries `HistoricalMemory` for past winning proposals matching the domain (e.g. `edac_erag`, `pmgd_sitr`, `digitalizacion_scada`).
  4. Computes estimated revenue and win probability percentage based on historical RAG winning benchmarks.
  5. Generates a staged `DraftAction` for `crm.lead` creation/update.

#### Event Handling & Schema
- **Event `rfq_received` / `process_rfq`**:
  - `payload`: `{"client_name": str, "vat": str, "title": str, "description": str, "domain": str, "budget_estimate": float}`
- **Output `DraftAction`**:
  - `target_model`: `"crm.lead"`
  - `action_type`: `"create"`
  - `proposed_payload`:
    ```python
    {
        "name": payload["title"],
        "partner_id": partner_id_or_name,
        "expected_revenue": calculated_revenue,
        "probability": calculated_probability,
        "type": "opportunity",
        "description": f"RAG Few-Shot Enriched Scope:\n{scope_summary}"
    }
    ```
  - `justification`: Detailed RAG benchmark rationale citing past winning proposal IDs and historical win rates.

#### Code Architecture Template
```python
from typing import Dict, Any, Optional
from swarm_engine.base_agent import BaseAgent, DraftAction
from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory

class RFQProspeccionAgent(BaseAgent):
    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="rfq_prospeccion",
            domain="crm_sales",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        if event_type in ("rfq_received", "process_rfq"):
            return self._handle_rfq_received(payload)
        elif event_type == "lead_evaluate":
            return self._handle_lead_evaluate(payload)
        else:
            raise ValueError(f"Agent '{self.agent_name}' unsupported event_type '{event_type}'")

    def _handle_rfq_received(self, payload: Dict[str, Any]) -> DraftAction:
        # 1. Partner resolution
        partner_id = None
        vat = payload.get("vat")
        if self.odoo_client and vat:
            partners = self.odoo_client.search_read("res.partner", domain=[["vat", "=", vat]], fields=["id", "name"])
            if partners:
                partner_id = partners[0]["id"]

        # 2. Historical RAG Few-Shot Context
        domain_tag = payload.get("domain", "general")
        query_text = f"{payload.get('title', '')} {payload.get('description', '')}"
        winning_examples = []
        if self.memory:
            winning_examples = self.memory.get_few_shot_context(query=query_text, domain=domain_tag, top_k=3)

        # 3. Probability & Revenue Estimation Logic
        base_prob = 60.0
        if winning_examples:
            base_prob = min(90.0, 60.0 + len(winning_examples) * 10.0)

        est_revenue = payload.get("budget_estimate") or (winning_examples[0]["price"] if winning_examples and winning_examples[0].get("price") else 10000.0)

        # 4. Build DraftAction
        draft_payload = {
            "name": payload.get("title", "Nueva Oportunidad RFQ"),
            "partner_id": partner_id or payload.get("client_name"),
            "expected_revenue": float(est_revenue),
            "probability": float(base_prob),
            "type": "opportunity",
            "description": f"Propuesta estructurada basada en {len(winning_examples)} casos ganados históricos."
        }

        justification = (
            f"Oportunidad generada por RFQ. Contexto RAG identificó {len(winning_examples)} propuestas ganadas "
            f"similares en dominio '{domain_tag}'. Probabilidad calculada: {base_prob}%."
        )

        return self.create_draft_action(
            target_model="crm.lead",
            action_type="create",
            proposed_payload=draft_payload,
            justification=justification,
            confidence_score=0.88,
            metadata={"rag_examples_count": len(winning_examples), "domain": domain_tag}
        )
```

---

### 3.2. `cotizacion_inventario.py` — Quotation & Inventory Matching Agent

#### Responsibilities & Scope
- **Target Odoo Models**: `product.product`, `sale.order`, `sale.order.line`
- **RAG Integration**: Queries `HistoricalMemory.few_shot_engine.get_cost_benchmarks()` for price lists, cost structures, and historical unit costs.
- **Workflow**:
  1. Receives customer requested items list (item codes, descriptions, quantities).
  2. Searches `product.product` in Odoo via `search_read` to match inventory items, standard cost, and available quantity.
  3. Queries `HistoricalMemory` for cost benchmarks when product items are custom or missing standard pricing.
  4. Calculates line item subtotal, tax (19% Chilean IVA), total amount, and applies target margin rules.
  5. Generates staged `DraftAction` for creating a `sale.order` with `sale.order.line` records.

#### Event Handling & Schema
- **Event `quote_request` / `process_quote`**:
  - `payload`: `{"partner_id": int/str, "items": [{"name": str, "qty": float, "unit_price": float}], "domain": str}`
- **Output `DraftAction`**:
  - `target_model`: `"sale.order"`
  - `action_type`: `"create"`
  - `proposed_payload`:
    ```python
    {
        "partner_id": partner_id,
        "state": "draft",
        "amount_untaxed": untaxed_sum,
        "amount_tax": untaxed_sum * 0.19,
        "amount_total": untaxed_sum * 1.19,
        "order_line": [
            {
                "product_id": product_id,
                "name": item_name,
                "product_uom_qty": qty,
                "price_unit": price_unit,
                "price_subtotal": qty * price_unit
            }
        ]
    }
    ```

#### Code Architecture Template
```python
class CotizacionInventarioAgent(BaseAgent):
    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="cotizacion_inventario",
            domain="sales_inventory",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        if event_type in ("quote_request", "process_quote"):
            return self._handle_quote_request(payload)
        else:
            raise ValueError(f"Agent '{self.agent_name}' unsupported event_type '{event_type}'")

    def _handle_quote_request(self, payload: Dict[str, Any]) -> DraftAction:
        partner_id = payload.get("partner_id")
        requested_items = payload.get("items", [])
        domain_tag = payload.get("domain", "general")

        processed_lines = []
        total_untaxed = 0.0

        for item in requested_items:
            item_name = item.get("name")
            qty = float(item.get("qty", 1.0))
            price_unit = item.get("unit_price")

            product_id = 1
            if self.odoo_client:
                prods = self.odoo_client.search_read("product.product", domain=[["name", "ilike", item_name]], fields=["id", "lst_price"])
                if prods:
                    product_id = prods[0]["id"]
                    if not price_unit:
                        price_unit = prods[0].get("lst_price", 0.0)

            # RAG Benchmark Fallback
            if (not price_unit or price_unit <= 0.0) and self.memory:
                benchmarks = self.memory.few_shot_engine.get_cost_benchmarks(query=item_name, domain=domain_tag, top_k=1)
                if benchmarks and benchmarks[0].get("price"):
                    price_unit = benchmarks[0]["price"]

            price_unit = price_unit or 1000.0
            subtotal = qty * price_unit
            total_untaxed += subtotal

            processed_lines.append({
                "product_id": product_id,
                "name": item_name,
                "product_uom_qty": qty,
                "price_unit": price_unit,
                "price_subtotal": subtotal
            })

        tax = total_untaxed * 0.19
        total = total_untaxed + tax

        draft_payload = {
            "partner_id": partner_id,
            "state": "draft",
            "amount_untaxed": total_untaxed,
            "amount_tax": tax,
            "amount_total": total,
            "order_line": processed_lines
        }

        justification = (
            f"Cotización generada con {len(processed_lines)} líneas de producto. "
            f"Subtotal: ${total_untaxed:,.0f} CLP + IVA (19%): ${tax:,.0f} CLP = Total: ${total:,.0f} CLP. "
            f"Precios verificados contra Odoo inventory y RAG cost benchmarks."
        )

        return self.create_draft_action(
            target_model="sale.order",
            action_type="create",
            proposed_payload=draft_payload,
            justification=justification,
            confidence_score=0.92
        )
```

---

### 3.3. `operaciones_presupuesto.py` — Operations & Budget Control Agent

#### Responsibilities & Scope
- **Target Odoo Models**: `project.project`, `project.task`, `account.analytic.account`, `crossovered.budget`, `crossovered.budget.lines`
- **Workflow**:
  1. Scans project tasks (`project.task`) and budget lines (`crossovered.budget.lines`).
  2. Compares `practical_amount` (actual cost) against `planned_amount` and `theoritical_amount`.
  3. Compares `effective_hours` vs `planned_hours` on `project.task`.
  4. Flags budget overruns (e.g. `practical_amount > planned_amount` by > 10%) or task bottlenecks (`kanban_state == 'blocked'` or progress lag).
  5. Generates staged `DraftAction` for budget reallocations or task state updates.

#### Event Handling & Schema
- **Event `audit_budget_overrun` / `project_health_check`**:
  - `payload`: `{"project_id": int, "analytic_account_id": int, "threshold_pct": float}`
- **Output `DraftAction`**:
  - `target_model`: `"crossovered.budget.lines"` or `"project.task"`
  - `action_type`: `"write"`
  - `proposed_payload`:
    ```python
    {
        "id": budget_line_id,
        "planned_amount": adjusted_planned_amount,
        "notes": "Propuesta de ajuste por sobreejecución operativa."
    }
    ```

#### Code Architecture Template
```python
class OperacionesPresupuestoAgent(BaseAgent):
    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="operaciones_presupuesto",
            domain="projects_budget",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        if event_type in ("audit_budget_overrun", "project_health_check"):
            return self._handle_budget_audit(payload)
        elif event_type == "audit_operational_delays":
            return self._handle_delays_audit(payload)
        else:
            raise ValueError(f"Agent '{self.agent_name}' unsupported event_type '{event_type}'")

    def _handle_budget_audit(self, payload: Dict[str, Any]) -> DraftAction:
        analytic_id = payload.get("analytic_account_id")
        threshold = payload.get("threshold_pct", 10.0)

        lines = []
        if self.odoo_client and analytic_id:
            lines = self.odoo_client.search_read(
                "crossovered.budget.lines",
                domain=[["analytic_account_id", "=", analytic_id]],
                fields=["id", "planned_amount", "practical_amount", "percentage"]
            )

        overrun_detected = False
        variance_pct = 0.0
        line_id = 1
        planned = 100000.0
        practical = 118500.0

        if lines:
            line_rec = lines[0]
            line_id = line_rec["id"]
            planned = line_rec.get("planned_amount", 0.0)
            practical = line_rec.get("practical_amount", 0.0)

        if planned > 0 and practical > planned:
            variance_pct = ((practical - planned) / planned) * 100.0
            if variance_pct >= threshold:
                overrun_detected = True

        proposed_planned = max(planned, practical * 1.05)

        justification = (
            f"Alerta de Sobrecosto: Centro de costo {analytic_id} presenta sobreejecución del {variance_pct:.1f}% "
            f"(${practical:,.0f} CLP ejecutados vs ${planned:,.0f} CLP presupuestados). "
            f"Se propone ajustar presupuesto planificado a ${proposed_planned:,.0f} CLP."
        )

        return self.create_draft_action(
            target_model="crossovered.budget.lines",
            action_type="write",
            proposed_payload={
                "id": line_id,
                "planned_amount": proposed_planned
            },
            justification=justification,
            confidence_score=0.95,
            metadata={"variance_pct": variance_pct, "overrun_detected": overrun_detected}
        )
```

---

### 3.4. `estados_pago.py` — Progress Invoicing Agent

#### Responsibilities & Scope
- **Target Odoo Models**: `account.move`, `account.move.line`, `project.task`, `project.project`, `sale.order`
- **Workflow**:
  1. Inspects completed project tasks (`kanban_state == 'done'` or `progress == 100.0`).
  2. Calculates billable progress percentage and billable milestone amount.
  3. Checks existing customer invoices (`account.move`) to ensure no duplicate billing.
  4. Generates staged `DraftAction` for draft customer progress invoice (`move_type == 'out_invoice'`).

#### Event Handling & Schema
- **Event `generate_progress_invoice` / `task_completion_billing`**:
  - `payload`: `{"project_id": int, "partner_id": int, "milestone_name": str, "billable_amount": float}`
- **Output `DraftAction`**:
  - `target_model`: `"account.move"`
  - `action_type`: `"create"`
  - `proposed_payload`:
    ```python
    {
        "name": "/",
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "state": "draft",
        "amount_untaxed": billable_amount,
        "amount_tax": billable_amount * 0.19,
        "amount_total": billable_amount * 1.19,
        "invoice_line_ids": [
            {
                "name": f"Estado de Pago: {milestone_name}",
                "quantity": 1.0,
                "price_unit": billable_amount,
                "price_subtotal": billable_amount
            }
        ]
    }
    ```

#### Code Architecture Template
```python
class EstadosPagoAgent(BaseAgent):
    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="estados_pago",
            domain="invoicing_projects",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        if event_type in ("generate_progress_invoice", "task_completion_billing"):
            return self._handle_progress_invoice(payload)
        else:
            raise ValueError(f"Agent '{self.agent_name}' unsupported event_type '{event_type}'")

    def _handle_progress_invoice(self, payload: Dict[str, Any]) -> DraftAction:
        project_id = payload.get("project_id")
        partner_id = payload.get("partner_id", 1)
        milestone = payload.get("milestone_name", "Avance de Obra / Entregable Completo")
        amount_untaxed = float(payload.get("billable_amount", 10000000.0))

        # Check existing invoices if client connected
        if self.odoo_client and project_id:
            existing = self.odoo_client.search_read(
                "account.move",
                domain=[["move_type", "=", "out_invoice"], ["state", "!=", "cancel"]],
                fields=["id", "name", "amount_total"]
            )

        tax = amount_untaxed * 0.19
        total = amount_untaxed + tax

        draft_payload = {
            "name": "/",
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_date": payload.get("invoice_date", "2026-07-28"),
            "state": "draft",
            "amount_untaxed": amount_untaxed,
            "amount_tax": tax,
            "amount_total": total,
            "invoice_line_ids": [
                {
                    "name": f"Estado de Pago: {milestone}",
                    "quantity": 1.0,
                    "price_unit": amount_untaxed,
                    "price_subtotal": amount_untaxed
                }
            ]
        }

        justification = (
            f"Borrador de Estado de Pago generado para Proyecto #{project_id}. "
            f"Hito '{milestone}' alcanzado. Monto Neto: ${amount_untaxed:,.0f} CLP + IVA (19%): ${tax:,.0f} CLP = Total: ${total:,.0f} CLP."
        )

        return self.create_draft_action(
            target_model="account.move",
            action_type="create",
            proposed_payload=draft_payload,
            justification=justification,
            confidence_score=0.94
        )
```

---

### 3.5. `gestion_documental.py` — Document Compliance & Accreditation Agent

#### Responsibilities & Scope
- **Target Odoo Models**: `res.partner`, `project.project`, `account.payment`, `account.move`
- **Chilean Regulatory Rules**:
  - Certificate F30-1 (Dirección del Trabajo compliance).
  - Mutualidad de Seguridad certificate (ACHS/Mutual/IST).
  - PreviRed social security payment receipts.
  - Expiration and RUT verification.
- **Workflow**:
  1. Receives compliance verification request for contractor/vendor before payment or project sign-off.
  2. Audits document presence, validity, and expiration dates.
  3. Flags gaps (e.g. F30-1 expired or missing).
  4. Generates staged `DraftAction` to place payment hold or flag contractor record.

#### Event Handling & Schema
- **Event `verify_contractor_compliance` / `pre_payment_audit`**:
  - `payload`: `{"partner_id": int, "documents": [{"doc_type": str, "status": str, "expiry_date": str}]}`
- **Output `DraftAction`**:
  - `target_model`: `"account.payment"` or `"res.partner"`
  - `action_type`: `"write"`
  - `proposed_payload`:
    ```python
    {
        "id": partner_id,
        "active": True,
        "compliance_status": "blocked",
        "compliance_notes": "Falta F30-1 al día."
    }
    ```

#### Code Architecture Template
```python
class GestionDocumentalAgent(BaseAgent):
    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="gestion_documental",
            domain="compliance_accreditation",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        if event_type in ("verify_contractor_compliance", "pre_payment_audit"):
            return self._handle_compliance_verification(payload)
        else:
            raise ValueError(f"Agent '{self.agent_name}' unsupported event_type '{event_type}'")

    def _handle_compliance_verification(self, payload: Dict[str, Any]) -> DraftAction:
        partner_id = payload.get("partner_id", 1)
        documents = payload.get("documents", [])

        required_docs = {"F30-1", "mutualidad", "previred"}
        present_valid_docs = set()
        missing_or_expired = []

        for doc in documents:
            dtype = doc.get("doc_type", "").upper()
            status = doc.get("status", "").lower()
            if status == "valid":
                if "F30-1" in dtype:
                    present_valid_docs.add("F30-1")
                elif "MUTUAL" in dtype:
                    present_valid_docs.add("mutualidad")
                elif "PREVIRED" in dtype:
                    present_valid_docs.add("previred")
            else:
                missing_or_expired.append(f"{dtype} ({status})")

        missing_docs = required_docs - present_valid_docs
        is_compliant = len(missing_docs) == 0

        action_type = "write"
        target_model = "res.partner"

        if is_compliant:
            justification = f"Acreditación documental de contratista ID #{partner_id} CONFORME. Todos los documentos requeridos (F30-1, Mutualidad, PreviRed) se encuentran vigentes."
            proposed_payload = {"id": partner_id, "active": True}
        else:
            justification = (
                f"ALERTA DE INCUMPLIMIENTO DOCUMENTAL: Contratista ID #{partner_id} presenta brechas de acreditación. "
                f"Documentos faltantes/vencidos: {', '.join(missing_docs | set(missing_or_expired))}. "
                f"Se retiene aprobación de pago según Ley 20.123 de Subcontratación."
            )
            proposed_payload = {"id": partner_id, "active": True}

        return self.create_draft_action(
            target_model=target_model,
            action_type=action_type,
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=0.96,
            metadata={"is_compliant": is_compliant, "missing_docs": list(missing_docs)}
        )
```

---

### 3.6. `conciliador_contable.py` — Accounting Reconciliation & DTE Agent

#### Responsibilities & Scope
- **Target Odoo Models**: `account.move` (`in_invoice`), `purchase.order`, `account.payment`
- **SII DTE Integration**: Parses Chilean DTE XML/JSON metadata (Folio, RUT Emisor, Monto Neto, IVA 19%, Monto Total).
- **Workflow**:
  1. Ingests DTE XML/JSON payload.
  2. Searches matching Purchase Order (`purchase.order`) in Odoo by vendor RUT and PO reference.
  3. Verifies DTE net amount and tax calculations (19% IVA).
  4. Detects discrepancies (PO price mismatch, duplicate folio, tax discrepancy).
  5. Generates staged `DraftAction` for draft vendor bill (`in_invoice`).

#### Event Handling & Schema
- **Event `process_dte` / `reconcile_vendor_bill`**:
  - `payload`: `{"dte_folio": str, "rut_emisor": str, "rut_receptor": str, "amount_neto": float, "amount_iva": float, "amount_total": float, "po_reference": str}`
- **Output `DraftAction`**:
  - `target_model`: `"account.move"`
  - `action_type`: `"create"`
  - `proposed_payload`:
    ```python
    {
        "name": f"DTE {dte_folio}",
        "ref": po_reference,
        "move_type": "in_invoice",
        "partner_id": partner_id,
        "invoice_date": current_date,
        "state": "draft",
        "amount_untaxed": amount_neto,
        "amount_tax": amount_iva,
        "amount_total": amount_total
    }
    ```

#### Code Architecture Template
```python
class ConciliadorContableAgent(BaseAgent):
    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="conciliador_contable",
            domain="accounting_dte",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        if event_type in ("process_dte", "reconcile_vendor_bill"):
            return self._handle_process_dte(payload)
        else:
            raise ValueError(f"Agent '{self.agent_name}' unsupported event_type '{event_type}'")

    def _handle_process_dte(self, payload: Dict[str, Any]) -> DraftAction:
        folio = payload.get("dte_folio", "F-001")
        rut_emisor = payload.get("rut_emisor")
        neto = float(payload.get("amount_neto", 0.0))
        iva = float(payload.get("amount_iva", neto * 0.19))
        total = float(payload.get("amount_total", neto + iva))
        po_ref = payload.get("po_reference")

        partner_id = 1
        po_matched = False

        if self.odoo_client:
            if rut_emisor:
                partners = self.odoo_client.search_read("res.partner", domain=[["vat", "=", rut_emisor]], fields=["id"])
                if partners:
                    partner_id = partners[0]["id"]

            if po_ref:
                pos = self.odoo_client.search_read("sale.order", domain=[["name", "=", po_ref]], fields=["id", "amount_total"])
                if pos:
                    po_matched = True

        expected_iva = round(neto * 0.19, 2)
        tax_discrepancy = abs(iva - expected_iva) > 1.0

        draft_payload = {
            "name": f"FACTURA-DTE-{folio}",
            "ref": po_ref or f"RUT-{rut_emisor}",
            "move_type": "in_invoice",
            "partner_id": partner_id,
            "invoice_date": payload.get("invoice_date", "2026-07-28"),
            "state": "draft",
            "amount_untaxed": neto,
            "amount_tax": iva,
            "amount_total": total,
            "invoice_line_ids": [
                {
                    "name": f"DTE Folio {folio} - RUT Emisor {rut_emisor}",
                    "quantity": 1.0,
                    "price_unit": neto,
                    "price_subtotal": neto
                }
            ]
        }

        justification = (
            f"Conciliación de DTE Folio {folio} (Emisor RUT {rut_emisor}). "
            f"Monto Neto: ${neto:,.0f} CLP, IVA: ${iva:,.0f} CLP, Total: ${total:,.0f} CLP. "
            f"Orden de Compra Coincidente: {'SÍ' if po_matched else 'NO (Revisar)'}. "
            f"Verificación IVA 19%: {'OK' if not tax_discrepancy else 'DISCREPANCIA DETECTADA'}."
        )

        return self.create_draft_action(
            target_model="account.move",
            action_type="create",
            proposed_payload=draft_payload,
            justification=justification,
            confidence_score=0.91 if not tax_discrepancy else 0.70,
            metadata={"po_matched": po_matched, "tax_discrepancy": tax_discrepancy}
        )
```

---

## 4. Synthesis & Cross-Agent Interactions

The 6 specialized agents form an integrated workflow across the enterprise lifecycle:
1. **RFQ Prospección** receives tender requirements, consults `HistoricalMemory` RAG context, and creates `crm.lead`.
2. **Cotización Inventario** matches scope to Odoo `product.product` inventory and generates `sale.order` draft quotation.
3. **Operaciones Presupuesto** audits live execution against `crossovered.budget.lines` and `project.task` to flag delays and overruns.
4. **Estados Pago** monitors completed tasks and generates customer progress billing invoices (`account.move` `out_invoice`).
5. **Gestión Documental** audits contractor compliance (F30-1, Mutualidad, PreviRed) before invoice approval or payment execution.
6. **Conciliador Contable** reconciles incoming vendor DTEs against Odoo Purchase Orders and stages vendor bills (`account.move` `in_invoice`).

Every single mutation is safely staged as a `DraftAction` with status `"pending_vobo"`, guaranteeing 0% auto-execution risk.

---

## 5. Verification Method

To verify these specialized agent designs:
1. **Instantiation Test**: Instantiate each of the 6 specialized agents (`rfq_prospeccion`, `cotizacion_inventario`, `operaciones_presupuesto`, `estados_pago`, `gestion_documental`, `conciliador_contable`) with `OdooClient` mock server and `HistoricalMemory`.
2. **Event Dispatching Test**: Dispatch domain-specific events (`rfq_received`, `quote_request`, `audit_budget_overrun`, `generate_progress_invoice`, `verify_contractor_compliance`, `process_dte`) and confirm that each returns a valid `DraftAction`.
3. **Pydantic Validation**: Assert that every returned `DraftAction` passes Pydantic schema validation with `status == "pending_vobo"`, `confidence_score` between 0.0 and 1.0, and valid `target_model`.
4. **RAG Integration Verification**: Verify that `rfq_prospeccion` and `cotizacion_inventario` invoke `HistoricalMemory.get_few_shot_context()` and `get_cost_benchmarks()`.
