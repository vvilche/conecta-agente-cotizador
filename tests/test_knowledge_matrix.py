"""
Unit tests for TechnicalKnowledgeMatrix and KnowledgeMatrix.
Tests normative rules, CEN protocols, standard BOM lookups, offer records, and SQLite storage.
"""

import os
import tempfile
import pytest
from src.rag_memory.knowledge_matrix import (
    TechnicalKnowledgeMatrix,
    KnowledgeMatrix,
    OfferRecord,
    OfferStatus,
    PricingItem,
    TechnicalSpec,
    CommercialTerms,
)


class TestTechnicalKnowledgeMatrix:
    """Test suite for TechnicalKnowledgeMatrix normative, CEN, and BOM lookups."""

    def test_get_normative_rule_by_id_valid(self):
        """Test retrieving normative rules by valid ID."""
        r1 = TechnicalKnowledgeMatrix.get_normative_rule("REG-NTSYCS-01")
        assert r1 is not None
        assert r1["rule_id"] == "REG-NTSYCS-01"
        assert r1["standard"] == "NTSyCS Cap. 4"
        assert r1["severity"] == "CRITICAL"

        r2 = TechnicalKnowledgeMatrix.get_normative_rule("REG-AT-SITR-1")
        assert r2 is not None
        assert r2["rule_id"] == "REG-AT-SITR-1"

    def test_get_normative_rule_by_id_case_insensitive(self):
        """Test retrieving normative rules with case-insensitive ID."""
        r = TechnicalKnowledgeMatrix.get_normative_rule("reg-sec-05-2021")
        assert r is not None
        assert r["rule_id"] == "REG-SEC-05-2021"

    def test_get_normative_rule_nonexistent(self):
        """Test retrieving nonexistent normative rule returns None."""
        assert TechnicalKnowledgeMatrix.get_normative_rule("INVALID-RULE-99") is None

    def test_search_normative_rules_by_query(self):
        """Test searching normative rules by keyword query."""
        results = TechnicalKnowledgeMatrix.search_normative_rules(query="sincronización")
        assert len(results) >= 1
        assert results[0]["rule_id"] == "REG-NTSYCS-01"

    def test_search_normative_rules_by_standard(self):
        """Test searching normative rules by standard name."""
        results = TechnicalKnowledgeMatrix.search_normative_rules(standard="SEC")
        assert len(results) >= 1
        assert results[0]["rule_id"] == "REG-SEC-05-2021"

    def test_get_cen_protocol_by_id_valid(self):
        """Test retrieving CEN protocols by valid ID."""
        p1 = TechnicalKnowledgeMatrix.get_cen_protocol("CEN-PROT-FAT-01")
        assert p1 is not None
        assert p1["category"] == "FAT_LAB"
        assert p1["execution_mode"] == "VIRTUAL_HIL_LAB"

        p2 = TechnicalKnowledgeMatrix.get_cen_protocol("CEN-PROT-SAT-02")
        assert p2 is not None
        assert p2["category"] == "SAT_FIELD"

    def test_get_cen_protocol_nonexistent(self):
        """Test retrieving nonexistent CEN protocol returns None."""
        assert TechnicalKnowledgeMatrix.get_cen_protocol("INVALID-PROT-99") is None

    def test_search_cen_protocols_by_category(self):
        """Test searching CEN protocols by category."""
        fat_prots = TechnicalKnowledgeMatrix.search_cen_protocols(category="FAT_LAB")
        assert len(fat_prots) == 1
        assert fat_prots[0]["protocol_id"] == "CEN-PROT-FAT-01"

        all_prots = TechnicalKnowledgeMatrix.search_cen_protocols()
        assert len(all_prots) >= 4

    def test_get_standard_bom_pmu_pdc(self):
        """Test standard BOM catalog lookup for 'pmu_pdc'."""
        bom = TechnicalKnowledgeMatrix.get_standard_bom("pmu_pdc")
        assert isinstance(bom, list)
        assert len(bom) >= 5
        codes = [item["item_code"] for item in bom]
        assert "HW-VIZIMAX-PMU" in codes
        assert "HW-GPS-CLK" in codes

    def test_get_standard_bom_sitr_telemetry(self):
        """Test standard BOM catalog lookup for 'sitr_telemetry'."""
        bom = TechnicalKnowledgeMatrix.get_standard_bom("sitr_telemetry")
        assert len(bom) >= 3
        codes = [item["item_code"] for item in bom]
        assert "HW-RTU-SITR" in codes

    def test_get_standard_bom_scada_retrofit(self):
        """Test standard BOM catalog lookup for 'scada_retrofit'."""
        bom = TechnicalKnowledgeMatrix.get_standard_bom("scada_retrofit")
        assert len(bom) >= 3
        codes = [item["item_code"] for item in bom]
        assert "HW-SCADA-PANEL" in codes or "HW-RTU-NOVATECH" in codes

    def test_get_standard_bom_fallback(self):
        """Test standard BOM catalog lookup fallback for unknown line."""
        bom = TechnicalKnowledgeMatrix.get_standard_bom("unknown_line")
        assert isinstance(bom, list)
        assert len(bom) >= 5  # Falls back to pmu_pdc

    def test_lookup_bom_item_valid(self):
        """Test looking up a specific BOM item across catalogs."""
        item = TechnicalKnowledgeMatrix.lookup_bom_item("HW-VIZIMAX-PMU")
        assert item is not None
        assert item["name"] == "Medidor Vizimax SynchroTeq Plus PMU (IEEE C37.118)"
        assert item["unit_price_clp"] == 9500000.0

    def test_lookup_bom_item_nonexistent(self):
        """Test looking up nonexistent BOM item returns None."""
        assert TechnicalKnowledgeMatrix.lookup_bom_item("NONEXISTENT-CODE") is None

    def test_export_matrix_summary(self):
        """Test high-level summary of Technical Knowledge Matrix."""
        summary = TechnicalKnowledgeMatrix.export_matrix_summary()
        assert summary["total_normative_rules"] >= 4
        assert summary["total_cen_protocols"] >= 4
        assert "pmu_pdc" in summary["business_lines_covered"]
        assert summary["total_bom_items"] >= 10


