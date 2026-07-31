"""
test_operations_automations_benchmark.py

Suite de pruebas de benchmark para validar los 5 módulos de automatización operacionales:
1. DocAutomator (Fichas, IPES, AT-SITR-1)
2. KittingEngine (BOM Kit PMU / RTU pre-cableado)
3. FatSatSimulator (Simulación HIL y Certificado FAT/SAT)
4. AccreditationAutomator (Dossier Digital Sicop / Pronexo)
5. PaymentStatementAutomator (Estados de Pago EDP 1 / EDP 2 & Odoo Payload)

Compara las salidas generadas contra 5 OTs históricas reales de Conecta S.A.
"""

import pytest
import json
import os
from datetime import datetime

from operations.doc_automator import DocAutomator
from operations.kitting_engine import KittingEngine
from operations.fat_sat_simulator import FatSatSimulator
from operations.accreditation_automator import AccreditationAutomator
from operations.payment_statement_automator import PaymentStatementAutomator

# 5 Historical Benchmark OTs
BENCHMARK_OTS = [
    {
        "ot_code": "OT 5209-00",
        "client": "COMASA S.A.",
        "project": "Implementación PMU Central Lautaro",
        "substation": "S/E Lautaro",
        "kit_type": "PMU",
        "line_type": "PMU_SITR",
        "contract_uf": 450.0,
        "monto_neto_clp": 17500000.0,
        "historical_margin_pct": 52.0
    },
    {
        "ot_code": "OT 5207-00",
        "client": "Tinguiririca Energía",
        "project": "Implementación PMUs La Higuera y La Confluencia",
        "substation": "S/E La Confluencia",
        "kit_type": "PMU",
        "line_type": "PMU_SITR",
        "contract_uf": 868.5,
        "monto_neto_clp": 33329000.0,
        "historical_margin_pct": 45.0
    },
    {
        "ot_code": "OT 5225-00",
        "client": "AES Andes S.A.",
        "project": "Suministro e Integración 10 PMUs Zona Cordillera",
        "substation": "S/E Cordillera",
        "kit_type": "PMU",
        "line_type": "PMU_SITR",
        "contract_uf": 3120.0,
        "monto_neto_clp": 120000000.0,
        "historical_margin_pct": 37.0
    },
    {
        "ot_code": "OT 5181-00",
        "client": "Chilquinta Transmisión S.A.",
        "project": "Retrofit de RTU SE Ventana",
        "substation": "S/E Ventana",
        "kit_type": "SCADA_RTU",
        "line_type": "PAC_PROTECTION",
        "contract_uf": 807.0,
        "monto_neto_clp": 31000000.0,
        "historical_margin_pct": 54.8
    },
    {
        "ot_code": "OT 5219-00",
        "client": "CGE Transmisión S.A.",
        "project": "Licitación PMU 6 Subestaciones CGET",
        "substation": "S/E Alcones",
        "kit_type": "PMU",
        "line_type": "PMU_SITR",
        "contract_uf": 2230.0,
        "monto_neto_clp": 85580000.0,
        "historical_margin_pct": 35.6
    }
]


def test_doc_automator_benchmark():
    """Prueba 1: DocAutomator genera Ficha, IPES y AT-SITR-1 para las 5 OTs históricas"""
    doc_automator = DocAutomator()

    for ot in BENCHMARK_OTS:
        # Generate handover sheet
        f_doc = doc_automator.generate_handover_sheet(
            ot_code=ot["ot_code"],
            client_name=ot["client"],
            proj_name=ot["project"],
            monto_uf=ot["contract_uf"],
            output_format="json"
        )
        assert f_doc["ot_code"] == ot["ot_code"]
        assert f_doc["status"] == "GENERATED_AUTOMATICALLY"

        # Generate IPES report
        ipes = doc_automator.generate_ipes_report(
            ot_code=ot["ot_code"],
            client_name=ot["client"],
            substation_name=ot["substation"],
            equipment_summary=ot["project"],
            output_format="json"
        )
        assert ipes["ot_code"] == ot["ot_code"]
        assert ipes["status"] == "APPROVED_READY_FOR_CEN_SUBMISSION"

        # Generate CEN FAT protocol
        cen_fat = doc_automator.generate_cen_fat_protocol(
            ot_code=ot["ot_code"],
            substation_name=ot["substation"],
            device_model="VIZIMAX / NovaTech Orion",
            output_format="json"
        )
        assert cen_fat["ot_code"] == ot["ot_code"]
        assert cen_fat["status"] == "READY_FOR_PDF_EXPORT"


