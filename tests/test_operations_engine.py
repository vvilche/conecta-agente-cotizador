import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.operations.config_automator import ConfigAutomator
from src.operations.fat_sat_simulator import FatSatSimulator
from src.operations.kitting_engine import KittingEngine
from src.operations.doc_automator import DocAutomator
from src.operations.payment_statement_automator import PaymentStatementAutomator
from src.operations.accreditation_automator import AccreditationAutomator
from src.operations.financial_engine import FinancialImpactEngine


def test_payment_statement_automator():
    edp_engine = PaymentStatementAutomator()
    edp = edp_engine.generate_payment_statement(
        ot_code="OT-7048",
        client_name="Enel Generación",
        milestone_name="Hito 2: Entrega Equipos y Pruebas FAT",
        milestone_pct=50.0,
        total_contract_uf=1500.0
    )
    assert edp["statement_id"] == "EDP-OT-7048-M50"
    assert edp["amount_uf"] == 750.0
    assert edp["status"] == "READY_FOR_CLIENT_INVOICING"
    assert edp["days_saved_in_collection"] == 25.0

    # Test attached signed FAT/SAT certificate
    cert_att = edp_engine.attach_signed_fat_sat_certificate(
        ot_code="OT-7048",
        certificate_id="CERT-FAT-7048",
        digital_signature="SIG-RSA2048-SECURE-HASH-998877"
    )
    assert cert_att["signature_status"] == "VALIDATED_RSA_SHA256"
    assert cert_att["vobo_eligible"] is True

    # Test Odoo invoice draft payload
    odoo_draft = edp_engine.create_odoo_invoice_draft_payload("OT-7048", edp)
    assert odoo_draft["odoo_model"] == "account.move"
    assert odoo_draft["move_type"] == "out_invoice"
    assert odoo_draft["ref"] == "EDP-OT-7048"
    assert odoo_draft["analytic_account_mapping"]["ot_code"] == "OT-7048"
    assert odoo_draft["vobo_billing_trigger"]["vobo_approved"] is True


def test_accreditation_automator():
    acc_engine = AccreditationAutomator()
    workers = [
        {"rut": "15.420.110-8", "name": "Carlos Mendoza"},
        {"rut": "16.890.344-K", "name": "Roberto Silva"}
    ]
    pkg = acc_engine.generate_substation_access_package(
        ot_code="OT-7060",
        client="Transelec",
        workers=workers
    )
    assert pkg["package_id"] == "ACREDITACION-OT-7060-TRANSELEC"
    assert pkg["total_workers"] == 2
    assert pkg["overall_accreditation"] == "READY_FOR_SUBMISSION"

    # Test platform dossier compilation (Sicop, Pronexo, RyS)
    for platform in ["Sicop", "Pronexo", "RyS"]:
        dossier = acc_engine.compile_platform_dossier(
            worker_rut="15.420.110-8",
            worker_name="Carlos Mendoza",
            substation="Subestación Ancud",
            target_platform=platform
        )
        assert dossier["target_platform"] == platform
        assert len(dossier["documents"]) > 0

    # Test document expiration audit
    sample_dossier = acc_engine.compile_worker_dossier("15.420.110-8", "Carlos Mendoza", "Ancud")
    # Add an expired doc for testing
    sample_dossier["documents"].append({"doc": "Pase de Ingreso Antiguo", "status": "EXPIRED", "expires": "2020-01-01"})
    audit = acc_engine.audit_document_expirations(sample_dossier)
    assert audit["expired_count"] == 1
    assert audit["overall_status"] == "CRITICAL_ACTION_REQUIRED"


