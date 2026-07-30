"""
Unit tests for all 8 REST API endpoints under /api/operations/ using Flask test client.
1. POST /api/operations/doc-automator/generate
2. POST /api/operations/fat-sat/run-fat
3. POST /api/operations/fat-sat/run-sat
4. POST /api/operations/fat-sat/certificate
5. POST /api/operations/kitting/build-kit
6. POST /api/operations/accreditation/compile
7. POST /api/operations/payment-statement/generate
8. GET /api/operations/metrics
"""

import pytest
from supervisor_ui.app import create_app
from supervisor_ui.console import SupervisorConsole


@pytest.fixture
def client():
    """Creates a Flask test client for testing REST API endpoints."""
    console = SupervisorConsole()
    app = create_app(console=console)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


class TestOperationsUIEndpoints:
    """Test suite covering all 8 /api/operations/ endpoints."""

    # -------------------------------------------------------------
    # Endpoint 1: POST /api/operations/doc-automator/generate
    # -------------------------------------------------------------
    def test_doc_automator_generate_handover(self, client):
        """Test generating handover sheet via REST API."""
        payload = {
            "doc_type": "handover",
            "ot_code": "OT-7048",
            "client_name": "Enel Generación Chile",
            "proj_name": "Planta Solar CEME 1",
            "monto_uf": 1500.0,
            "output_format": "pdf"
        }
        res = client.post("/api/operations/doc-automator/generate", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["doc_type"] == "handover"
        assert "document" in data
        assert data["document"]["ot_code"] == "OT-7048"

    def test_doc_automator_generate_fat_protocol(self, client):
        """Test generating FAT protocol document via REST API."""
        payload = {
            "doc_type": "fat_protocol",
            "ot_code": "OT-7049",
            "substation_name": "Subestación Ancud",
            "device_model": "SEL-735 / Orion MX"
        }
        res = client.post("/api/operations/doc-automator/generate", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["doc_type"] == "fat_protocol"

    def test_doc_automator_generate_ipes(self, client):
        """Test generating IPES report document via REST API."""
        payload = {
            "doc_type": "ipes",
            "ot_code": "OT-7050",
            "client_name": "Transelec",
            "substation_name": "Subestación Charrúa"
        }
        res = client.post("/api/operations/doc-automator/generate", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["doc_type"] == "ipes"

    def test_doc_automator_generate_batch_default_fallback(self, client):
        """Test batch document generation with default payload fallbacks."""
        res = client.post("/api/operations/doc-automator/generate", json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["doc_type"] == "batch"
        assert "document" in data

    # -------------------------------------------------------------
    # Endpoint 2: POST /api/operations/fat-sat/run-fat
    # -------------------------------------------------------------
    def test_fat_sat_run_fat_list_devices(self, client):
        """Test executing virtual FAT test with list of devices."""
        payload = {
            "ot_code": "OT-7051",
            "device_list": ["SEL-735", "ORION-MX", "MOXA-SW"]
        }
        res = client.post("/api/operations/fat-sat/run-fat", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["result"]["overall_status"] == "APPROVED_100_PERCENT"

    def test_fat_sat_run_fat_string_devices(self, client):
        """Test executing virtual FAT test with comma-separated string device list."""
        payload = {
            "ot_code": "OT-7052",
            "device_list": "SEL-735, ORION-MX"
        }
        res = client.post("/api/operations/fat-sat/run-fat", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_fat_sat_run_fat_empty_payload(self, client):
        """Test virtual FAT execution with empty payload."""
        res = client.post("/api/operations/fat-sat/run-fat", json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    # -------------------------------------------------------------
    # Endpoint 3: POST /api/operations/fat-sat/run-sat
    # -------------------------------------------------------------
    def test_fat_sat_run_sat_success(self, client):
        """Test executing virtual SAT test with substation and engineer."""
        payload = {
            "ot_code": "OT-7053",
            "substation_name": "Subestación CEME 1",
            "engineer_name": "Víctor Vilche"
        }
        res = client.post("/api/operations/fat-sat/run-sat", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["result"]["ot_code"] == "OT-7053"

    def test_fat_sat_run_sat_empty_payload(self, client):
        """Test virtual SAT execution with empty payload defaults."""
        res = client.post("/api/operations/fat-sat/run-sat", json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    # -------------------------------------------------------------
    # Endpoint 4: POST /api/operations/fat-sat/certificate
    # -------------------------------------------------------------
    def test_fat_sat_certificate_success(self, client):
        """Test generating formal FAT/SAT testing certificate."""
        payload = {
            "ot_code": "OT-7054",
            "client_name": "Colbún S.A."
        }
        res = client.post("/api/operations/fat-sat/certificate", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "certificate" in data
        assert data["certificate"]["ot_code"] == "OT-7054"

    def test_fat_sat_certificate_empty_payload(self, client):
        """Test generating certificate with empty payload defaults."""
        res = client.post("/api/operations/fat-sat/certificate", json={})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    # -------------------------------------------------------------
    # Endpoint 5: POST /api/operations/kitting/build-kit
    # -------------------------------------------------------------
    def test_kitting_build_kit_pmu(self, client):
        """Test building PMU panel assembly kit."""
        payload = {
            "ot_code": "OT-7055",
            "kit_type": "PMU_PANEL_KIT_A"
        }
        res = client.post("/api/operations/kitting/build-kit", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "kit" in data
        assert "inventory" in data
        assert "checklist" in data

    def test_kitting_build_kit_scada(self, client):
        """Test building SCADA RTU panel assembly kit."""
        payload = {
            "ot_code": "OT-7056",
            "kit_type": "SCADA_RTU_KIT_B"
        }
        res = client.post("/api/operations/kitting/build-kit", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "kit" in data

    # -------------------------------------------------------------
    # Endpoint 6: POST /api/operations/accreditation/compile
    # -------------------------------------------------------------
    def test_accreditation_compile_package(self, client):
        """Test compiling worker accreditation package."""
        payload = {
            "ot_code": "OT-7057",
            "client": "Transelec",
            "workers": [
                {"rut": "15.420.110-8", "name": "Carlos Mendoza"},
                {"rut": "16.890.344-K", "name": "Roberto Silva"}
            ]
        }
        res = client.post("/api/operations/accreditation/compile", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "package" in data

    def test_accreditation_compile_platform_dossier(self, client):
        """Test compiling platform dossier for specific target platform (e.g. Sicop)."""
        payload = {
            "target_platform": "sicop",
            "worker_rut": "15.420.110-8",
            "worker_name": "Carlos Mendoza",
            "substation": "Subestación Ancud"
        }
        res = client.post("/api/operations/accreditation/compile", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "dossier" in data["package"]
        assert "audit" in data["package"]

    # -------------------------------------------------------------
    # Endpoint 7: POST /api/operations/payment-statement/generate
    # -------------------------------------------------------------
    def test_payment_statement_generate_success(self, client):
        """Test generating payment statement and staging Odoo account.move draft."""
        payload = {
            "ot_code": "OT-7058",
            "client_name": "Enel Generación Chile",
            "milestone_name": "Hito 2: Entrega Equipos y Pruebas FAT",
            "milestone_pct": 50.0,
            "total_contract_uf": 2000.0,
            "uf_value_clp": 38377.09
        }
        res = client.post("/api/operations/payment-statement/generate", json=payload)
        assert res.status_code == 201
        data = res.get_json()
        assert data["success"] is True
        assert "draft_id" in data
        assert "statement" in data
        assert "odoo_payload" in data
        assert data["odoo_payload"]["move_type"] == "out_invoice"

    def test_payment_statement_generate_custom_values(self, client):
        """Test payment statement generation with custom numbers and string coercions."""
        payload = {
            "ot_code": "OT-7059",
            "client_name": "CGE Distribución",
            "milestone_pct": "30.0",
            "total_contract_uf": "1000.0",
            "uf_value_clp": "39000.0"
        }
        res = client.post("/api/operations/payment-statement/generate", json=payload)
        assert res.status_code == 201
        data = res.get_json()
        assert data["success"] is True

    # -------------------------------------------------------------
    # Endpoint 8: GET /api/operations/metrics
    # -------------------------------------------------------------
    def test_ops_metrics_default_params(self, client):
        """Test fetching financial impact metrics with default query parameters."""
        res = client.get("/api/operations/metrics")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "metrics" in data
        assert data["metrics"]["retained_gross_margin_pct"] == 54.8
        assert data["metrics"]["total_contract_uf"] == 3500.0

    def test_ops_metrics_custom_query_params(self, client):
        """Test fetching financial impact metrics with custom query parameters."""
        res = client.get("/api/operations/metrics?num_ots=10&total_contract_uf=5000&uf_value_clp=38000&num_devices=20&num_workers=8&num_substations=5")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["metrics"]["num_ots"] == 10
        assert data["metrics"]["total_contract_uf"] == 5000.0
        assert data["metrics"]["uf_value_clp"] == 38000.0
        assert data["metrics"]["released_hh"] > 0
        assert data["metrics"]["reduced_field_days"] > 0
        assert data["metrics"]["retained_gross_margin_pct"] == 54.8

    def test_ops_metrics_invalid_query_params_fallback(self, client):
        """Test fetching metrics when query params are invalid non-numeric strings."""
        res = client.get("/api/operations/metrics?num_ots=abc&total_contract_uf=xyz")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["metrics"]["num_ots"] == 5  # Fallback
        assert data["metrics"]["total_contract_uf"] == 3500.0  # Fallback
