"""
Unit tests for Belden Hirschmann switches and optional GPS Satellite Clocks.
Verifies user comments:
1. Switches in SCADA/RTU proposals are Belden Hirschmann (primary brand).
2. PMU quotations allow optional GPS clocks depending on whether the client has existing GPS clock infrastructure in the substation.
"""

import pytest
from src.rag_memory.business_lines import STANDARD_BOM_TEMPLATES, BusinessLineType
from src.operations.kitting_engine import KittingEngine
from src.swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent


class TestBeldenSwitchesAndOptionalGPS:
    """Test suite for Belden Hirschmann switches and optional client GPS clocks."""

    def test_belden_hirschmann_switch_in_scada_bom(self):
        """Verify Belden Hirschmann is featured in SCADA_RETROFIT BOM template."""
        scada_template = STANDARD_BOM_TEMPLATES[BusinessLineType.SCADA_RETROFIT]
        items_desc = [item.description for item in scada_template.items]
        assert any("Belden Hirschmann" in d for d in items_desc)

    def test_belden_hirschmann_switch_in_kitting_engine(self):
        """Verify KittingEngine uses Belden Hirschmann for SCADA RTU kit."""
        engine = KittingEngine()
        scada_kit = engine.build_scada_rtu_kit(ot_code="OT-7080")
        skus = [b["sku"] for b in scada_kit["bom_items"]]
        assert "BELDEN-HIRSCHMANN-SW" in skus

    def test_optional_gps_clock_omitted_when_client_has_clock(self):
        """Verify GPS clock is omitted from BOM when client has existing GPS in substation."""
        agent = CotizacionInventarioAgent()
        draft_with_existing_gps = agent.guide_quotation(
            "Cotización Medición Fasorial PMU",
            {"has_existing_gps": True}
        )
        lines = draft_with_existing_gps.proposed_payload["order_line"]
        item_codes = [l["item_code"] for l in lines]
        assert "HW-GPS-CLOCK" not in item_codes

    def test_optional_gps_clock_included_when_client_needs_clock(self):
        """Verify GPS clock is included in BOM when client needs new GPS clock."""
        agent = CotizacionInventarioAgent()
        draft_needs_gps = agent.guide_quotation(
            "Cotización Medición Fasorial PMU",
            {"has_existing_gps": False}
        )
        lines = draft_needs_gps.proposed_payload["order_line"]
        item_codes = [l["item_code"] for l in lines]
        assert "HW-GPS-CLOCK" in item_codes


@pytest.mark.parametrize("prompt_str", [
    "Cotizar switch Belden Hirschmann 8 puertos RJ45",
    "Instalar switches Belden en gabinete SCADA",
    "Requiero 2 switches Hirschmann RS20 DIN-Rail",
    "Proveer switch industrial Belden con redundancia PRP/HSR",
])
def test_belden_hirschmann_prompt_parsing(prompt_str):
    from src.operations.quantity_parser import parse_quantities
    res = parse_quantities(prompt_str)
    assert res.get("num_switches", 0) >= 1.0 or res.get("switches", 0) >= 1.0


@pytest.mark.parametrize("has_gps_flag", [True, False])
def test_gps_clock_inclusion_boolean_flag(has_gps_flag):
    agent = CotizacionInventarioAgent()
    draft = agent.guide_quotation(
        "Medición Fasorial PMU",
        {"has_existing_gps": has_gps_flag}
    )
    lines = draft.proposed_payload["order_line"]
    item_codes = [l["item_code"] for l in lines]

    if has_gps_flag:
        assert "HW-GPS-CLOCK" not in item_codes
    else:
        assert "HW-GPS-CLOCK" in item_codes
