"""
test_full_end_to_end_system_suite.py

Suite de Pruebas Integrales End-to-End que ejecuta y valida el flujo completo del sistema Conecta:
1. Generador de Cotizaciones Word .docx (6 Secciones Oficiales)
2. Generador de Libro Excel .xlsx de 9 Pestañas (BOM, HH, Cash Flow, Check & Sensibilidad)
3. Motor Agéntico Swarm (6 Agentes Especializados: RFQ, Cotizador, Operaciones, EDPs, Gestión Doc, Conciliador)
4. Módulos de Automatización de Operaciones:
   - DocAutomator (Ficha OT, IPES, AT-SITR-1 CEN)
   - KittingEngine (BOM Rittal, VIZIMAX, Orion, Belden, Kronos)
   - FatSatSimulator (HIL FAT/SAT Lab & Certificación)
   - AccreditationAutomator (Dossier Sicop/Pronexo Digital)
   - PaymentStatementAutomator (3 EDPs: OC 30%, Ing. 40%, SAT/CEN 30% + Odoo Draft Payload)
"""

import pytest
import os
import json
from datetime import datetime

from operations.official_word_quote_builder import OfficialWordQuoteBuilder
from operations.bom_excel_builder import MultiTabBOMExcelBuilder
from operations.doc_automator import DocAutomator
from operations.kitting_engine import KittingEngine
from operations.fat_sat_simulator import FatSatSimulator
from operations.accreditation_automator import AccreditationAutomator
from operations.payment_statement_automator import PaymentStatementAutomator
from swarm_engine.swarm import AgentSwarm

SAMPLE_E2E_PROJECT = {
    "reference_no": "COT-2026-E2E-FULL",
    "ot_code": "OT-5209-E2E",
    "date_str": "Santiago, 31 de Julio de 2026",
    "client_name": "COMASA S.A.",
    "substation": "S/E Lautaro",
    "subject": "Suministro e Integración PMU Central Lautaro - Integración End-to-End",
    "lines": [
        {"item_code": "PMU-VIZI-01", "name": "Unidad de Medición Fasorial VIZIMAX SynchroTeq Plus", "product_uom_qty": 1, "price_unit": 10900000.0, "price_subtotal": 10900000.0},
        {"item_code": "GPS-KRON-01", "name": "Reloj Satelital GPS Kronos IRIG-B / PTP 1588", "product_uom_qty": 1, "price_unit": 3800000.0, "price_subtotal": 3800000.0},
        {"item_code": "SW-BELD-01", "name": "Switch Managed Belden Hirschmann RS20 IEC61850", "product_uom_qty": 1, "price_unit": 2400000.0, "price_subtotal": 2400000.0},
        {"item_code": "ENG-CEN-01", "name": "Ingeniería de Detalle y Protocolos CEN AT-SITR-1", "product_uom_qty": 1, "price_unit": 4500000.0, "price_subtotal": 4500000.0}
    ],
    "amount_untaxed": 21600000.0,
    "amount_tax": 4104000.0,
    "amount_total": 25704000.0,
    "contract_uf": 560.0,
    "margin_pct": 54.8
}


def test_e2e_word_quote_builder():
    """Fase 1: Construcción de Cotización Word .docx con 6 Secciones Oficiales"""
    builder = OfficialWordQuoteBuilder()
    doc_bytes = builder.build_quote_docx_bytes(SAMPLE_E2E_PROJECT)
    assert doc_bytes is not None
    assert len(doc_bytes) > 10000


def test_e2e_excel_9_sheet_bom_builder():
    """Fase 2: Construcción de Libro Excel .xlsx con las 9 Pestañas Conecta"""
    builder = MultiTabBOMExcelBuilder()
    excel_bytes = builder.build_workbook_bytes(SAMPLE_E2E_PROJECT)
    assert excel_bytes is not None
    assert len(excel_bytes) > 5000


