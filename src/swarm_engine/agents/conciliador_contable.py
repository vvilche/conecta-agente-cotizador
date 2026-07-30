"""
Accounting Reconciliation & DTE Agent (ConciliadorContableAgent).
Reconciles Chilean Electronic Tax Documents (DTE / SII) against Purchase Orders and vendor accounts,
verifying 19% IVA tax splits, checking for discrepancies, and drafting vendor bills (account.move in_invoice).
"""

from typing import Any, Dict, List, Optional
import logging
from swarm_engine.base_agent import BaseAgent, DraftAction
from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory

logger = logging.getLogger(__name__)


class ConciliadorContableAgent(BaseAgent):
    """
    Specialized agent for Chilean DTE tax document reconciliation and vendor bill draft creation.
    """

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
        """
        Processes DTE reconciliation and vendor bill events to generate staged DraftActions.
        """
        supported_events = {
            "process_dte", "reconcile_vendor_bill", "dte_reconciliation",
            "bank_matching", "invoice_received", "process_task"
        }
        if event_type not in supported_events:
            logger.warning("Agent '%s' received unmapped event type '%s'", self.agent_name, event_type)

        return self._handle_dte_reconciliation(payload)

    def _handle_dte_reconciliation(self, payload: Dict[str, Any]) -> DraftAction:
        folio = str(payload.get("dte_folio") or payload.get("folio") or "F-1001")
        rut_emisor = payload.get("rut_emisor") or payload.get("vat") or "76111222-3"
        neto = float(payload.get("amount_neto") or payload.get("amount_untaxed") or 1000000.0)
        iva = float(payload.get("amount_iva") or payload.get("amount_tax") or round(neto * 0.19, 2))
        total = float(payload.get("amount_total") or (neto + iva))
        po_ref = payload.get("po_reference") or payload.get("po_name") or payload.get("ref")

        partner_id = 1
        po_matched = False
        po_discrepancy = False

        if self.odoo_client:
            # 1. Match partner by RUT
            if rut_emisor:
                partners = self.query_odoo("res.partner", domain=[["vat", "=", rut_emisor]], fields=["id"])
                if partners:
                    partner_id = partners[0]["id"]

            # 2. Match Purchase Order in Odoo
            if po_ref:
                pos = self.query_odoo("sale.order", domain=[["name", "=", po_ref]], fields=["id", "amount_total"])
                if not pos:
                    pos = self.query_odoo("purchase.order", domain=[["name", "=", po_ref]], fields=["id", "amount_total"])

                if pos:
                    po_matched = True
                    po_total = float(pos[0].get("amount_total", 0.0))
                    if abs(po_total - total) > 1.0 and po_total > 0:
                        po_discrepancy = True

        expected_iva = round(neto * 0.19, 2)
        tax_discrepancy = abs(iva - expected_iva) > 1.0

        proposed_payload = {
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

        justification_parts = [
            f"Conciliación de DTE Folio {folio} (Emisor RUT {rut_emisor}).",
            f"Monto Neto: ${neto:,.0f} CLP, IVA: ${iva:,.0f} CLP, Total: ${total:,.0f} CLP.",
            f"Orden de Compra Coincidente: {'SÍ' if po_matched else 'NO (Sin OC direct)'}."
        ]

        if tax_discrepancy:
            justification_parts.append(f"ALERTA: Discrepancia en IVA calculada (${iva:,.0f} vs esperada ${expected_iva:,.0f}).")
        if po_discrepancy:
            justification_parts.append(f"ALERTA: Discrepancia entre total DTE (${total:,.0f}) y total OC.")

        justification = " ".join(justification_parts)

        confidence = 0.94
        if tax_discrepancy or po_discrepancy:
            confidence = 0.68

        return self.create_draft_action(
            target_model="account.move",
            action_type="create",
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=confidence,
            metadata={
                "dte_folio": folio,
                "rut_emisor": rut_emisor,
                "po_matched": po_matched,
                "po_discrepancy": po_discrepancy,
                "tax_discrepancy": tax_discrepancy
            }
        )
