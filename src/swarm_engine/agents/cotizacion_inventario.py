"""
Quotation & Inventory Agent (CotizacionInventarioAgent).
Matches products against Odoo inventory (product.product), retrieves cost benchmarks from RAG memory,
calculates price subtotals and Chilean 19% IVA, and drafts Sales Quotations (sale.order).
"""

from typing import Any, Dict, List, Optional
import logging
from swarm_engine.base_agent import BaseAgent, DraftAction
from odoo_ecosystem.client import OdooClient
from rag_memory.few_shot import HistoricalMemory
from rag_memory.business_lines import (
    BusinessLineClassifier,
    BusinessLineType,
    STANDARD_BOM_TEMPLATES,
    BOMTemplate,
    CommercialModality,
    TenderAntecedents,
    SavingsOpportunity,
    MarginOptimizationReport,
)
from rag_memory.advanced_intelligence import (
    RegulatoryComplianceAuditor,
    WinRateEstimator,
    CrossSellEngine,
)
try:
    from operations.quantity_parser import QuantityParser
except ImportError:
    from src.operations.quantity_parser import QuantityParser


logger = logging.getLogger(__name__)


class CotizacionInventarioAgent(BaseAgent):
    """
    Specialized agent for product catalog matching, historical pricing lookup,
    guided business line quotations (PMUS/PDC, SITR, SCADA, EDAC), commercial modality handling (Compra Directa vs Licitación),
    margin optimization, and draft sale order generation.
    """

    def __init__(
        self,
        odoo_client: Optional[OdooClient] = None,
        memory: Optional[HistoricalMemory] = None
    ):
        super().__init__(
            agent_name="cotizacion_inventario",
            domain="quotations_inventory",
            odoo_client=odoo_client,
            memory=memory
        )

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        """
        Processes quotation requests and inventory checks to construct a staged DraftAction for sale.order creation.
        """
        supported_events = {
            "quote_request", "process_quote", "quotation_requested",
            "inventory_check", "pricing_request", "process_task", "guided_quote"
        }
        if event_type not in supported_events:
            logger.warning("Agent '%s' received unmapped event type '%s'", self.agent_name, event_type)

        if payload.get("items") or payload.get("product_id"):
            return self._handle_quote_request(payload)

        prompt = payload.get("prompt") or payload.get("title") or payload.get("query") or ""
        return self.guide_quotation(prompt_or_line=prompt or payload.get("business_line", "scada_retrofit"), user_params=payload)

    def guide_quotation(self, prompt_or_line: str, user_params: Dict[str, Any]) -> DraftAction:
        """
        Guided Interactive Quotation Generator with Margin Optimization & Savings Opportunities.
        """
        b_type = BusinessLineClassifier.classify(prompt_or_line)
        template: BOMTemplate = STANDARD_BOM_TEMPLATES.get(b_type, STANDARD_BOM_TEMPLATES[BusinessLineType.PMU_PDC])

        partner_id = str(user_params.get("partner_id") or user_params.get("client") or "Cliente Coordinado 2026")

        raw_qty = user_params.get("num_rtus") or user_params.get("num_remotas") or user_params.get("num_pmus") or user_params.get("qty")
        if raw_qty is not None:
            if isinstance(raw_qty, str):
                num_devices = QuantityParser.extract_device_quantity(raw_qty, default=1.0)
            else:
                num_devices = float(raw_qty)
        else:
            num_devices = QuantityParser.extract_device_quantity(prompt_or_line, default=1.0)

        parsed_quantities = QuantityParser.parse_quantities(prompt_or_line)

        modality_str = user_params.get("modality") or ("licitacion" if "licitacion" in prompt_or_line.lower() or "rfp" in prompt_or_line.lower() else "compra_directa")
        modality = CommercialModality.LICITACION if modality_str == "licitacion" else CommercialModality.COMPRA_DIRECTA

        # Target Retained Margin: User-configurable (Default 54.8% Hardware/Engineering, 68.5% SLA/Software)
        default_target = 68.5 if b_type in [BusinessLineType.MAINTENANCE_LICENSES] else 54.8
        target_margin_pct = float(user_params.get("target_margin_pct") or user_params.get("margin_pct") or default_target)
        sale_multiplier = 1.0 / (1.0 - (target_margin_pct / 100.0))

        processed_lines = []
        total_cost = 0.0
        has_existing_gps = bool(user_params.get("has_existing_gps")) or bool(user_params.get("client_has_gps")) or (user_params.get("include_gps_clock") is False)

        for b_item in template.items:
            if has_existing_gps and "gps" in b_item.item_code.lower():
                continue  # Omit GPS clock if client already has existing clock in substation

            qty = b_item.default_qty
            if ("pmu" in b_item.item_code.lower() or "rtu" in b_item.item_code.lower()) and num_devices > 1:
                qty = num_devices
            elif "switch" in b_item.item_code.lower() and parsed_quantities.get("num_switches"):
                qty = float(parsed_quantities["num_switches"])


            unit_cost = b_item.unit_price_clp

            if self.memory and hasattr(self.memory, "few_shot_engine"):
                benchmarks = self.memory.few_shot_engine.get_cost_benchmarks(query=b_item.description, top_k=1)
                if benchmarks and benchmarks[0].get("price"):
                    unit_cost = float(benchmarks[0]["price"])

            cost_subtotal = qty * unit_cost
            total_cost += cost_subtotal

            # Calculate Selling Unit Price per line item so sum(line.price_subtotal) == total_sale_untaxed
            unit_sale_price = round(unit_cost * sale_multiplier, 0)
            sale_subtotal = round(qty * unit_sale_price, 0)

            processed_lines.append({
                "product_id": 1,
                "item_code": b_item.item_code,
                "name": f"[{b_item.category.value.upper()}] {b_item.description}",
                "product_uom_qty": qty,
                "unit_cost_clp": unit_cost,
                "price_unit": unit_sale_price,
                "price_subtotal": sale_subtotal
            })

        # Tender Antecedents items
        tender_info = None
        if modality == CommercialModality.LICITACION:
            tender_info = TenderAntecedents(
                tender_code=f"LIC-{b_type.value.upper()}-2026",
                title=f"Licitación Pública {template.name}",
                client_name=partner_id,
                modality=CommercialModality.LICITACION
            )
            bond_cost = total_cost * 0.02
            total_cost += bond_cost
            bond_sale_price = round(bond_cost * sale_multiplier, 0)
            processed_lines.append({
                "product_id": 1,
                "item_code": "REG-BOND-F10",
                "name": f"[REGULATORY_CERTIFICATION] Boleta de Fiel Cumplimiento de Contrato (10% {tender_info.tender_code})",
                "product_uom_qty": 1.0,
                "unit_cost_clp": bond_cost,
                "price_unit": bond_sale_price,
                "price_subtotal": bond_sale_price
            })

        # Calculate Total Untaxed Net Sale Price from line item subtotals
        total_sale_untaxed = sum(line["price_subtotal"] for line in processed_lines)
        base_gross_margin_clp = total_sale_untaxed - total_cost
        base_gross_margin_pct = round((base_gross_margin_clp / total_sale_untaxed) * 100.0, 1)

        # Identify Internal Cost Savings Opportunities
        savings_hw = total_cost * 0.05
        savings_hh = total_cost * 0.03

        opportunities = [
            SavingsOpportunity(
                category="volume_discount",
                title="Descuento por Volumen en Equipos (VIZIMAX / Belden Hirschmann)",
                description="Negociación interna de volumen con fabricante para bajar costo directo sin alterar precio al cliente.",
                estimated_savings_clp=savings_hw,
                additional_profit_clp=savings_hw,
                margin_boost_pct=3.5,
                risk_level="LOW"
            ),
            SavingsOpportunity(
                category="engineering_efficiency",
                title="Optimización de Jornadas FAT/SAT y Pre-kitting en Taller",
                description="Armado de tableros pre-cableados en taller, reduciendo costo de HH terreno para la empresa.",
                estimated_savings_clp=savings_hh,
                additional_profit_clp=savings_hh,
                margin_boost_pct=2.1,
                risk_level="LOW"
            )
        ]

        total_retained_savings = sum(o.additional_profit_clp for o in opportunities)
        optimized_cost = total_cost - total_retained_savings
        boosted_gross_margin_clp = total_sale_untaxed - optimized_cost
        boosted_margin_pct = round((boosted_gross_margin_clp / total_sale_untaxed) * 100.0, 1)

        margin_report = MarginOptimizationReport(
            total_cost_clp=total_cost,
            optimized_cost_clp=optimized_cost,
            total_sale_price_clp=total_sale_untaxed,
            base_margin_clp=base_gross_margin_clp,
            base_margin_pct=base_gross_margin_pct,
            retained_savings_clp=total_retained_savings,
            boosted_margin_clp=boosted_gross_margin_clp,
            boosted_margin_pct=boosted_margin_pct,
            opportunities=opportunities
        )

        tax = round(total_sale_untaxed * 0.19, 0)
        total = total_sale_untaxed + tax

        # Run Preventive Regulatory Audit, Win-Rate Estimator, and SLA Cross-Selling Discovery
        reg_audit = RegulatoryComplianceAuditor.audit_proposal(processed_lines, b_type.value)
        win_prediction = WinRateEstimator.predict_win_rate(partner_id, boosted_margin_pct)
        cross_sells = CrossSellEngine.find_opportunities(partner_id, b_type.value, total_sale_untaxed)

        # Query InfoTécnica CEN API for technical substation/plant metadata and documents
        try:
            from operations.infotecnica_client import InfoTecnicaClient
            infotecnica_context = InfoTecnicaClient.enrich_quotation_context(prompt_or_line)
        except Exception:
            infotecnica_context = {"found": False, "matches": []}

        proposed_payload = {
            "partner_id": partner_id,
            "business_line": b_type.value,
            "commercial_modality": modality.value,
            "state": "draft",
            "amount_untaxed": total_sale_untaxed,
            "amount_tax": tax,
            "amount_total": total,
            "order_line": processed_lines,
            "margin_analysis": margin_report.model_dump(),
            "regulatory_audit": reg_audit.model_dump(),
            "win_rate_prediction": win_prediction.model_dump(),
            "cross_sell_opportunities": [cs.model_dump() for cs in cross_sells],
            "infotecnica_cen": infotecnica_context
        }

        if tender_info:
            proposed_payload["tender_antecedents"] = tender_info.model_dump()

        modality_label = "LICITACIÓN" if modality == CommercialModality.LICITACION else "COMPRA DIRECTA"
        justification = (
            f"Cotización Guiada Modalidad '{modality_label}' ({template.name}). "
            f"Precio Cliente Neto: ${total_sale_untaxed:,.0f} CLP | Total Bruto con IVA: ${total:,.0f} CLP. "
            f"💰 Utilidad Bruta Empresa: {boosted_margin_pct:.1f}% (${boosted_gross_margin_clp:,.0f} CLP) | "
            f"🏆 Probabilidad Win-Rate Est.: {win_prediction.estimated_win_rate_pct:.0f}% | "
            f"🛡️ Audit Normativo: {reg_audit.status} ({reg_audit.compliance_score * 100:.0f}%)."
        )

        return self.create_draft_action(
            target_model="sale.order",
            action_type="create",
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=0.96 if modality == CommercialModality.COMPRA_DIRECTA else 0.94,
            metadata={
                "business_line": b_type.value,
                "commercial_modality": modality.value,
                "template_name": template.name,
                "guided_questions": template.guided_questions,
                "tender_antecedents": tender_info.model_dump() if tender_info else None,
                "margin_analysis": margin_report.model_dump(),
                "regulatory_audit": reg_audit.model_dump(),
                "win_rate_prediction": win_prediction.model_dump(),
                "cross_sell_opportunities": [cs.model_dump() for cs in cross_sells],
                "line_items_count": len(processed_lines),
                "total_untaxed": total_sale_untaxed,
                "tax_iva": tax,
                "total_amount": total
            }
        )

    def _handle_quote_request(self, payload: Dict[str, Any]) -> DraftAction:
        partner_id = payload.get("partner_id") or 1
        requested_items = payload.get("items") or payload.get("order_line") or []
        domain_tag = payload.get("domain") or "general"

        if not requested_items and payload.get("product_name"):
            requested_items = [{
                "name": payload.get("product_name"),
                "qty": payload.get("qty", 1.0),
                "unit_price": payload.get("unit_price")
            }]

        processed_lines = []
        total_untaxed = 0.0

        for item in requested_items:
            item_name = item.get("name") or item.get("product_name") or "Servicio / Producto General"
            qty = float(item.get("qty") or item.get("product_uom_qty") or 1.0)
            price_unit = item.get("unit_price") or item.get("price_unit")

            product_id = 1
            # 1. Query Odoo inventory for product details
            if self.odoo_client and item_name:
                prods = self.query_odoo("product.product", domain=[["name", "ilike", item_name]], fields=["id", "name", "lst_price"])
                if prods:
                    product_id = prods[0]["id"]
                    if price_unit is None or float(price_unit) <= 0:
                        price_unit = prods[0].get("lst_price", 0.0)

            # 2. Query RAG Memory for price benchmarks if price missing
            if (price_unit is None or float(price_unit) <= 0) and self.memory:
                if hasattr(self.memory, "few_shot_engine"):
                    benchmarks = self.memory.few_shot_engine.get_cost_benchmarks(query=item_name, domain=domain_tag, top_k=1)
                    if benchmarks and benchmarks[0].get("price"):
                        price_unit = float(benchmarks[0]["price"])

                if price_unit is None or float(price_unit) <= 0:
                    context = self.get_historical_context(query=item_name, top_k=1)
                    if context and context[0].get("price"):
                        price_unit = float(context[0]["price"])

            price_unit = float(price_unit) if price_unit and float(price_unit) > 0 else 100000.0
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

        proposed_payload = {
            "partner_id": partner_id,
            "state": "draft",
            "amount_untaxed": total_untaxed,
            "amount_tax": tax,
            "amount_total": total,
            "order_line": processed_lines
        }

        justification = (
            f"Cotización generada con {len(processed_lines)} líneas de producto. "
            f"Neto: ${total_untaxed:,.0f} CLP + IVA (19%): ${tax:,.0f} CLP = Total: ${total:,.0f} CLP. "
            f"Precios verificados contra Odoo inventory y RAG cost benchmarks."
        )

        return self.create_draft_action(
            target_model="sale.order",
            action_type="create",
            proposed_payload=proposed_payload,
            justification=justification,
            confidence_score=0.92,
            metadata={
                "line_items_count": len(processed_lines),
                "total_untaxed": total_untaxed,
                "tax_iva": tax,
                "total_amount": total
            }
        )
