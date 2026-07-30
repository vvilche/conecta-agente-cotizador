"""
Unit tests for OperationalIntelligenceEngine, RegulatoryComplianceAuditor, WinRateEstimator, and CrossSellEngine.
Tests predictive access delays, bottleneck detection, operational risk scoring,
preventive regulatory audits, pricing elasticity win rates, and SLA cross-selling discovery.
"""

import pytest
from src.rag_memory.advanced_intelligence import (
    OperationalIntelligenceEngine,
    RegulatoryComplianceAuditor,
    WinRateEstimator,
    CrossSellEngine,
    RegulatoryAuditReport,
    WinRatePrediction,
)


class TestOperationalIntelligenceEngine:
    """Test suite for OperationalIntelligenceEngine predictive capability."""

    def test_predict_access_delay_default_platform(self):
        """Test predictive access delay for default platform ('direct') with 1 worker."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Normal",
            platform="direct",
            num_workers=1
        )
        assert res["substation_name"] == "Subestación Normal"
        assert res["platform"] == "direct"
        assert res["num_workers"] == 1
        assert res["estimated_delay_days"] == 1.0
        assert res["recommended_lead_time_days"] == 2
        assert res["platform_risk"] == "LOW"

    def test_predict_access_delay_sicop_platform(self):
        """Test predictive access delay for 'sicop' platform (base delay 5.0 days)."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Lampa",
            platform="sicop",
            num_workers=2
        )
        assert res["platform"] == "sicop"
        assert res["estimated_delay_days"] == 5.0
        assert res["platform_risk"] == "MEDIUM"
        assert any("Sicop" in b for b in res["bottleneck_factors"])

    def test_predict_access_delay_pronexo_platform(self):
        """Test predictive access delay for 'pronexo' platform (base delay 4.0 days)."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Nogales",
            platform="pronexo",
            num_workers=2
        )
        assert res["platform"] == "pronexo"
        assert res["estimated_delay_days"] == 4.0
        assert res["platform_risk"] == "MEDIUM"

    def test_predict_access_delay_rys_platform(self):
        """Test predictive access delay for 'rys' platform (base delay 3.0 days)."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Maipú",
            platform="rys",
            num_workers=2
        )
        assert res["platform"] == "rys"
        assert res["estimated_delay_days"] == 3.0
        assert res["platform_risk"] == "LOW"

    def test_predict_access_delay_high_complexity_substation(self):
        """Test high complexity substation penalty (+2.0 days penalty)."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Ancud 220kV",
            platform="pronexo",
            num_workers=2
        )
        assert res["is_high_complexity"] is True
        # Base 4.0 + complexity 2.0 = 6.0
        assert res["estimated_delay_days"] == 6.0
        assert res["platform_risk"] == "MEDIUM"
        assert any("alta complejidad" in b for b in res["bottleneck_factors"])

    def test_predict_access_delay_worker_scaling_penalty(self):
        """Test worker scaling penalty (+0.5 days per worker beyond 2)."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Cardones",
            platform="sicop",
            num_workers=6
        )
        # Base 5.0 + worker penalty (6 - 2)*0.5 = 2.0 + complexity (Cardones) 2.0 = 9.0
        assert res["num_workers"] == 6
        assert res["estimated_delay_days"] == 9.0
        assert res["platform_risk"] == "HIGH"
        assert any("elevada" in b for b in res["bottleneck_factors"])

    def test_predict_access_delay_negative_worker_guard(self):
        """Test negative worker count input is coerced to max(1, n)."""
        res = OperationalIntelligenceEngine.predict_access_delay(
            substation_name="Subestación Test",
            platform="direct",
            num_workers=-5
        )
        assert res["num_workers"] == 1
        assert res["estimated_delay_days"] == 1.0

    def test_detect_bottlenecks_empty_tasks(self):
        """Test bottleneck detection with empty tasks list."""
        res = OperationalIntelligenceEngine.detect_bottlenecks([])
        assert res["total_tasks_analyzed"] == 0
        assert res["bottlenecks_detected"] == []
        assert res["has_critical_bottleneck"] is False

    def test_detect_bottlenecks_accreditation_delay(self):
        """Test detection of accreditation bottlenecks."""
        tasks = [
            {"task_id": "T1", "name": "Compilar dossier acreditacion Sicop", "status": "pending"}
        ]
        res = OperationalIntelligenceEngine.detect_bottlenecks(tasks)
        assert res["total_tasks_analyzed"] == 1
        assert len(res["bottlenecks_detected"]) == 1
        assert res["bottlenecks_detected"][0]["bottleneck_type"] == "ACCREDITATION_DELAY"

    def test_detect_bottlenecks_procurement_lead_time(self):
        """Test detection of hardware procurement lead time bottlenecks."""
        tasks = [
            {"task_id": "T2", "name": "Importacion Gabinete PMU Vizimax SynchroTeq Plus", "lead_time_days": 25, "status": "pending"}
        ]
        res = OperationalIntelligenceEngine.detect_bottlenecks(tasks)
        assert res["total_tasks_analyzed"] == 1
        assert len(res["bottlenecks_detected"]) == 1
        assert res["bottlenecks_detected"][0]["bottleneck_type"] == "PROCUREMENT_LEAD_TIME"

    def test_detect_bottlenecks_cen_fat_sat_approval(self):
        """Test detection of CEN FAT/SAT protocol bottlenecks."""
        tasks = [
            {"task_id": "T3", "name": "Protocolo Ensayos CEN AT-SITR-1", "fat_sat_passed": False, "status": "pending"}
        ]
        res = OperationalIntelligenceEngine.detect_bottlenecks(tasks)
        assert res["total_tasks_analyzed"] == 1
        assert len(res["bottlenecks_detected"]) == 1
        assert res["bottlenecks_detected"][0]["bottleneck_type"] == "CEN_FAT_SAT_APPROVAL"

    def test_detect_bottlenecks_substation_outage_window(self):
        """Test detection of critical substation outage window bottlenecks."""
        tasks = [
            {"task_id": "T4", "name": "Ventana de desconexión autorizada por CEN", "status": "pending"}
        ]
        res = OperationalIntelligenceEngine.detect_bottlenecks(tasks)
        assert res["total_tasks_analyzed"] == 1
        assert res["has_critical_bottleneck"] is True
        assert res["critical_count"] == 1
        assert res["bottlenecks_detected"][0]["severity"] == "CRITICAL"

    def test_calculate_operational_risk_score_basic(self):
        """Test basic operational risk scoring."""
        ot_data = {
            "num_workers": 2,
            "num_substations": 1,
            "has_fat_sat_lab": True,
            "accreditation_platform": "direct",
            "device_count": 2,
            "has_cen_protocols": True
        }
        res = OperationalIntelligenceEngine.calculate_operational_risk_score(ot_data)
        assert "total_risk_score" in res
        assert "risk_level" in res
        assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert "breakdown" in res

    def test_calculate_operational_risk_score_fat_sat_lab_reduction(self):
        """Test risk score reduction when FAT/SAT lab testing is enabled."""
        ot_no_lab = {
            "num_workers": 4,
            "num_substations": 2,
            "has_fat_sat_lab": False,
            "accreditation_platform": "sicop",
            "device_count": 5,
            "has_cen_protocols": False
        }
        ot_with_lab = dict(ot_no_lab, has_fat_sat_lab=True)

        res_no_lab = OperationalIntelligenceEngine.calculate_operational_risk_score(ot_no_lab)
        res_with_lab = OperationalIntelligenceEngine.calculate_operational_risk_score(ot_with_lab)

        assert res_with_lab["total_risk_score"] < res_no_lab["total_risk_score"]

    def test_calculate_operational_risk_score_negative_guards(self):
        """Test negative inputs for workers, substations, devices are guarded."""
        ot_data = {
            "num_workers": -10,
            "num_substations": -5,
            "device_count": -2
        }
        res = OperationalIntelligenceEngine.calculate_operational_risk_score(ot_data)
        assert res["total_risk_score"] >= 0.0
        assert res["total_risk_score"] <= 100.0