class TestKnowledgeMatrixStorage:
    """Test suite for KnowledgeMatrix SQLite persistence and OfferRecord validation."""

    @pytest.fixture
    def temp_db(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        yield tmp.name
        if os.path.exists(tmp.name):
            os.remove(tmp.name)

    def test_offer_record_to_summary_dict(self):
        """Test OfferRecord serialization to summary dict."""
        record = OfferRecord(
            offer_id="OFF-2026-001",
            title="Suministro e Integración PMU CEME 1",
            client_name="Enel Generación",
            date="2026-01-15",
            status=OfferStatus.WON,
            domain="pmu_pdc",
            total_amount=45000000.0
        )
        summary = record.to_summary_dict()
        assert summary["offer_id"] == "OFF-2026-001"
        assert summary["client_name"] == "Enel Generación"
        assert summary["status"] == "won"
        assert summary["total_amount"] == 45000000.0

    def test_knowledge_matrix_sqlite_add_and_get(self, temp_db):
        """Test adding and retrieving OfferRecord from SQLite store."""
        km = KnowledgeMatrix(db_path=temp_db)
        record = OfferRecord(
            offer_id="OFF-2026-002",
            title="Retrofit SCADA Subestación Ancud",
            client_name="Transelec",
            date="2026-02-10",
            status=OfferStatus.WON,
            domain="scada_retrofit",
            total_amount=82000000.0,
            pricing_items=[
                PricingItem(item_code="HW-SCADA", description="Gabinete SCADA", unit_price=82000000.0, total_price=82000000.0)
            ]
        )
        km.add_record(record)
        assert km.count() == 1

        retrieved = km.get_record("OFF-2026-002")
        assert retrieved is not None
        assert retrieved.offer_id == "OFF-2026-002"
        assert retrieved.client_name == "Transelec"
        assert retrieved.status == OfferStatus.WON
        assert len(retrieved.pricing_items) == 1

    def test_knowledge_matrix_search_filters(self, temp_db):
        """Test searching records in KnowledgeMatrix with domain, client, status filters."""
        km = KnowledgeMatrix(db_path=temp_db)
        r1 = OfferRecord(offer_id="O1", title="Proposal 1", client_name="Colbún", date="2026-01-01", status=OfferStatus.WON, domain="pmu_pdc")
        r2 = OfferRecord(offer_id="O2", title="Proposal 2", client_name="CGE", date="2026-01-02", status=OfferStatus.LOST, domain="sitr_telemetry")
        km.add_record(r1)
        km.add_record(r2)

        won_records = km.search(status="won")
        assert len(won_records) == 1
        assert won_records[0].offer_id == "O1"

        colbun_records = km.search(client_name="Colbún")
        assert len(colbun_records) == 1
        assert colbun_records[0].offer_id == "O1"

        pmu_records = km.search(domain="pmu_pdc")
        assert len(pmu_records) == 1
        assert pmu_records[0].offer_id == "O1"

    def test_knowledge_matrix_export_to_json(self, temp_db):
        """Test exporting KnowledgeMatrix store to JSON file."""
        km = KnowledgeMatrix(db_path=temp_db)
        km.add_record(OfferRecord(offer_id="O100", title="Test JSON Export", client_name="AES Andes", date="2026-03-01"))

        json_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        try:
            res_path = km.export_to_json(json_file)
            assert os.path.exists(res_path)
            assert os.path.getsize(res_path) > 0
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)
