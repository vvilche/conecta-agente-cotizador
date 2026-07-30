"""
Unit & Integration Test Suite for Business Lines Classification & Guided BOM Quotations.
Verifies PMU/PDC, SITR, SCADA, and EDAC business lines, BOM extraction, and CotizacionInventarioAgent guided flow.
"""

import pytest
from rag_memory.business_lines import (
    BusinessLineClassifier,
    BusinessLineType,
    STANDARD_BOM_TEMPLATES,
    BOMTemplate,
    BOMItemCategory,
)
from swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent
from swarm_engine.swarm import AgentSwarm
from rag_memory.few_shot import HistoricalMemory


class TestBusinessLineClassification:
    """Tests for classifying prompts and folder names into business lines."""

    def test_classify_pmu_pdc(self):
        assert BusinessLineClassifier.classify("Licitación Suministro PMU y PDC ENLASA") == BusinessLineType.PMU_PDC
        assert BusinessLineClassifier.classify("Implementación 4 PMU Centella") == BusinessLineType.PMU_PDC
        assert BusinessLineClassifier.classify("Generame una cotizacion para PMUS") == BusinessLineType.PMU_PDC

    def test_classify_sitr_pmgd(self):
        assert BusinessLineClassifier.classify("Habilitación Telemetría SITR PMGD Solar") == BusinessLineType.SITR_PMGD
        assert BusinessLineClassifier.classify("Visita por levantamiento SITR AT-SITR-1") == BusinessLineType.SITR_PMGD

    def test_classify_scada_retrofit(self):
        assert BusinessLineClassifier.classify("Codelco Gabriela Mistral - SCADA") == BusinessLineType.SCADA_RETROFIT
        assert BusinessLineClassifier.classify("Retrofit de RTU Sicam SE Polpaico IEC 61850") == BusinessLineType.SCADA_RETROFIT

    def test_classify_edac_erag(self):
        assert BusinessLineClassifier.classify("Estudio Coordinación Protecciones EDAC ERAG DIgSILENT") == BusinessLineType.EDAC_ERAG_STUDIES

    def test_classify_maintenance(self):
        assert BusinessLineClassifier.classify("Mantenimiento de PDCE 2026 e Inyección Relés") == BusinessLineType.MAINTENANCE_LICENSES


class TestBOMTemplates:
    """Tests for standard BOM templates and items structure."""

    def test_pmu_pdc_bom_template(self):
        tmpl = STANDARD_BOM_TEMPLATES[BusinessLineType.PMU_PDC]
        assert tmpl.business_line == BusinessLineType.PMU_PDC
        assert len(tmpl.items) >= 5
        assert len(tmpl.guided_questions) >= 3

        # Check item categories
        categories = {item.category for item in tmpl.items}
        assert BOMItemCategory.HARDWARE in categories
        assert BOMItemCategory.SOFTWARE_LICENSE in categories
        assert BOMItemCategory.ENGINEERING_HOURS in categories
        assert BOMItemCategory.REGULATORY_CERTIFICATION in categories


class TestGuidedQuotationAgent:
    """Tests for guided quotation generation by CotizacionInventarioAgent."""

    def test_guided_quote_pmus_request(self):
        agent = CotizacionInventarioAgent()
        draft = agent.process_event("guided_quote", {
            "prompt": "Generame una cotización para PMUS",
            "client": "ENEL Generación Chile S.A.",
            "num_pmus": 2
        })

        assert draft.agent_name == "cotizacion_inventario"
        assert draft.target_model == "sale.order"
        assert draft.status == "pending_vobo"
        assert draft.metadata["business_line"] == "pmu_pdc"
        assert draft.metadata["line_items_count"] >= 5
        assert len(draft.metadata["guided_questions"]) >= 3

        payload = draft.proposed_payload
        assert payload["partner_id"] == "ENEL Generación Chile S.A."
        assert payload["amount_untaxed"] > 0
        assert abs(payload["amount_tax"] - (payload["amount_untaxed"] * 0.19)) < 1.0
        assert payload["amount_total"] == payload["amount_untaxed"] + payload["amount_tax"]
        assert len(payload["order_line"]) >= 5

    def test_guided_quote_sitr_pmgd_request(self):
        agent = CotizacionInventarioAgent()
        draft = agent.process_event("guided_quote", {
            "prompt": "Necesito cotización SITR para PMGD Solar 9MW",
            "client": "Grenergy Chile SpA"
        })

        assert draft.target_model == "sale.order"
        assert draft.metadata["business_line"] == "sitr_pmgd"
        assert draft.proposed_payload["partner_id"] == "Grenergy Chile SpA"

    def test_swarm_integration_process_task_pmus(self):
        swarm = AgentSwarm()
        draft = swarm.process_task("cotizacion_inventario", {
            "prompt": "Generame una cotización para PMUS",
            "client": "Transelec S.A."
        })

        assert draft.agent_name == "cotizacion_inventario"
        assert draft.status == "pending_vobo"
        assert draft.metadata["business_line"] == "pmu_pdc"