def test_e2e_doc_automator():
    """Fase 3: Generación Automática de Documentos Operacionales y CEN"""
    doc_auto = DocAutomator()
    
    handover = doc_auto.generate_handover_sheet(
        ot_code=SAMPLE_E2E_PROJECT["ot_code"],
        client_name=SAMPLE_E2E_PROJECT["client_name"],
        proj_name=SAMPLE_E2E_PROJECT["subject"],
        monto_uf=SAMPLE_E2E_PROJECT["contract_uf"]
    )
    assert handover["status"] == "GENERATED_AUTOMATICALLY"

    ipes = doc_auto.generate_ipes_report(
        ot_code=SAMPLE_E2E_PROJECT["ot_code"],
        client_name=SAMPLE_E2E_PROJECT["client_name"],
        substation_name=SAMPLE_E2E_PROJECT["substation"],
        equipment_summary="PMU VIZIMAX SynchroTeq Plus"
    )
    assert ipes["status"] == "APPROVED_READY_FOR_CEN_SUBMISSION"

    fat_proto = doc_auto.generate_cen_fat_protocol(
        ot_code=SAMPLE_E2E_PROJECT["ot_code"],
        substation_name=SAMPLE_E2E_PROJECT["substation"],
        device_model="VIZIMAX / NovaTech Orion"
    )
    assert fat_proto["status"] == "READY_FOR_PDF_EXPORT"


def test_e2e_kitting_engine():
    """Fase 4: Armado de Tablero Pre-cableado en Taller (BOM Kitting)"""
    kitting = KittingEngine()
    kit = kitting.build_pmu_assembly_kit(SAMPLE_E2E_PROJECT["ot_code"])
    assert kit["pre_assembled_in_taller"] is True
    assert len(kit["bom_items"]) >= 4


def test_e2e_fat_sat_simulator():
    """Fase 5: Banco de Pruebas Virtuales HIL FAT/SAT y Certificado CEN"""
    sim = FatSatSimulator()
    fat_res = sim.run_virtual_fat_test(SAMPLE_E2E_PROJECT["ot_code"], ["VIZIMAX_PMU", "GPS_KRONOS", "BELDEN_SWITCH"])
    assert fat_res["overall_status"] == "APPROVED_100_PERCENT"

    sat_res = sim.run_virtual_sat_test(SAMPLE_E2E_PROJECT["ot_code"], SAMPLE_E2E_PROJECT["substation"], "Kevin Fuentealba")
    assert sat_res["overall_status"] == "SAT_PASSED_READY_FOR_COMMERCIAL_OPERATION"

    cert = sim.generate_test_certificate(SAMPLE_E2E_PROJECT["ot_code"], SAMPLE_E2E_PROJECT["client_name"])
    assert cert["cen_normative_compliance"] == "CEN_AT_SITR_1_COMPLIANT"


def test_e2e_accreditation_automator():
    """Fase 6: Compilación de Dossier Digital de Acreditación Sicop / Pronexo"""
    acc = AccreditationAutomator()
    dossier = acc.compile_platform_dossier("15.432.890-1", "Kevin Fuentealba", SAMPLE_E2E_PROJECT["substation"], "Sicop")
    assert dossier["dossier_status"] == "READY_FOR_PLATFORM_UPLOAD"


def test_e2e_payment_statement_automator():
    """Fase 7: Emisión de Estados de Pago (3 Hitos: OC 30%, Ing. 40%, SAT 30%) y Payload Odoo"""
    pay = PaymentStatementAutomator()
    
    edp1 = pay.generate_payment_statement(SAMPLE_E2E_PROJECT["ot_code"], SAMPLE_E2E_PROJECT["client_name"], "EDP 1 - OC", 30.0, SAMPLE_E2E_PROJECT["contract_uf"])
    assert edp1["amount_uf"] == 168.0

    edp2 = pay.generate_payment_statement(SAMPLE_E2E_PROJECT["ot_code"], SAMPLE_E2E_PROJECT["client_name"], "EDP 2 - Ing", 40.0, SAMPLE_E2E_PROJECT["contract_uf"])
    assert edp2["amount_uf"] == 224.0

    edp3 = pay.generate_payment_statement(SAMPLE_E2E_PROJECT["ot_code"], SAMPLE_E2E_PROJECT["client_name"], "EDP 3 - SAT", 30.0, SAMPLE_E2E_PROJECT["contract_uf"])
    assert edp3["amount_uf"] == 168.0

    odoo_payload = pay.create_odoo_invoice_draft_payload(SAMPLE_E2E_PROJECT["ot_code"], edp1)
    assert odoo_payload["odoo_model"] == "account.move"
    assert odoo_payload["move_type"] == "out_invoice"


def test_e2e_swarm_engine():
    """Fase 8: Orquestación Agéntica Swarm (6 Agentes Especializados)"""
    swarm = AgentSwarm()
    agents = swarm.list_agents()
    assert len(agents) >= 6

    for agent_name in agents:
        action = swarm.process_task(agent_name, {"ot_code": SAMPLE_E2E_PROJECT["ot_code"], "client": SAMPLE_E2E_PROJECT["client_name"]})
        assert action is not None