def test_doc_automator():
    doc_engine = DocAutomator()
    handover = doc_engine.generate_handover_sheet(
        ot_code="OT-7046", client_name="TECMA", proj_name="Andes Solar II", monto_uf=1475.76, output_format="docx"
    )
    assert handover["doc_id"] == "FICHA-TRASPASO-OT-7046"
    assert handover["status"] == "GENERATED_AUTOMATICALLY"
    assert handover["output_format"] == "docx"
    assert "file_payload" in handover
    assert handover["generation_duration_seconds"] > 0.0

    fat_proto = doc_engine.generate_cen_fat_protocol(
        ot_code="OT-7048", substation_name="Subestación Ancud", device_model="SEL-735", output_format="pdf"
    )
    assert fat_proto["doc_id"] == "PROTOCOL-FAT-CEN-OT-7048"
    assert fat_proto["output_format"] == "pdf"

    ipes = doc_engine.generate_ipes_report(
        ot_code="OT-7048", client_name="Enel", substation_name="Ancud", equipment_summary="PMU + Orion MX"
    )
    assert ipes["doc_id"] == "INFORME-IPES-OT-7048"
    assert ipes["status"] == "APPROVED_READY_FOR_CEN_SUBMISSION"
    assert "generation_duration_seconds" in ipes

    batch = doc_engine.batch_generate_ot_documentation(ot_code="OT-7050", client="WPD", proj="Parque Eólico", output_format="pdf")
    assert len(batch) >= 4
    assert any("IPES" in doc["doc_id"] for doc in batch)


def test_config_automator_pmu():
    automator = ConfigAutomator()
    res = automator.generate_pmu_config(ot_code="OT-7042", substation_name="Subestación Ancud", pmu_id=1)
    assert res["ot_code"] == "OT-7042"
    assert res["device_type"] == "Vizimax SynchroTeq Plus PMU"
    assert res["ip_address"] == "192.168.10.11"
    assert res["protocol"] == "IEEE C37.118-2011"
    assert res["estimated_hh_saved"] == 33.0


def test_config_automator_orion_and_gps():
    automator = ConfigAutomator()
    rtu_res = automator.generate_rtu_orion_config(ot_code="OT-7056", points_count=150)
    assert rtu_res["device_type"] == "NovaTech Orion MX"
    assert rtu_res["points_count"] == 150

    gps_scripts = automator.generate_gps_kronos_script(ot_code="OT-7055", device_count=3)
    assert len(gps_scripts) == 3
    assert gps_scripts[0]["device_id"] == "KRONOS-GPS-01"


def test_fat_sat_simulator():
    sim = FatSatSimulator()
    fat_res = sim.run_virtual_fat_test(ot_code="OT-7048", device_list=["SEL-735", "ORION-MX"])
    assert fat_res["overall_status"] == "APPROVED_100_PERCENT"
    assert fat_res["tested_devices_count"] == 2
    assert fat_res["field_days_saved"] == 3.5

    sat_res = sim.run_virtual_sat_test(ot_code="OT-7048", substation_name="Subestación Ancud", engineer_name="Víctor Vilche")
    assert sat_res["overall_status"] == "SAT_PASSED_READY_FOR_COMMERCIAL_OPERATION"
    assert sat_res["trigger_invoice_milestone"] is True

    cert = sim.generate_test_certificate(ot_code="OT-7048", client_name="Enel Generación")
    assert cert["certificate_id"] == "CERT-FAT-SAT-OT-7048-2026"
    assert cert["approval_status"] == "READY_FOR_CLIENT_SIGNATURE"

    # Test HIL Telemetry simulation
    hil_res = sim.run_hil_telemetry_simulation(
        ot_code="OT-7048", line_type="PMU_SITR", duration_seconds=5.0, packet_loss_rate=0.01, latency_ms=8.5
    )
    assert hil_res["simulation_status"] == "COMPLETED_SUCCESSFULLY"
    assert hil_res["dnp3_points"]["binary_count"] > 0
    assert hil_res["ieee_c37_118_synchrophasors"]["frame_rate_fps"] == 50
    assert hil_res["timestamp_sync_audit"]["microsecond_accuracy_verified"] is True


def test_kitting_engine():
    engine = KittingEngine()
    pmu_kit = engine.build_pmu_assembly_kit(ot_code="OT-7050")
    assert pmu_kit["kit_type"] == "PMU_PANEL_KIT_A"
    assert len(pmu_kit["bom_items"]) == 5

    scada_kit = engine.build_scada_rtu_kit(ot_code="OT-7051")
    assert scada_kit["kit_type"] == "SCADA_RTU_KIT_B"
    assert len(scada_kit["bom_items"]) == 5

    # Test Odoo inventory verification
    inv = engine.verify_inventory_stock("PMU_PANEL_KIT_A")
    assert inv["stock_available"] is True
    assert len(inv["stock_details"]) == 5

    # Test workshop checklist
    checklist = engine.get_prewiring_workshop_checklist("PMU_PANEL_KIT_A")
    assert len(checklist) == 5
    categories = [item["category"] for item in checklist]
    assert "wiring_continuity" in categories
    assert "aislacion_electrica" in categories
    assert "rotulacion_termocontraible" in categories


