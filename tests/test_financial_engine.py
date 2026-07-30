"""
Unit tests for FinancialImpactEngine.
Tests gross margin retention (54.8%), released man-hours (HH), reduced field days,
UF/CLP financial summary calculations, and negative/invalid input guards.
"""

import pytest
from src.operations.financial_engine import FinancialImpactEngine


@pytest.fixture
def engine():
    return FinancialImpactEngine()


class TestFinancialImpactEngine:
    """Test suite for FinancialImpactEngine operational and financial calculations."""


    def test_retained_gross_margin_pct(self, engine):
        """Verify the strictly required gross margin retention percentage (54.8%)."""
        assert engine.retained_gross_margin_pct() == 54.8

    def test_calculate_released_man_hours_default_params(self, engine):
        """Test released man-hours calculation with default parameters (1 OT, 1 device, 1 worker)."""
        res = engine.calculate_released_man_hours(num_ots=1)
        assert res["num_ots"] == 1
        assert res["num_devices"] == 1
        assert res["num_workers"] == 1
        assert res["doc_generation_hh"] == 7.0
        assert res["fat_sat_lab_hh"] == 12.0
        assert res["panel_kitting_hh"] == 25.0
        assert res["accreditation_hh"] == 17.5
        assert res["payment_statements_hh"] == 5.0
        # Total: 7 + 12 + 25 + 17.5 + 5 = 66.5 HH
        assert res["total_released_hh"] == 66.5

    def test_calculate_released_man_hours_multiple_ots(self, engine):
        """Test released man-hours with multiple OTs, devices, and workers."""
        res = engine.calculate_released_man_hours(num_ots=10, num_devices=5, num_workers=4)
        assert res["doc_generation_hh"] == 70.0
        assert res["fat_sat_lab_hh"] == 60.0
        assert res["panel_kitting_hh"] == 250.0
        assert res["accreditation_hh"] == 70.0
        assert res["payment_statements_hh"] == 50.0
        # Total: 70 + 60 + 250 + 70 + 50 = 500 HH
        assert res["total_released_hh"] == 500.0

    def test_calculate_released_man_hours_zero_inputs(self, engine):
        """Test released man-hours with zero inputs."""
        res = engine.calculate_released_man_hours(num_ots=0, num_devices=0, num_workers=0)
        assert res["total_released_hh"] == 0.0

    def test_calculate_released_man_hours_negative_inputs_guarded(self, engine):
        """Test negative inputs are guarded and coerced to max(0, val)."""
        res = engine.calculate_released_man_hours(num_ots=-5, num_devices=-10, num_workers=-2)
        assert res["num_ots"] == 0
        assert res["num_devices"] == 0
        assert res["num_workers"] == 0
        assert res["total_released_hh"] == 0.0

    def test_calculate_reduced_field_days_default_params(self, engine):
        """Test reduced field days with default parameters (1 OT, 1 substation)."""
        res = engine.calculate_reduced_field_days(num_ots=1)
        assert res["num_ots"] == 1
        assert res["num_substations"] == 1
        assert res["days_saved_per_ot"] == 3.5
        assert res["total_reduced_field_days"] == 3.5

    def test_calculate_reduced_field_days_multiple_substations(self, engine):
        """Test reduced field days across multiple OTs and substations."""
        res = engine.calculate_reduced_field_days(num_ots=6, num_substations=4)
        assert res["num_ots"] == 6
        assert res["num_substations"] == 4
        assert res["total_reduced_field_days"] == 21.0

    def test_calculate_reduced_field_days_zero_and_negative(self, engine):
        """Test reduced field days with zero and negative inputs."""
        res = engine.calculate_reduced_field_days(num_ots=-3, num_substations=-1)
        assert res["num_ots"] == 0
        assert res["num_substations"] == 0
        assert res["total_reduced_field_days"] == 0.0

    def test_calculate_financial_summary_basic(self, engine):
        """Test financial summary calculation for 1000 UF contract."""
        res = engine.calculate_financial_summary(
            num_ots=2,
            total_contract_uf=1000.0,
            uf_value_clp=38000.0,
            num_devices=4,
            num_workers=2,
            num_substations=2
        )
        assert res["num_ots"] == 2
        assert res["total_contract_uf"] == 1000.0
        assert res["uf_value_clp"] == 38000.0
        assert res["total_contract_clp"] == 38000000.0
        assert res["retained_gross_margin_pct"] == 54.8
        # Retained margin: 38,000,000 * 0.548 = 20,824,000
        assert res["retained_gross_margin_clp"] == 20824000.0

    def test_calculate_financial_summary_engineering_and_field_savings(self, engine):
        """Verify breakdown of engineering HH savings (35k/HH) and field logistics savings (450k/day)."""
        # 1 OT, 1 device, 1 worker => 66.5 total released HH
        # 1 OT => 3.5 reduced field days
        res = engine.calculate_financial_summary(
            num_ots=1,
            total_contract_uf=500.0,
            uf_value_clp=38377.09,
            num_devices=1,
            num_workers=1,
            num_substations=1
        )

        released_hh = res["released_hh"]  # 66.5
        reduced_days = res["reduced_field_days"]  # 3.5

        expected_eng_savings = 66.5 * 35000.0  # 2,327,500
        expected_field_savings = 3.5 * 450000.0  # 1,575,000
        expected_total_savings = expected_eng_savings + expected_field_savings  # 3,902,500

        assert res["total_savings_clp"] == round(expected_total_savings, 2)

    def test_calculate_financial_summary_negative_guards(self, engine):
        """Test negative inputs for UF, UF rate, OTs, workers are all guarded."""
        res = engine.calculate_financial_summary(
            num_ots=-5,
            total_contract_uf=-100.0,
            uf_value_clp=-38000.0,
            num_devices=-1,
            num_workers=-1,
            num_substations=-1
        )
        assert res["total_contract_uf"] == 0.0
        assert res["uf_value_clp"] == 0.0
        assert res["total_contract_clp"] == 0.0
        assert res["retained_gross_margin_clp"] == 0.0
        assert res["total_savings_clp"] == 0.0

    def test_calculate_financial_summary_large_scale(self, engine):
        """Test financial summary with large scale OT portfolio."""
        res = engine.calculate_financial_summary(
            num_ots=50,
            total_contract_uf=25000.0,
            uf_value_clp=38500.0,
            num_devices=200,
            num_workers=50,
            num_substations=15
        )
        assert res["total_contract_clp"] == 962500000.0
        assert res["retained_gross_margin_pct"] == 54.8
        assert res["retained_gross_margin_clp"] == round(962500000.0 * 0.548, 2)
        assert res["released_hh"] > 0
        assert res["reduced_field_days"] == 175.0
        assert res["total_savings_clp"] > 0

    def test_financial_summary_structure(self, engine):
        """Test that returned dict contains all expected keys."""
        res = engine.calculate_financial_summary(num_ots=1, total_contract_uf=100.0)
        expected_keys = {
            "num_ots", "total_contract_uf", "uf_value_clp", "total_contract_clp",
            "retained_gross_margin_pct", "retained_gross_margin_clp", "total_savings_clp",
            "released_hh", "reduced_field_days", "released_man_hours_breakdown", "reduced_field_days_breakdown"
        }
        assert expected_keys.issubset(res.keys())


