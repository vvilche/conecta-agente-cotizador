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
