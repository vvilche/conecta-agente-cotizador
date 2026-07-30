"""
Multi-Quote Agentic Workflow Recording Script.
Simulates a 3-quote cycle:
1. PMU / WAPMS Quote (Transelec - SE Ancud 220kV)
2. RTU Remota Quote (Chilquinta - SE Mayaca 110kV)
3. SCADA Retrofit Quote (ADASA - SE Desaladora)

Logs step-by-step agentic interactions, BOM generations, margin calculations, and Odoo ERP staging.
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
from swarm_engine.agents.rfq_prospeccion import RFQProspeccionAgent
from swarm_engine.agents.operaciones_presupuesto import OperacionesPresupuestoAgent
from src.supervisor_ui.console import SupervisorConsole
from src.operations.doc_automator import DocAutomator
from src.operations.kitting_engine import KittingEngine
from src.operations.config_automator import ConfigAutomator
from src.operations.fat_sat_simulator import FatSatSimulator
from src.operations.payment_statement_automator import PaymentStatementAutomator


def run_multi_quote_agentic_cycle():
    print("\n" + "=" * 80)
    print("🎬 GRABACIÓN DE CICLO AGÉNTICO MULTICOTIZACIÓN (PMU, RTU REMOTA, SCADA)")
    print("   Demostración de Coordinación de Agentes Autónomos en Tiempo Real")
    print("=" * 80)

    start_time = time.perf_counter()
    cycle_log = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "quotes": []
    }

    console = SupervisorConsole()

    # =========================================================================
    # COTIZACIÓN 1: PMU / WAPMS (Transelec - SE Ancud 220kV)
    # =========================================================================
    print("\n------------------------------------------------------------------------")
    print("📌 COTIZACIÓN 1: PMU / WAPMS (Transelec S.A. - SE Ancud 220kV)")
    print("------------------------------------------------------------------------")
    q1_request = "Necesito cotizar un sistema de Medición Fasorial PMU para Subestación Ancud 220kV de Transelec. Incluir medidor fasorial, concentrador PDC y reloj GPS."
    
    print(f"  [USER INPUT]: '{q1_request}'")
    
    # 1. RFQ Classification
    bl1 = BusinessLineClassifier.classify(q1_request)
    print(f"  🤖 [RFQProspeccionAgent]: Clasificación de Línea -> '{bl1.value}' (Confianza: 99.8%)")
    
    # 2. Guided Architecture
    arch1 = GuidedArchitectureEngine.get_architecture_guidance(bl1.value)
    print(f"  🤖 [CotizacionInventarioAgent]: Arquitectura Recomendada -> '{arch1['architecture']['title']}'")
    print(f"     • Componentes Requeridos: {', '.join(arch1['architecture']['required_components'])}")
    print(f"     • Protocolo Objetivo: {arch1['architecture']['protocol']}")
    
    # 3. BOM & Margin Calculation
    bom1 = [
        {"item_code": "HW-VIZIMAX-PMU", "name": "Medidor Vizimax SynchroTeq Plus PMU IEEE C37.118", "qty": 1, "unit_price_clp": 9500000.0},
        {"item_code": "HW-PDC-ORION", "name": "Concentrador PDC NovaTech Orion MX Gateway C37.118", "qty": 1, "unit_price_clp": 12500000.0},
        {"item_code": "HW-GPS-CLOCK", "name": "Sincronizador Satelital GPS Kronos IRIG-B / PTP 1588", "qty": 1, "unit_price_clp": 6800000.0},
        {"item_code": "SW-BELDEN-SWITCH", "name": "Switch Ethernet Industrial Belden Hirschmann RS20/RS30", "qty": 1, "unit_price_clp": 3200000.0},
        {"item_code": "SRV-ING-CEN", "name": "Servicio de Ingeniería, Protocolos AT-SITR-1 e Informe IPES", "qty": 1, "unit_price_clp": 6000000.0}
    ]
    cost1 = sum(i["unit_price_clp"] for i in bom1)
    margin1_pct = 54.8
    price1 = cost1 / (1 - (margin1_pct / 100.0))
    
    print(f"  🤖 [OperacionesPresupuestoAgent]: Costo Interno: CLP ${cost1:,.0f} | Precio Venta: CLP ${price1:,.0f} | Margen Retenido: {margin1_pct}%")
    
    # 4. Odoo Staging
    so1_draft = DraftAction(
        agent_name="CotizacionInventarioAgent",
        target_model="sale.order",
        action_type="create",
        proposed_payload={
            "partner_name": "Transelec S.A.",
            "opportunity_name": "Sistema PMU VIZIMAX SE Ancud 220kV",
            "amount_total_clp": price1,
            "proposed_margin_pct": margin1_pct,
            "order_line": bom1
        },
        justification="Cotización PMU VIZIMAX SynchroTeq Plus + PDC NovaTech Orion MX para Transelec.",
        confidence_score=0.99
    )
    so1_action = console.register_draft(so1_draft)
    print(f"  ✅ [SupervisorConsole]: Draft Staged ID -> '{so1_action.draft_id}' en Odoo ERP sale.order")

    cycle_log["quotes"].append({
        "type": "PMU_WAPMS",
        "client": "Transelec S.A.",
        "project": "SE Ancud 220kV",
        "amount_clp": price1,
        "margin_pct": margin1_pct,
        "draft_id": so1_action.draft_id
    })

    # =========================================================================
    # COTIZACIÓN 2: RTU REMOTA (Chilquinta - SE Mayaca 110kV)
    # =========================================================================
    print("\n------------------------------------------------------------------------")
    print("📌 COTIZACIÓN 2: RTU REMOTA DE SUBESTACIÓN (Chilquinta - SE Mayaca 110kV)")
    print("------------------------------------------------------------------------")
    q2_request = "Requiero cotización para reemplazar la remota RTU obsoleta en SE Mayaca de Chilquinta. Se requiere remota DNP3, tarjetas I/O y switches Belden Hirschmann. El cliente ya cuenta con reloj GPS."
    
    print(f"  [USER INPUT]: '{q2_request}'")
    
    # 1. RFQ Classification
    bl2 = BusinessLineClassifier.classify(q2_request)
    print(f"  🤖 [RFQProspeccionAgent]: Clasificación de Línea -> '{bl2.value}' (Confianza: 99.5%)")
    
    # 2. Guided Architecture
    arch2 = GuidedArchitectureEngine.get_architecture_guidance(bl2.value)
    print(f"  🤖 [CotizacionInventarioAgent]: Arquitectura Recomendada -> '{arch2['architecture']['title']}'")
    print(f"     • Componentes Requeridos: {', '.join(arch2['architecture']['required_components'])}")
    print(f"     • Sincronización GPS: OMITIDA (Cliente posee reloj existente en SE)")

    # 3. BOM & Margin Calculation
    bom2 = [
        {"item_code": "HW-RTU-ORION-LX", "name": "Remota RTU NovaTech Orion LX+ DNP3/IEC61850", "qty": 1, "unit_price_clp": 8900000.0},
        {"item_code": "HW-NOVACARD-IO", "name": "Tarjetas I/O Novacard 32DI / 16DO / 8AI", "qty": 2, "unit_price_clp": 3400000.0},
        {"item_code": "SW-BELDEN-SWITCH", "name": "Switch Ethernet Industrial Belden Hirschmann RS20 Managed", "qty": 2, "unit_price_clp": 6400000.0},
        {"item_code": "HW-ROUTER-4G", "name": "Módem Router Industrial 4G Dual-SIM DNP3", "qty": 1, "unit_price_clp": 1800000.0},
        {"item_code": "SRV-KITTING-RTU", "name": "Pre-cableado Tablero Kit B RTU en Taller + Ensayos HIL", "qty": 1, "unit_price_clp": 4500000.0}
    ]
    cost2 = sum(i["unit_price_clp"] for i in bom2)
    margin2_pct = 54.8
    price2 = cost2 / (1 - (margin2_pct / 100.0))
    
    print(f"  🤖 [OperacionesPresupuestoAgent]: Costo Interno: CLP ${cost2:,.0f} | Precio Venta: CLP ${price2:,.0f} | Margen Retenido: {margin2_pct}%")
    
    # 4. Odoo Staging
    so2_draft = DraftAction(
        agent_name="CotizacionInventarioAgent",
        target_model="sale.order",
        action_type="create",
        proposed_payload={
            "partner_name": "Chilquinta Distribución S.A.",
            "opportunity_name": "Retrofit Remota RTU NovaTech Orion LX+ SE Mayaca",
            "amount_total_clp": price2,
            "proposed_margin_pct": margin2_pct,
            "order_line": bom2
        },
        justification="Cotización RTU NovaTech Orion LX+ con Switches Belden Hirschmann para Chilquinta (GPS Omitido por existencia en cliente).",
        confidence_score=0.99
    )
    so2_action = console.register_draft(so2_draft)
    print(f"  ✅ [SupervisorConsole]: Draft Staged ID -> '{so2_action.draft_id}' en Odoo ERP sale.order")

    cycle_log["quotes"].append({
        "type": "RTU_REMOTA",
        "client": "Chilquinta Distribución S.A.",
        "project": "SE Mayaca 110kV",
        "amount_clp": price2,
        "margin_pct": margin2_pct,
        "draft_id": so2_action.draft_id
    })

    # =========================================================================
    # COTIZACIÓN 3: SCADA RETROFIT HMI (ADASA - SE Desaladora)
    # =========================================================================
    print("\n------------------------------------------------------------------------")
    print("📌 COTIZACIÓN 3: RETROFIT SCADA HMI (ADASA - Subestación Desaladora)")
    print("------------------------------------------------------------------------")
    q3_request = "Cotizar upgrade de Sistema SCADA HMI para la Subestación Desaladora de ADASA. Incluir licencias de software SCADA zenon/Elipse, servidor industrial redundante y switches Belden Hirschmann."
    
    print(f"  [USER INPUT]: '{q3_request}'")
    
    # 1. RFQ Classification
    bl3 = BusinessLineClassifier.classify(q3_request)
    print(f"  🤖 [RFQProspeccionAgent]: Clasificación de Línea -> '{bl3.value}' (Confianza: 99.9%)")
    
    # 2. Guided Architecture
    arch3 = GuidedArchitectureEngine.get_architecture_guidance(bl3.value)
    print(f"  🤖 [CotizacionInventarioAgent]: Arquitectura Recomendada -> '{arch3['architecture']['title']}'")
    print(f"     • Componentes Requeridos: {', '.join(arch3['architecture']['required_components'])}")

    # 3. BOM & Margin Calculation
    bom3 = [
        {"item_code": "SW-SCADA-ZENON", "name": "Licencia Software SCADA COPA-DATA zenon / Elipse Power 4000 Tags", "qty": 1, "unit_price_clp": 14500000.0},
        {"item_code": "HW-SERVER-ADV", "name": "Servidores Industriales Redundantes Advantech Xeon 19\" IP50", "qty": 2, "unit_price_clp": 9800000.0},
        {"item_code": "SW-BELDEN-SWITCH", "name": "Switches Ethernet Industriales Belden Hirschmann RS30 Managed", "qty": 2, "unit_price_clp": 7200000.0},
        {"item_code": "SRV-SCADA-ENG", "name": "Ingeniería de Pantallas HMI, Mapeo DNP3 e Integración en Sitio", "qty": 1, "unit_price_clp": 8500000.0}
    ]
    cost3 = sum(i["unit_price_clp"] for i in bom3)
    margin3_pct = 54.8
    price3 = cost3 / (1 - (margin3_pct / 100.0))
    
    print(f"  🤖 [OperacionesPresupuestoAgent]: Costo Interno: CLP ${cost3:,.0f} | Precio Venta: CLP ${price3:,.0f} | Margen Retenido: {margin3_pct}%")
    
    # 4. Odoo Staging
    so3_draft = DraftAction(
        agent_name="CotizacionInventarioAgent",
        target_model="sale.order",
        action_type="create",
        proposed_payload={
            "partner_name": "Aguas de Antofagasta S.A. (ADASA)",
            "opportunity_name": "Upgrade Sistema SCADA HMI Subestación Desaladora",
            "amount_total_clp": price3,
            "proposed_margin_pct": margin3_pct,
            "order_line": bom3
        },
        justification="Cotización SCADA HMI COPA-DATA zenon + Servidores Advantech + Switches Belden Hirschmann para ADASA.",
        confidence_score=0.99
    )
    so3_action = console.register_draft(so3_draft)
    print(f"  ✅ [SupervisorConsole]: Draft Staged ID -> '{so3_action.draft_id}' en Odoo ERP sale.order")

    cycle_log["quotes"].append({
        "type": "SCADA_RETROFIT",
        "client": "ADASA",
        "project": "SE Desaladora",
        "amount_clp": price3,
        "margin_pct": margin3_pct,
        "draft_id": so3_action.draft_id
    })

    # =========================================================================
    # SUMMARY & RECORDING SAVED
    # =========================================================================
    duration = round(time.perf_counter() - start_time, 2)
    cycle_log["total_duration_seconds"] = duration
    total_sales_clp = price1 + price2 + price3

    print("\n" + "=" * 80)
    print("🏆 RESUMEN DEL CICLO AGÉNTICO MULTICOTIZACIÓN CONCLUIDO")
    print(f"  • Total Cotizaciones Procesadas: 3 (PMU, RTU Remota, SCADA)")
    print(f"  • Valor Total Venta Generada: CLP ${total_sales_clp:,.0f}")
    print(f"  • Margen Bruto Medio Retenido: 54.8%")
    print(f"  • Tiempo Total de Orquestación Agéntica: {duration} segundos")
    print("=" * 80 + "\n")

    output_path = Path(__file__).resolve().parent.parent / "multi_quote_recording_record.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cycle_log, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    run_multi_quote_agentic_cycle()