# =====================================================================
# EXPANDED EDGE CASE & PARAMETERIZED TEST SUITE FOR FINANCIAL ENGINE
# =====================================================================

@pytest.mark.parametrize("uf_rate", [35000.0, 38000.0, 38377.09, 40000.0, 45000.0])
def test_uf_clp_rate_variations(engine, uf_rate):
    res = engine.calculate_financial_summary(
        num_ots=1,
        total_contract_uf=1000.0,
        uf_value_clp=uf_rate
    )
    assert res["total_contract_clp"] == 1000.0 * uf_rate
    assert res["retained_gross_margin_clp"] == round((1000.0 * uf_rate) * 0.548, 2)


@pytest.mark.parametrize("num_ots, num_devices, num_workers, expected_total_hh", [
    (1, 1, 1, 66.5),
    (2, 2, 2, 133.0),
    (5, 10, 4, 375.0),
    (10, 20, 8, 750.0),
])
def test_released_man_hours_parameterized(engine, num_ots, num_devices, num_workers, expected_total_hh):
    res = engine.calculate_released_man_hours(num_ots=num_ots, num_devices=num_devices, num_workers=num_workers)
    assert res["total_released_hh"] == expected_total_hh


@pytest.mark.parametrize("num_ots, num_subs, expected_days", [
    (1, 1, 3.5),
    (2, 2, 7.0),
    (5, 3, 17.5),
    (10, 5, 35.0),
])
def test_reduced_field_days_parameterized(engine, num_ots, num_subs, expected_days):
    res = engine.calculate_reduced_field_days(num_ots=num_ots, num_substations=num_subs)
    assert res["total_reduced_field_days"] == expected_days
