"""
Unit tests for CampaignOnePagerEngine.
Verifies One-Pager proposals and targeted market expansion campaigns generation.
"""

import pytest
from src.rag_memory.campaign_onepager_engine import CampaignOnePagerEngine, OnePagerProposal, TargetedCampaign


class TestCampaignOnePagerEngine:
    """Test suite for CampaignOnePagerEngine."""

    def test_get_all_onepagers(self):
        """Verify retrieving all 4 commercial One-Pagers."""
        ops = CampaignOnePagerEngine.get_all_onepagers()
        assert len(ops) == 4
        ids = [op.onepager_id for op in ops]
        assert "ONEPAGER-PDC-UPGRADE" in ids
        assert "ONEPAGER-VIZIMAX-POW" in ids
        assert "ONEPAGER-SLA-SITR" in ids
        assert "ONEPAGER-OT-CYBER" in ids

    def test_get_onepager_by_id(self):
        """Verify retrieving specific One-Pager by ID."""
        op = CampaignOnePagerEngine.get_onepager_by_id("ONEPAGER-VIZIMAX-POW")
        assert op.onepager_id == "ONEPAGER-VIZIMAX-POW"
        assert "Vizimax SynchroTeq Plus" in op.conecta_value_proposition
        assert op.standard_pricing_uf == 1250.0

    def test_build_targeted_campaigns(self):
        """Verify building targeted market expansion campaigns."""
        campaigns = CampaignOnePagerEngine.build_targeted_campaigns()
        assert len(campaigns) == 4
        total_market_potential = sum(c.potential_market_revenue_clp for c in campaigns)
        assert total_market_potential > 2500000000.0  # Over CLP $2.5 Billion market potential


@pytest.mark.parametrize("onepager_id, expected_title_keyword", [
    ("ONEPAGER-PDC-UPGRADE", "PDC"),
    ("ONEPAGER-VIZIMAX-POW", "Vizimax"),
    ("ONEPAGER-SLA-SITR", "SLA"),
    ("ONEPAGER-OT-CYBER", "Ciberseguridad"),
])
def test_get_onepager_individual_lookup(onepager_id, expected_title_keyword):
    op = CampaignOnePagerEngine.get_onepager_by_id(onepager_id)
    assert op is not None
    assert op.onepager_id == onepager_id
    assert expected_title_keyword in op.title or expected_title_keyword in op.conecta_value_proposition
    assert op.standard_pricing_uf > 0.0


def test_get_onepager_by_invalid_id():
    op = CampaignOnePagerEngine.get_onepager_by_id("NON_EXISTENT_ONEPAGER")
    assert op is None


@pytest.mark.parametrize("idx", [0, 1, 2, 3])
def test_targeted_campaigns_structure(idx):
    campaigns = CampaignOnePagerEngine.build_targeted_campaigns()
    c = campaigns[idx]
    assert c.campaign_id is not None
    assert len(c.target_client_types) > 0
    assert c.potential_market_revenue_clp > 0.0
    assert len(c.key_talking_points) > 0