def test_kitting_engine_benchmark():
    """Prueba 2: KittingEngine arma tableros pre-cableados y valida BOMs"""
    kitting = KittingEngine()

    for ot in BENCHMARK_OTS:
        if ot["kit_type"] == "PMU":
            kit = kitting.build_pmu_assembly_kit(ot["ot_code"])
            assert len(kit["bom_items"]) >= 3
            assert kit["pre_assembled_in_taller"] is True
        else:
            kit = kitting.build_scada_rtu_kit(ot["ot_code"])
            assert len(kit["bom_items"]) >= 3
            assert kit["pre_assembled_in_taller"] is True

        checklist = kitting.get_prewiring_workshop_checklist(ot["kit_type"])
        assert len(checklist) >= 4


def test_fat_sat_simulator_benchmark():
    """Prueba 3: FatSatSimulator ejecuta simulación HIL y certifica FAT en taller"""
    sim = FatSatSimulator()

    for ot in BENCHMARK_OTS:
        # Run virtual HIL FAT
        fat_res = sim.run_virtual_fat_test(ot["ot_code"], ["VIZIMAX_PMU", "ORION_RTU", "GPS_KRONOS"])
        assert fat_res["overall_status"] == "APPROVED_100_PERCENT"
        assert fat_res["tested_devices_count"] == 3

        # Run virtual SAT
        sat_res = sim.run_virtual_sat_test(ot["ot_code"], ot["substation"], "Ingeniero Conecta")
        assert sat_res["overall_status"] == "SAT_PASSED_READY_FOR_COMMERCIAL_OPERATION"

        # Generate test cert
        cert = sim.generate_test_certificate(ot["ot_code"], ot["client"])
        assert cert["cen_normative_compliance"] == "CEN_AT_SITR_1_COMPLIANT"


def test_accreditation_automator_benchmark():
    """Prueba 4: AccreditationAutomator compila dossiers expres para Sicop/Pronexo"""
    acc = AccreditationAutomator()

    for ot in BENCHMARK_OTS:
        workers = [
            {"rut": "15.432.890-1", "name": "Kevin Fuentealba", "role": "Ingeniero Residente"},
            {"rut": "16.789.123-4", "name": "Bruno Jofré", "role": "Técnico Especialista"}
        ]
        pkg = acc.generate_substation_access_package(ot["ot_code"], ot["client"], workers)
        assert pkg["overall_accreditation"] == "READY_FOR_SUBMISSION"
        assert pkg["total_workers"] == 2

        dossier = acc.compile_platform_dossier("15.432.890-1", "Kevin Fuentealba", ot["substation"], "Sicop")
        assert dossier["dossier_status"] == "READY_FOR_PLATFORM_UPLOAD"


def test_payment_statement_automator_benchmark():
    """Prueba 5: PaymentStatementAutomator emite EDP 1 (50%) y EDP 2 (50%) disparando Odoo"""
    pay = PaymentStatementAutomator()

    for ot in BENCHMARK_OTS:
        # EDP 1 - FAT Milestone (50%)
        edp1 = pay.generate_payment_statement(
            ot_code=ot["ot_code"],
            client_name=ot["client"],
            milestone_name="EDP 1 - Pre-kitting & Pruebas FAT HIL Taller",
            milestone_pct=50.0,
            total_contract_uf=ot["contract_uf"]
        )
        assert edp1["amount_uf"] == round(ot["contract_uf"] * 0.5, 2)

        # Odoo Invoice Payload
        odoo_payload = pay.create_odoo_invoice_draft_payload(ot["ot_code"], edp1)
        assert odoo_payload["partner_id"] == ot["client"]
        assert odoo_payload["move_type"] == "out_invoice"

        # EDP 2 - SAT Milestone (50%)
        edp2 = pay.generate_payment_statement(
            ot_code=ot["ot_code"],
            client_name=ot["client"],
            milestone_name="EDP 2 - Comisionamiento SAT Terreno & Informe IPES CEN",
            milestone_pct=50.0,
            total_contract_uf=ot["contract_uf"]
        )
        assert edp2["amount_uf"] == round(ot["contract_uf"] * 0.5, 2)