class TestRegulatoryComplianceAuditor:
    """Test suite for RegulatoryComplianceAuditor."""

    def test_audit_proposal_pmu_without_gps(self):
        """Test compliance audit flags missing GPS when PMU is present."""
        lines = [
            {"item_code": "HW-VIZIMAX-PMU", "name": "Gabinete PMU Vizimax SynchroTeq Plus"}
        ]
        res = RegulatoryComplianceAuditor.audit_proposal(lines, "pmu_pdc")
        assert res.status == "CRITICAL_GAPS"
        assert res.compliance_score < 1.0
        assert any(w.rule_id == "REG-NTSYCS-01" for w in res.warnings)

    def test_audit_proposal_pmu_without_pdc(self):
        """Test compliance audit flags missing PDC when PMU is present."""
        lines = [
            {"item_code": "HW-VIZIMAX-PMU", "name": "Gabinete PMU Vizimax SynchroTeq Plus"},
            {"item_code": "HW-GPS-CLK", "name": "Reloj GPS IRIG-B"}
        ]
        res = RegulatoryComplianceAuditor.audit_proposal(lines, "pmu_pdc")
        assert any(w.rule_id == "REG-DTR-CEN-02" for w in res.warnings)

    def test_audit_proposal_compliant(self):
        """Test compliance audit returns COMPLIANT when all regulatory components exist."""
        lines = [
            {"item_code": "HW-VIZIMAX-PMU", "name": "Gabinete PMU Vizimax SynchroTeq Plus"},
            {"item_code": "HW-GPS-CLK", "name": "Reloj GPS IRIG-B"},
            {"item_code": "HW-PDC-SRV", "name": "Servidor PDC Orion MX"},
            {"item_code": "SRV-CEN-TEST", "name": "Ensayos Protocolo CEN"}
        ]
        res = RegulatoryComplianceAuditor.audit_proposal(lines, "pmu_pdc")
        assert res.status == "COMPLIANT"
        assert res.compliance_score == 1.0
        assert len(res.warnings) == 0


