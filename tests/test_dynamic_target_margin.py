"""
Unit tests for dynamic target gross margin configuration across the stack.
Tests FinancialImpactEngine, MultiTabBOMExcelBuilder, Flask API endpoints (/api/operations/metrics, /api/documents/download),
and value boundary clamping (10.0% to 85.0%).
"""

import io
import json
import openpyxl
import pytest
from src.operations.financial_engine import FinancialImpactEngine
from src.operations.bom_excel_builder import MultiTabBOMExcelBuilder
from src.supervisor_ui.app import create_app


@pytest.fixture
def app_client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class TestDynamicTargetMargin:
    """Test suite for configurable target gross margin across financial engine, Excel builder, and API endpoints."""


    def test_financial_engine_custom_margins(self):
        """Test FinancialImpactEngine with dynamic margin percentages."""
        engine_default = FinancialImpactEngine()
        assert engine_default.retained_gross_margin_pct() == 54.8

        engine_custom = FinancialImpactEngine(target_margin_pct=68.5)
        assert engine_custom.retained_gross_margin_pct() == 68.5

        # Test method override
        summary_30 = engine_default.calculate_financial_summary(
            num_ots=1, total_contract_uf=1000.0, uf_value_clp=38000.0, target_margin_pct=30.0
        )
        assert summary_30["retained_gross_margin_pct"] == 30.0
        assert summary_30["retained_gross_margin_clp"] == 38000000.0 * 0.30

        summary_40 = engine_default.calculate_financial_summary(
            num_ots=1, total_contract_uf=1000.0, uf_value_clp=38000.0, target_gross_margin=40.0
        )
        assert summary_40["retained_gross_margin_pct"] == 40.0
        assert summary_40["retained_gross_margin_clp"] == 38000000.0 * 0.40

    def test_margin_clamping_bounds(self):
        """Test margin clamping between 10.0% and 85.0%."""
        engine = FinancialImpactEngine()

        # Below min (5.0%) -> clamped to 10.0%
        assert engine.retained_gross_margin_pct(5.0) == 10.0

        # Above max (95.0%) -> clamped to 85.0%
        assert engine.retained_gross_margin_pct(95.0) == 85.0

        # Decimal format input (0.65 -> 65.0%)
        assert engine.retained_gross_margin_pct(0.65) == 65.0

    def test_excel_bom_builder_dynamic_margin(self):
        """Test MultiTabBOMExcelBuilder with custom target_margin_pct."""
        payload_68 = {
            "partner_id": "Test SLA Client",
            "amount_untaxed": 100000000.0,
            "target_margin_pct": 68.5,
            "order_line": []
        }
        wb_bytes = MultiTabBOMExcelBuilder.build_workbook_bytes(payload_68)
        wb = openpyxl.load_workbook(io.BytesIO(wb_bytes), data_only=False)

        resumen = wb["Resumen"]
        assert resumen["B7"].value == 68.5

        # Target Margin CLP cell formula should reference B7
        margin_clp_formula = str(resumen["B8"].value)
        assert margin_clp_formula.startswith("=") and "B4*(B7/100)" in margin_clp_formula

    def test_api_operations_metrics_dynamic_margin(self, app_client):
        """Test GET and POST /api/operations/metrics with target_margin_pct parameter."""
        # Query parameter GET
        response_get = app_client.get("/api/operations/metrics?num_ots=5&total_contract_uf=1000&target_margin_pct=40.0")
        assert response_get.status_code == 200
        data_get = json.loads(response_get.data)
        assert data_get["metrics"]["retained_gross_margin_pct"] == 40.0

        # JSON body POST
        response_post = app_client.post(
            "/api/operations/metrics",
            data=json.dumps({"num_ots": 5, "total_contract_uf": 1000, "target_gross_margin": 68.5}),
            content_type="application/json"
        )
        assert response_post.status_code == 200
        data_post = json.loads(response_post.data)
        assert data_post["metrics"]["retained_gross_margin_pct"] == 68.5

    def test_api_documents_download_dynamic_margin(self, app_client):
        """Test GET /api/documents/download with target_margin_pct parameter for Ficha Traspaso Excel."""
        response = app_client.get("/api/documents/download?doc_type=ficha_traspaso&target_margin_pct=30.0")
        assert response.status_code == 200
        assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        wb = openpyxl.load_workbook(io.BytesIO(response.data), data_only=False)
        resumen = wb["Resumen"]
        assert resumen["B7"].value == 30.0


# =====================================================================
# EXPANDED EDGE CASE & PARAMETERIZED TEST SUITE FOR TARGET MARGIN
# =====================================================================

@pytest.mark.parametrize("target_margin, expected_clamped", [
    (10.0, 10.0),
    (15.5, 15.5),
    (25.0, 25.0),
    (40.0, 40.0),
    (54.8, 54.8),
    (65.0, 65.0),
    (75.0, 75.0),
    (85.0, 85.0),
    # Out of bounds below min
    (0.0, 10.0),
    (5.0, 10.0),
    (-15.0, 10.0),
    # Out of bounds above max
    (85.1, 85.0),
    (90.0, 85.0),
    (100.0, 85.0),
    (150.0, 85.0),
    # Decimal fraction inputs
    (0.10, 10.0),
    (0.50, 50.0),
    (0.85, 85.0),
])
def test_financial_engine_clamping_sweep(target_margin, expected_clamped):
    engine = FinancialImpactEngine()
    clamped = engine.retained_gross_margin_pct(target_margin)
    assert clamped == expected_clamped


@pytest.mark.parametrize("margin_val", [10.0, 20.0, 35.0, 50.0, 68.5, 85.0])
def test_financial_impact_summary_retained_margin_clp(margin_val):
    engine = FinancialImpactEngine()
    summary = engine.calculate_financial_summary(
        num_ots=1,
        total_contract_uf=1000.0,
        uf_value_clp=38000.0,
        target_margin_pct=margin_val
    )
    expected_clp = 38000000.0 * (margin_val / 100.0)
    assert summary["retained_gross_margin_pct"] == margin_val
    assert summary["retained_gross_margin_clp"] == round(expected_clp, 2)


@pytest.mark.parametrize("query_param_margin, expected_resp_margin", [
    ("10.0", 10.0),
    ("25.0", 25.0),
    ("50.0", 50.0),
    ("85.0", 85.0),
    ("5.0", 10.0),   # Clamped to min
    ("95.0", 85.0),  # Clamped to max
])
def test_api_metrics_query_params_clamping_sweep(app_client, query_param_margin, expected_resp_margin):
    res = app_client.get(f"/api/operations/metrics?num_ots=1&total_contract_uf=500&target_margin_pct={query_param_margin}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["metrics"]["retained_gross_margin_pct"] == expected_resp_margin


@pytest.mark.parametrize("post_body_margin, expected_resp_margin", [
    (10.0, 10.0),
    (30.0, 30.0),
    (60.0, 60.0),
    (85.0, 85.0),
    (2.0, 10.0),   # Clamped
    (99.0, 85.0),  # Clamped
])
def test_api_metrics_post_body_clamping_sweep(app_client, post_body_margin, expected_resp_margin):
    res = app_client.post(
        "/api/operations/metrics",
        data=json.dumps({"num_ots": 1, "total_contract_uf": 500, "target_gross_margin": post_body_margin}),
        content_type="application/json"
    )
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["metrics"]["retained_gross_margin_pct"] == expected_resp_margin
