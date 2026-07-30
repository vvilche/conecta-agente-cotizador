"""
Unit tests for GuidedArchitectureEngine and strict decoupling between RTU / Remotas vs PMUs in guided quotations.
Verifies that:
1. When selecting 'RTU' or 'Remota SCADA', only RTU questions and RTU BOM items are generated (NO PMU / PDC questions).
2. When selecting 'PMU', PMU-specific questions and BOM items (SEL-735, IRIG-B, PDC) are generated.
3. BusinessLineClassifier correctly routes 'remotas', 'rtu', 'remota scada' to SCADA_RETROFIT or SITR_PMGD.
"""

import pytest
from src.rag_memory.business_lines import (
    BusinessLineClassifier,
    BusinessLineType,
    GuidedArchitectureEngine,
    STANDARD_BOM_TEMPLATES,
)
from src.swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent


class TestGuidedArchitectureEngineAndRTU:
    """Test suite ensuring RTUs/Remotas quotes are decoupled from PMU quotes."""

    def test_classifier_routing_rtus_and_remotas(self):
        """Verify queries with 'remota', 'rtu', 'scada' route to SCADA_RETROFIT."""
        assert BusinessLineClassifier.classify("Cotización Remotas de Subestación") == BusinessLineType.SCADA_RETROFIT
        assert BusinessLineClassifier.classify("Reemplazo de RTU legacy Novatech Orion") == BusinessLineType.SCADA_RETROFIT
        assert BusinessLineClassifier.classify("Telecontrol SCADA 61850") == BusinessLineType.SCADA_RETROFIT
        assert BusinessLineClassifier.classify("Remota SCADA con Entradas Digitales") == BusinessLineType.SCADA_RETROFIT

    def test_classifier_routing_pmus(self):
        """Verify queries with 'pmu', 'pdc', 'fasorial' route to PMU_PDC."""
        assert BusinessLineClassifier.classify("Medición Fasorial PMU SEL-735") == BusinessLineType.PMU_PDC
        assert BusinessLineClassifier.classify("Concentrador PDC C37.118") == BusinessLineType.PMU_PDC

    def test_guided_architecture_engine_rtu_guidance(self):
        """Verify GuidedArchitectureEngine returns RTU-specific components and excludes PMU questions."""
        guidance = GuidedArchitectureEngine.get_architecture_guidance("scada_retrofit")
        assert guidance["business_line"] == "scada_retrofit"
        assert "Medidor Fasorial PMU" in guidance["architecture"]["excluded_questions"]
        assert "Servidor PDC" in guidance["architecture"]["excluded_questions"]

        # Check questions contain RTU specific terms
        questions_str = " ".join(guidance["guided_questions"]).lower()
        assert "remotas" in questions_str or "rtu" in questions_str
        assert "pmu" not in questions_str
        assert "c37.118" not in questions_str

    def test_guided_architecture_engine_pmu_guidance(self):
        """Verify GuidedArchitectureEngine returns PMU-specific components."""
        guidance = GuidedArchitectureEngine.get_architecture_guidance("pmu_pdc")
        assert guidance["business_line"] == "pmu_pdc"
        questions_str = " ".join(guidance["guided_questions"]).lower()
        assert "pmu" in questions_str or "fasorial" in questions_str

    def test_agent_guide_quotation_rtu_prompt(self):
        """Verify CotizacionInventarioAgent generates RTU BOM items when prompt is about RTUs."""
        agent = CotizacionInventarioAgent()
        draft = agent.guide_quotation("Suministro de Remota RTU Novatech con Tarjetas I/O", {"num_rtus": 2})
        assert draft.target_model == "sale.order"
        lines = draft.proposed_payload["order_line"]
        item_codes = [l["item_code"] for l in lines]
        assert "HW-RTU-NOVATECH" in item_codes
        assert "HW-IO-CARDS" in item_codes
        # PMU specific item should NOT be present
        assert "HW-PMU-SEL735" not in item_codes
        assert "SW-PDC-LIC" not in item_codes


@pytest.mark.parametrize("b_line_str", [
    "pmu_pdc",
    "sitr_pmgd",
    "scada_retrofit",
    "edac_erag",
    "mantenimiento",
])
def test_guided_architecture_engine_all_lines(b_line_str):
    guidance = GuidedArchitectureEngine.get_architecture_guidance(b_line_str)
    assert guidance is not None
    assert "business_line" in guidance
    assert "guided_questions" in guidance
    assert "architecture" in guidance
