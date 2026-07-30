"""
Interactive Quoting Console for Conecta Ingeniería S.A. Sales Estimators (Cotizadores).
Allows commercial teams to test, input RFQs, generate itemized BOMs with official brands (Vizimax, Belden Hirschmann, NovaTech Orion),
apply optional GPS rules, optimize margins, and stage proposals into Odoo ERP.
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag_memory.business_lines import BusinessLineClassifier, GuidedArchitectureEngine, BusinessLineType
from src.rag_memory.advanced_intelligence import RegulatoryComplianceAuditor, WinRateEstimator
from swarm_engine.base_agent import DraftAction
from swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent
from src.supervisor_ui.console import SupervisorConsole


def run_interactive_cotizador():
    print("\n" + "=" * 80)
    print("⚡ SISTEMA AGÉNTICO DE COTIZACIÓN GUIADA - CONECTA INGENIERÍA S.A.")
    print("   Herramienta Interactiva para Cotizadores y Líderes Comerciales")
    print("=" * 80)

    console = SupervisorConsole()

    print("\n📋 INGRESO DE NUEVA SOLICITUD DE COTIZACIÓN (RFQ):")
    client_name = input("  • Nombre del Cliente (ej. Transelec, Chilquinta, Colbún, Enel, ADASA): ").strip()
    if not client_name:
        client_name = "Transelec S.A."

    project_title = input("  • Título / Nombre del Proyecto (ej. Medición Fasorial SE Ancud 220kV): ").strip()
    if not project_title:
        project_title = "Proyecto Digitalización & Telemetría Subestación"

    rfq_text = input("  • Descripción Corta del Requerimiento: ").strip()
    if not rfq_text:
        rfq_text = "Cotizar suministro de remotas RTU, tarjetas I/O y switches Belden Hirschmann para subestación"

    print("\n🔍 PROCESANDO CON EL ENJAMBRE AGÉNTICO...")
    time.sleep(0.5)

    # 1. Classification
    bl = BusinessLineClassifier.classify(rfq_text)
    print(f"\n✅ 1. Clasificación Automática de Línea de Negocio: '{bl.value.upper()}'")

    # 2. Guided Architecture
    arch = GuidedArchitectureEngine.get_architecture_guidance(bl.value)
    print(f"📐 2. Arquitectura Recomendada: '{arch['architecture']['title']}'")
    print(f"     • Protocolo Estándar: {arch['architecture']['protocol']}")
    print(f"     • Componentes Base: {', '.join(arch['architecture']['required_components'])}")

    # 3. Interactive Question for Optional GPS Clock
    has_gps = False
    if bl == BusinessLineType.PMU_PDC or "pmu" in rfq_text.lower():
        gps_input = input("\n❓ ¿El cliente YA posee Reloj GPS satelital IRIG-B en la subestación? (s/n, por defecto 'n'): ").strip().lower()
        has_gps = (gps_input == "s" or gps_input == "si" or gps_input == "y")

    # 4. Itemized BOM Construction according to official Conecta rules
    bom_items = []
    if bl == BusinessLineType.PMU_PDC or "pmu" in rfq_text.lower():
        bom_items.append({"item_code": "HW-VIZIMAX-PMU", "name": "Medidor Vizimax SynchroTeq Plus PMU IEEE C37.118-2011", "qty": 1, "unit_price_clp": 9500000.0})
        bom_items.append({"item_code": "HW-PDC-ORION", "name": "Concentrador PDC NovaTech Orion MX Gateway C37.118", "qty": 1, "unit_price_clp": 12500000.0})
        if not has_gps:
            bom_items.append({"item_code": "HW-GPS-CLOCK", "name": "Sincronizador Satelital GPS Kronos IRIG-B / PTP 1588", "qty": 1, "unit_price_clp": 6800000.0})
            print("  📌 Nota: Se incluye Reloj GPS Kronos IRIG-B en la cotización.")
        else:
            print("  📌 Nota: Se OMITE el Reloj GPS Kronos por existencia confirmada en el cliente.")
        bom_items.append({"item_code": "SW-BELDEN-SWITCH", "name": "Switch Ethernet Industrial Belden Hirschmann RS20/RS30", "qty": 1, "unit_price_clp": 3200000.0})
        bom_items.append({"item_code": "SRV-ING-CEN", "name": "Servicio de Ingeniería, Protocolos AT-SITR-1 e Informe IPES", "qty": 1, "unit_price_clp": 6000000.0})
    else:
        bom_items.append({"item_code": "HW-RTU-ORION-LX", "name": "Remota RTU NovaTech Orion LX+ DNP3/IEC61850", "qty": 1, "unit_price_clp": 8900000.0})
        bom_items.append({"item_code": "HW-NOVACARD-IO", "name": "Tarjetas I/O Novacard 32DI / 16DO / 8AI", "qty": 2, "unit_price_clp": 3400000.0})
        bom_items.append({"item_code": "SW-BELDEN-SWITCH", "name": "Switch Ethernet Industrial Belden Hirschmann RS20 Managed", "qty": 2, "unit_price_clp": 6400000.0})
        bom_items.append({"item_code": "HW-ROUTER-4G", "name": "Módem Router Industrial 4G Dual-SIM DNP3", "qty": 1, "unit_price_clp": 1800000.0})
        bom_items.append({"item_code": "SRV-KITTING-RTU", "name": "Pre-cableado Tablero Kit B RTU en Taller + Ensayos HIL", "qty": 1, "unit_price_clp": 4500000.0})

    cost_clp = sum(item["unit_price_clp"] * item["qty"] for item in bom_items)
    margin_pct = 54.8
    sale_price_clp = cost_clp / (1 - (margin_pct / 100.0))
    gross_profit_clp = sale_price_clp - cost_clp

    print("\n💰 3. Análisis Financiero & Rentabilidad Retenida:")
    print(f"  • Costo Directo Interno: CLP ${cost_clp:,.0f}")
    print(f"  • Margen Bruto Retenido: {margin_pct}% (Regla de Oro Conecta)")
    print(f"  • Utilidad Bruta Directa: CLP ${gross_profit_clp:,.0f}")
    print(f"  • PRECIO DE VENTA SUGERIDO A CLIENTE: CLP ${sale_price_clp:,.0f} (+ IVA)")

    # 5. Regulatory Audit
    audit = RegulatoryComplianceAuditor.audit_proposal(bom_items, bl.value)
    print(f"\n🛡️ 4. Auditoría Preventiva Normativa CEN/SEC:")
    print(f"  • Puntuación de Cumplimiento: {audit.compliance_score * 100:.0f}% ({audit.status})")
    if audit.warnings:
        for w in audit.warnings:
            print(f"    ⚠️ [{w.severity}] {w.standard}: {w.message}")

    # 6. Odoo Staging Draft Action
    so_draft = DraftAction(
        agent_name="CotizacionInventarioAgent",
        target_model="sale.order",
        action_type="create",
        proposed_payload={
            "partner_name": client_name,
            "opportunity_name": project_title,
            "amount_total_clp": sale_price_clp,
            "proposed_margin_pct": margin_pct,
            "order_line": bom_items
        },
        justification=f"Cotización agéntica para {client_name} - {project_title} con marcas oficiales Conecta.",
        confidence_score=0.99
    )
    so_action = console.register_draft(so_draft)

    print("\n🚀 5. ENVIADO A ODOO ERP STAGING (`sale.order`):")
    print(f"  ✅ Sale Order Draft ID: '{so_action.draft_id}'")
    print(f"  ✅ Disponible para Visto Bueno (VoBo) en la Consola Web: http://127.0.0.1:5001/")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    run_interactive_cotizador()