def test_financial_impact_engine():
    fin_engine = FinancialImpactEngine()
    assert fin_engine.retained_gross_margin_pct() == 54.8

    hh = fin_engine.calculate_released_man_hours(num_ots=5, num_devices=10, num_workers=4)
    assert hh["total_released_hh"] > 0
    assert hh["doc_generation_hh"] == 35.0

    days = fin_engine.calculate_reduced_field_days(num_ots=5, num_substations=3)
    assert days["total_reduced_field_days"] == 17.5

    summary = fin_engine.calculate_financial_summary(
        num_ots=5, total_contract_uf=3500.0, uf_value_clp=38377.09, num_devices=10, num_workers=4, num_substations=3
    )
    assert summary["retained_gross_margin_pct"] == 54.8
    assert summary["retained_gross_margin_clp"] > 0
    assert summary["total_savings_clp"] > 0
    assert summary["released_hh"] == hh["total_released_hh"]
    assert summary["reduced_field_days"] == 17.5


# =====================================================================
# EXPANDED EDGE CASE & PARAMETERIZED TEST SUITE FOR OPERATIONS ENGINE
# =====================================================================

@pytest.mark.parametrize("pct, contract_uf, expected_amount_uf", [
    (10.0, 1000.0, 100.0),
    (30.0, 1500.0, 450.0),
    (50.0, 2000.0, 1000.0),
    (100.0, 800.0, 800.0),
])
def test_payment_statement_milestone_percentages(pct, contract_uf, expected_amount_uf):
    edp_engine = PaymentStatementAutomator()
    edp = edp_engine.generate_payment_statement(
        ot_code="OT-9000",
        client_name="Test Client",
        milestone_name="Hito Test",
        milestone_pct=pct,
        total_contract_uf=contract_uf
    )
    assert edp["amount_uf"] == expected_amount_uf


@pytest.mark.parametrize("platform", ["Sicop", "Pronexo", "RyS"])
def test_accreditation_platform_dossiers(platform):
    acc_engine = AccreditationAutomator()
    dossier = acc_engine.compile_platform_dossier(
        worker_rut="12.345.678-9",
        worker_name="Juan Perez",
        substation="SE Ancoa",
        target_platform=platform
    )
    assert dossier["target_platform"] == platform
    assert isinstance(dossier["documents"], list)
    assert len(dossier["documents"]) > 0


@pytest.mark.parametrize("points_count", [10, 50, 150, 500, 1000])
def test_config_automator_orion_varying_points(points_count):
    automator = ConfigAutomator()
    res = automator.generate_rtu_orion_config(ot_code="OT-TEST", points_count=points_count)
    assert res["points_count"] == points_count


@pytest.mark.parametrize("device_count", [1, 2, 5, 10])
def test_config_automator_gps_device_counts(device_count):
    automator = ConfigAutomator()
    scripts = automator.generate_gps_kronos_script(ot_code="OT-GPS", device_count=device_count)
    assert len(scripts) == device_count


@pytest.mark.parametrize("loss, latency", [
    (0.0, 1.0),
    (0.01, 8.5),
    (0.05, 50.0),
])
def test_hil_telemetry_simulation_network_conditions(loss, latency):
    sim = FatSatSimulator()
    hil = sim.run_hil_telemetry_simulation(
        ot_code="OT-HIL", line_type="PMU_SITR", duration_seconds=2.0, packet_loss_rate=loss, latency_ms=latency
    )
    assert hil["simulation_status"] == "COMPLETED_SUCCESSFULLY"
    assert hil["network_parameters"]["packet_loss_rate"] == loss
    assert hil["network_parameters"]["latency_ms"] == latency