class TestWinRateEstimator:
    """Test suite for Commercial Win-Rate Estimator."""

    def test_predict_win_rate_colbun_quality_focused(self):
        """Test win rate estimation for Colbún (quality focused profile)."""
        res = WinRateEstimator.predict_win_rate("Colbún S.A.", 45.0)
        assert res.client_sensitivity == "QUALITY_FOCUSED"
        assert res.recommended_margin_pct == 45.0
        assert res.estimated_win_rate_pct > 80.0

    def test_predict_win_rate_cge_price_sensitive(self):
        """Test win rate estimation for CGE (price sensitive profile)."""
        res = WinRateEstimator.predict_win_rate("CGE Distribución", 40.0)
        assert res.client_sensitivity == "HIGH_PRICE_SENSITIVE"
        assert res.recommended_margin_pct == 25.0
        # High margin for price sensitive client reduces win rate significantly
        assert res.estimated_win_rate_pct < 80.0

    def test_predict_win_rate_unknown_client_fallback(self):
        """Test win rate estimation fallback for unknown client."""
        res = WinRateEstimator.predict_win_rate("Empresa Fantasma SpA", 30.0)
        assert res.client_sensitivity == "BALANCED"
        assert res.recommended_margin_pct == 28.0


class TestCrossSellEngine:
    """Test suite for SLA & Recurring Revenue Cross-Selling Engine."""

    def test_find_opportunities_pmu_pdc(self):
        """Test cross-sell opportunity discovery for PMU/PDC business line."""
        opps = CrossSellEngine.find_opportunities("Transelec", "pmu_pdc", 50000000.0)
        assert len(opps) >= 2
        assert any("SLA" in o.suggested_service for o in opps)
        assert any("Ciberseguridad OT" in o.suggested_service or "Control de Onda" in o.suggested_service for o in opps)

    def test_find_opportunities_unrelated_business_line(self):
        """Test cross-sell opportunity discovery for unmapped line still offers worker accreditation management."""
        opps = CrossSellEngine.find_opportunities("Enel", "consultoria_general", 10000000.0)
        assert len(opps) >= 1
        assert any("Acreditación" in o.suggested_service for o in opps)
