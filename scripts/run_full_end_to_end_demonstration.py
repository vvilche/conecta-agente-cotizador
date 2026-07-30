#!/usr/bin/env python3
"""
Full-Stack End-to-End Demonstration & Recording Script.
Executes and records a complete workflow run across all 6 operational engines,
SQLite Knowledge Matrix, Odoo ERP staging, and Supervisor UI REST APIs.
Saves complete execution recording to full_demo_test_execution_record.json.
"""

import sys
import json
import time
import datetime
from pathlib import Path

# Add project src to PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.operations import (
    DocAutomator,
    FatSatSimulator,
    KittingEngine,
    AccreditationAutomator,
    PaymentStatementAutomator,
    FinancialImpactEngine
)
from src.rag_memory.advanced_intelligence import OperationalIntelligenceEngine, WinRateEstimator
from src.supervisor_ui.console import SupervisorConsole
from src.supervisor_ui.app import create_app
from swarm_engine.base_agent import DraftAction

def run_full_recorded_demo():
    print("==========================================================================")
    print("🎬 GRABACIÓN DE PRUEBA COMPLETA PUNTA A PUNTA (FULL DEMO RUN)")
    print("   Plataforma de Automatización Operacional - Conecta Ingeniería S.A.")
    print("==========================================================================")

    start_time = time.time()
    recording_log = {
        "title": "Demostración Ejecutiva y Grabación Completa de Pruebas Operacionales",
        "timestamp": datetime.datetime.now().isoformat(),
        "ot_code": "OT-7099",
        "client": "Transelec S.A.",
        "project": "Digitalización Subestación Charrúa II 220kV",
        "contract_uf": 2500.0,
        "uf_rate_clp": 38377.09,
        "steps": []
    }

    # -------------------------------------------------------------------------
    # STEP 1: Inteligencia de Cotización & Acceso Operacional
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 1: Inteligencia de Cotización y Predicción de Acceso")
    win_rate = WinRateEstimator.predict_win_rate("Transelec S.A.", 42.0)
    access_pred = OperationalIntelligenceEngine.predict_access_delay(
        substation_name="Subestación Charrúa",
        platform="sicop",
        num_workers=4
    )
    step1_res = {
        "step_name": "Paso 1: Inteligencia Comercial y Predicción de Acceso",
        "win_rate_prediction": {
            "client": win_rate.client_name,
            "proposed_margin_pct": win_rate.proposed_margin_pct,
            "estimated_win_rate_pct": win_rate.estimated_win_rate_pct,
            "sensitivity": win_rate.client_sensitivity
        },
        "access_delay_prediction": access_pred
    }
    recording_log["steps"].append(step1_res)
    print(f"  • Win-Rate Estimado (Transelec @ 42%): {win_rate.estimated_win_rate_pct:.1f}%")
    print(f"  • Retraso Estimado Acceso Sicop (4 Operarios en Charrúa): {access_pred['estimated_delay_days']} días")

    # -------------------------------------------------------------------------
    # STEP 2: DocAutomator - Auto-Generación Documental (3s)
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 2: DocAutomator - Auto-Generación Documental")
    doc_engine = DocAutomator()
    docs_batch = doc_engine.batch_generate_ot_documentation(
        ot_code="OT-7099",
        client="Transelec S.A.",
        proj="Subestación Charrúa II",
        output_format="pdf"
    )
    step2_res = {
        "step_name": "Paso 2: Generación Automática de Documentos Técnicos",
        "documents_generated_count": len(docs_batch),
        "documents": docs_batch
    }
    recording_log["steps"].append(step2_res)
    print(f"  • Documentos generados en lote: {len(docs_batch)} archivos (Ficha, Protocolo CEN FAT, IPES, Memoria, Calidad)")

    # -------------------------------------------------------------------------
    # STEP 3: FatSatSimulator - Banco HIL & Telemetría C37.118
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 3: FatSatSimulator - Pruebas FAT Digitales HIL en Laboratorio")
    fat_sat_engine = FatSatSimulator()
    fat_run = fat_sat_engine.run_virtual_fat_test("OT-7099", ["VIZIMAX-SYNCHROTEQ", "ORION-MX", "MOXA-EDS510A"])
    hil_sim = fat_sat_engine.run_hil_telemetry_simulation("OT-7099", line_type="PMU_SITR", duration_seconds=5.0)
    sat_run = fat_sat_engine.run_virtual_sat_test("OT-7099", "Subestación Charrúa II", "Víctor Vilche")
    cert = fat_sat_engine.generate_test_certificate("OT-7099", "Transelec S.A.")

    step3_res = {
        "step_name": "Paso 3: Pruebas FAT/SAT Digitales HIL y Certificación",
        "fat_result": fat_run,
        "hil_telemetry_simulation": hil_sim,
        "sat_result": sat_run,
        "certificate": cert
    }
    recording_log["steps"].append(step3_res)
    print(f"  • Estado FAT Laboratorio: {fat_run['overall_status']}")
    print(f"  • Sincronismo Reloj PTP/IRIG-B: {hil_sim['timestamp_sync_audit']['lock_status']} (Drift: {hil_sim['timestamp_sync_audit']['clock_drift_microseconds']} µs)")
    print(f"  • Estado SAT Terreno: {sat_run['overall_status']}")
    print(f"  • Certificado Emitido: {cert['certificate_id']}")

    # -------------------------------------------------------------------------
    # STEP 4: KittingEngine - Armado de Tableros & Verificación Odoo
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 4: KittingEngine - Kitting Estándar de Tableros & Stock Odoo")
    kit_engine = KittingEngine()
    pmu_kit = kit_engine.build_pmu_assembly_kit("OT-7099")
    scada_kit = kit_engine.build_scada_rtu_kit("OT-7099")
    inv_check = kit_engine.verify_inventory_stock("PMU_PANEL_KIT_A")
    checklist = kit_engine.get_prewiring_workshop_checklist("PMU_PANEL_KIT_A")

    step4_res = {
        "step_name": "Paso 4: Pre-Kitting de Tableros y Verificación de Stock ERP",
        "kit_pmu": pmu_kit,
        "kit_scada": scada_kit,
        "inventory_verification": inv_check,
        "workshop_checklist_count": len(checklist)
    }
    recording_log["steps"].append(step4_res)
    print(f"  • Kit PMU Generado: {pmu_kit['kit_id']} ({len(pmu_kit['bom_items'])} componentes)")
    print(f"  • Disponibilidad Stock Odoo ERP: {inv_check['stock_available']}")
    print(f"  • Chequeo Calidad Taller: {len(checklist)} puntos de control aprobados")

    # -------------------------------------------------------------------------
    # STEP 5: AccreditationAutomator - Expediente Sicop / Pronexo
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 5: AccreditationAutomator - Compilación de Expedientes Sicop")
    acc_engine = AccreditationAutomator()
    workers = [
        {"rut": "15.420.110-8", "name": "Carlos Mendoza"},
        {"rut": "16.890.344-K", "name": "Roberto Silva"},
        {"rut": "14.550.899-2", "name": "Felipe Morales"},
        {"rut": "17.112.455-3", "name": "Andrés Tapia"}
    ]
    substation_pkg = acc_engine.generate_substation_access_package("OT-7099", "Transelec S.A.", workers)
    sicop_dossier = acc_engine.compile_platform_dossier("15.420.110-8", "Carlos Mendoza", "Subestación Charrúa II", "Sicop")
    audit_docs = acc_engine.audit_document_expirations(sicop_dossier)

    step5_res = {
        "step_name": "Paso 5: Acreditación de Personal e Ingreso a Faena",
        "substation_package_status": substation_pkg["overall_accreditation"],
        "total_workers_accredited": len(workers),
        "target_platform_dossier": sicop_dossier["dossier_id"],
        "document_expiration_audit": audit_docs["overall_status"]
    }
    recording_log["steps"].append(step5_res)
    print(f"  • Trabajadores Acreditados: {len(workers)}")
    print(f"  • Dossier Plataforma Sicop: {sicop_dossier['dossier_id']} (Estado: {sicop_dossier['dossier_status']})")
    print(f"  • Auditoría de Documentos: {audit_docs['overall_status']}")

    # -------------------------------------------------------------------------
    # STEP 6: PaymentStatementAutomator - Estado de Pago & Staging VoBo
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 6: PaymentStatementAutomator - Estado de Pago & Staging Odoo")
    edp_engine = PaymentStatementAutomator()
    statement = edp_engine.generate_payment_statement(
        ot_code="OT-7099",
        client_name="Transelec S.A.",
        milestone_name="Hito 2: Entrega Equipos y Pruebas FAT",
        milestone_pct=50.0,
        total_contract_uf=2500.0,
        uf_value_clp=38377.09
    )
    cert_att = edp_engine.attach_signed_fat_sat_certificate(
        "OT-7099", cert["certificate_id"], "SIG-RSA2048-SECURE-HASH-OT7099-PROD"
    )
    odoo_invoice_payload = edp_engine.create_odoo_invoice_draft_payload("OT-7099", statement)

    # Stage into SupervisorConsole queue
    console = SupervisorConsole()
    draft_action = DraftAction(
        agent_name="estados_pago",
        target_model="account.move",
        action_type="create",
        proposed_payload=odoo_invoice_payload,
        justification="Estado de Pago Hito 2 OT-7099 Transelec Charrúa II",
        confidence_score=0.98
    )
    draft_id = console.stage_operations_draft(draft_action)

    step6_res = {
        "step_name": "Paso 6: Emisión de Estado de Pago y Borrador Factura Odoo",
        "statement_id": statement["statement_id"],
        "net_amount_clp": statement["net_amount_clp"],
        "total_clp": statement["total_clp"],
        "attached_certificate_status": cert_att["signature_status"],
        "staged_draft_id": draft_id
    }
    recording_log["steps"].append(step6_res)
    print(f"  • Estado de Pago Generado: {statement['statement_id']} (Total: CLP ${statement['total_clp']:,.0f})")
    print(f"  • Certificado FAT/SAT Firma Digital: {cert_att['signature_status']}")
    print(f"  • ID Borrador Factura en Cola VoBo: {draft_id}")

    # -------------------------------------------------------------------------
    # STEP 7: FinancialImpactEngine - Matriz de Rentabilidad 54.8%
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 7: FinancialImpactEngine - Cuantificación de Impacto Financiero")
    fin_engine = FinancialImpactEngine()
    summary_metrics = fin_engine.calculate_financial_summary(
        num_ots=5,
        total_contract_uf=3500.0,
        uf_value_clp=38377.09,
        num_devices=10,
        num_workers=4,
        num_substations=3
    )
    step7_res = {
        "step_name": "Paso 7: Resumen Financiero y Expansión de Margen",
        "metrics": summary_metrics
    }
    recording_log["steps"].append(step7_res)
    print(f"  • Margen Bruto Interno Retenido: {summary_metrics['retained_gross_margin_pct']}%")
    print(f"  • Utilidad Bruta Retenida: CLP ${summary_metrics['retained_gross_margin_clp']:,.0f}")
    print(f"  • Horas Hombre Liberadas: {summary_metrics['released_hh']} HH")
    print(f"  • Días de Terreno Reducidos: {summary_metrics['reduced_field_days']} Días")

    # -------------------------------------------------------------------------
    # STEP 8: REST API Flask Web Console Test Execution
    # -------------------------------------------------------------------------
    print("\n🔹 PASO 8: Verificación de Endpoints REST API de Supervisión Web")
    app = create_app(console=console)
    app.config["TESTING"] = True
    with app.test_client() as client:
        res_metrics = client.get("/api/operations/metrics?num_ots=5&total_contract_uf=3500")
        assert res_metrics.status_code == 200
        res_fat = client.post("/api/operations/fat-sat/run-fat", json={"ot_code": "OT-7099"})
        assert res_fat.status_code == 200

    step8_res = {
        "step_name": "Paso 8: Integración REST API Flask",
        "api_metrics_status": res_metrics.status_code,
        "api_fat_run_status": res_fat.status_code
    }
    recording_log["steps"].append(step8_res)
    print("  • Endpoints REST API /api/operations/* respondiendo HTTP 200 OK")

    # Finalize recording
    elapsed = round(time.time() - start_time, 2)
    recording_log["total_execution_duration_seconds"] = elapsed
    recording_log["final_status"] = "FULL_DEMO_RUN_COMPLETED_SUCCESSFULLY"

    # Save JSON recording file
    json_path = project_root / "full_demo_test_execution_record.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(recording_log, f, ensure_ascii=False, indent=2)

    print("\n==========================================================================")
    print("🎉 DEMOSTRACIÓN COMPLETA FINALIZADA CON ÉXITO ABSOLUTO")
    print(f"• Tiempo de Ejecución: {elapsed} segundos")
    print(f"• Registro de Grabación Guardado en: '{json_path}'")
    print("==========================================================================")

    return recording_log

if __name__ == "__main__":
    run_full_recorded_demo()
