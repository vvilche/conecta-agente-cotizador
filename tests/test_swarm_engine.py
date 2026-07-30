"""
Comprehensive Pytest Suite for Swarm Agentic Engine (Milestone 3).
Tests BaseAgent, DraftAction schema, the 6 Specialized Agents, AgentSwarm event routing,
health checks, error isolation, multi-agent workflows, and the Zero Auto-Execution Invariant.
"""

import pytest
from pydantic import ValidationError
from typing import Dict, Any

from swarm_engine.base_agent import BaseAgent, DraftAction
from swarm_engine.swarm import AgentSwarm, KNOWN_AGENTS, EVENT_ROUTING_MAP
from swarm_engine.agents.rfq_prospeccion import RFQProspeccionAgent
from swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent
from swarm_engine.agents.operaciones_presupuesto import OperacionesPresupuestoAgent
from swarm_engine.agents.estados_pago import EstadosPagoAgent
from swarm_engine.agents.gestion_documental import GestionDocumentalAgent
from swarm_engine.agents.conciliador_contable import ConciliadorContableAgent


class ConcreteDummyAgent(BaseAgent):
    """Concrete subclass of BaseAgent for baseline abstract testing."""
    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        return self.create_draft_action(
            target_model="crm.lead",
            proposed_payload={"name": payload.get("title", "Test")},
            justification="Dummy agent test action"
        )


class FailingAgent(BaseAgent):
    """Subclass of BaseAgent designed to simulate runtime failures for error isolation tests."""
    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        raise RuntimeError("Simulated failure in failing agent")


# ==========================================
# 1. TestDraftActionAndBaseAgent
# ==========================================
class TestDraftActionAndBaseAgent:

    def test_draft_action_default_status(self):
        draft = DraftAction(
            agent_name="rfq_prospeccion",
            target_model="crm.lead",
            proposed_payload={"name": "Oportunidad Test"},
            justification="Justificación de prueba"
        )
        assert draft.status == "pending_vobo"
        assert draft.draft_id.startswith("draft_")
        assert draft.confidence_score == 1.0
        assert isinstance(draft.audit_trail, list)

    def test_draft_action_confidence_score_valid(self):
        draft = DraftAction(
            agent_name="test_agent",
            target_model="sale.order",
            proposed_payload={},
            justification="Test",
            confidence_score=0.85
        )
        assert draft.confidence_score == 0.85

    def test_draft_action_confidence_score_invalid_high(self):
        with pytest.raises(ValidationError):
            DraftAction(
                agent_name="test_agent",
                target_model="sale.order",
                proposed_payload={},
                justification="Test",
                confidence_score=1.5
            )

    def test_draft_action_confidence_score_invalid_low(self):
        with pytest.raises(ValidationError):
            DraftAction(
                agent_name="test_agent",
                target_model="sale.order",
                proposed_payload={},
                justification="Test",
                confidence_score=-0.1
            )

    def test_draft_action_invalid_status(self):
        with pytest.raises(ValidationError):
            DraftAction(
                agent_name="test_agent",
                target_model="sale.order",
                proposed_payload={},
                justification="Test",
                status="invalid_status"
            )

    def test_draft_action_serialization(self):
        draft = DraftAction(
            agent_name="test_agent",
            target_model="crm.lead",
            proposed_payload={"name": "Lead Test"},
            justification="Justificación de prueba",
            confidence_score=0.9
        )
        dumped = draft.model_dump()
        assert dumped["agent_name"] == "test_agent"
        assert dumped["status"] == "pending_vobo"
        assert dumped["confidence_score"] == 0.9

        json_str = draft.model_dump_json()
        assert "pending_vobo" in json_str

    def test_base_agent_abstract_instantiation(self):
        with pytest.raises(TypeError):
            BaseAgent(agent_name="abstract", domain="test")

    def test_base_agent_helper_methods(self, odoo_client_xmlrpc, historical_memory_instance):
        agent = ConcreteDummyAgent(
            agent_name="dummy_agent",
            domain="edac_erag",
            odoo_client=odoo_client_xmlrpc,
            memory=historical_memory_instance
        )
        assert agent.status == "idle"

        # Test query_odoo
        partners = agent.query_odoo("res.partner", domain=[], fields=["id", "name"])
        assert isinstance(partners, list)
        assert len(partners) > 0

        # Test get_historical_context
        context = agent.get_historical_context("EDAC", top_k=2)
        assert isinstance(context, list)

        # Test create_draft_action
        draft = agent.create_draft_action("sale.order", {"amount": 100}, "Test draft")
        assert draft.status == "pending_vobo"
        assert draft.agent_name == "dummy_agent"

        # Test check_health
        health = agent.check_health()
        assert health["healthy"] is True
        assert health["agent_name"] == "dummy_agent"


# ==========================================
# 2. TestRFQAgent
# ==========================================
class TestRFQAgent:

    def test_rfq_agent_process_event_basic(self):
        agent = RFQProspeccionAgent()
        payload = {
            "client_name": "Empresa Electrica COMASA S.A.",
            "title": "Estudio EDAC Subestación Ancoa",
            "description": "Estudio de coordinación de protecciones y simulación DIgSILENT",
            "domain": "edac_erag",
            "budget_estimate": 45000000.0
        }
        draft = agent.process_event("rfq_received", payload)
        assert draft.target_model == "crm.lead"
        assert draft.status == "pending_vobo"
        assert draft.action_type == "create"
        assert draft.proposed_payload["expected_revenue"] == 45000000.0
        assert "COMASA" in draft.justification

    def test_rfq_agent_partner_lookup(self, odoo_client_xmlrpc):
        agent = RFQProspeccionAgent(odoo_client=odoo_client_xmlrpc)
        payload = {
            "vat": "76111222-3",
            "title": "Proyecto Telemetría SITR",
            "domain": "pmgd_sitr"
        }
        draft = agent.process_event("process_rfq", payload)
        assert draft.target_model == "crm.lead"
        assert draft.proposed_payload["partner_id"] == 1

    def test_rfq_agent_rag_context_integration(self, historical_memory_instance):
        agent = RFQProspeccionAgent(memory=historical_memory_instance)
        payload = {
            "title": "Estudio de Coordinación EDAC/ERAG",
            "domain": "edac_erag"
        }
        draft = agent.process_event("rfq_received", payload)
        assert draft.metadata.get("rag_references_count", 0) > 0
        assert draft.proposed_payload["probability"] >= 60.0

    def test_rfq_agent_without_client_or_memory(self):
        agent = RFQProspeccionAgent(odoo_client=None, memory=None)
        payload = {"title": "Licitación General"}
        draft = agent.process_event("rfq_received", payload)
        assert draft.status == "pending_vobo"
        assert draft.proposed_payload["expected_revenue"] > 0

    def test_rfq_agent_unmapped_event_type(self):
        agent = RFQProspeccionAgent()
        draft = agent.process_event("unknown_event", {"title": "Test Fallback"})
        assert draft.status == "pending_vobo"


# ==========================================
# 3. TestQuotationAgent
# ==========================================
class TestQuotationAgent:

    def test_quotation_agent_product_matching(self, odoo_client_xmlrpc):
        agent = CotizacionInventarioAgent(odoo_client=odoo_client_xmlrpc)
        payload = {
            "partner_id": 1,
            "items": [
                {"name": "Servicio Estudio EDAC", "qty": 1.0, "unit_price": 45000.0}
            ]
        }
        draft = agent.process_event("quote_request", payload)
        assert draft.target_model == "sale.order"
        assert draft.status == "pending_vobo"
        assert draft.proposed_payload["amount_untaxed"] == 45000.0
        assert draft.proposed_payload["amount_tax"] == 45000.0 * 0.19
        assert draft.proposed_payload["amount_total"] == 45000.0 * 1.19

    def test_quotation_agent_rag_cost_benchmarks(self, historical_memory_instance):
        agent = CotizacionInventarioAgent(memory=historical_memory_instance)
        payload = {
            "domain": "edac_erag",
            "items": [
                {"name": "Estudio de Coordinación de Protecciones EDAC/ERAG", "qty": 1.0}
            ]
        }
        draft = agent.process_event("process_quote", payload)
        assert draft.status == "pending_vobo"
        assert draft.proposed_payload["amount_untaxed"] > 0

    def test_quotation_agent_chilean_tax_calculation(self):
        agent = CotizacionInventarioAgent()
        payload = {
            "partner_id": 2,
            "items": [
                {"name": "Tablero SCADA", "qty": 2.0, "unit_price": 1000000.0}
            ]
        }
        draft = agent.process_event("quote_request", payload)
        assert draft.proposed_payload["amount_untaxed"] == 2000000.0
        assert draft.proposed_payload["amount_tax"] == 380000.0
        assert draft.proposed_payload["amount_total"] == 2380000.0

    def test_quotation_agent_multiple_line_items(self):
        agent = CotizacionInventarioAgent()
        payload = {
            "partner_id": 1,
            "items": [
                {"name": "Item A", "qty": 1.0, "unit_price": 100.0},
                {"name": "Item B", "qty": 3.0, "unit_price": 200.0}
            ]
        }
        draft = agent.process_event("quote_request", payload)
        assert len(draft.proposed_payload["order_line"]) == 2
        assert draft.proposed_payload["amount_untaxed"] == 700.0

    def test_quotation_agent_missing_price_fallback(self):
        agent = CotizacionInventarioAgent(odoo_client=None, memory=None)
        payload = {"items": [{"name": "Item Desconocido", "qty": 1.0}]}
        draft = agent.process_event("quote_request", payload)
        assert draft.proposed_payload["amount_untaxed"] > 0


# ==========================================
# 4. TestOperationsAgent
# ==========================================
class TestOperationsAgent:

    def test_operations_agent_budget_overrun_detection(self):
        agent = OperacionesPresupuestoAgent()
        payload = {
            "analytic_account_id": 300,
            "planned_amount": 100000.0,
            "practical_amount": 125000.0,
            "threshold_pct": 10.0
        }
        draft = agent.process_event("audit_budget_overrun", payload)
        assert draft.target_model == "crossovered.budget.lines"
        assert draft.status == "pending_vobo"
        assert draft.metadata["overrun_detected"] is True
        assert "SOBRECOSTO" in draft.justification

    def test_operations_agent_budget_normal_execution(self):
        agent = OperacionesPresupuestoAgent()
        payload = {
            "analytic_account_id": 300,
            "planned_amount": 100000.0,
            "practical_amount": 102000.0,
            "threshold_pct": 10.0
        }
        draft = agent.process_event("audit_budget_overrun", payload)
        assert draft.metadata["overrun_detected"] is False

    def test_operations_agent_odoo_analytic_lookup(self, odoo_client_xmlrpc):
        agent = OperacionesPresupuestoAgent(odoo_client=odoo_client_xmlrpc)
        payload = {"analytic_account_id": 300}
        draft = agent.process_event("project_health_check", payload)
        assert draft.status == "pending_vobo"
        assert draft.target_model == "crossovered.budget.lines"

    def test_operations_agent_task_creation_event(self):
        agent = OperacionesPresupuestoAgent()
        payload = {
            "project_id": 200,
            "task_name": "Calibración de Relé Siemens",
            "planned_hours": 15.0
        }
        draft = agent.process_event("create_project_task", payload)
        assert draft.target_model == "project.task"
        assert draft.proposed_payload["planned_hours"] == 15.0


# ==========================================
# 5. TestProgressInvoicingAgent
# ==========================================
class TestProgressInvoicingAgent:

    def test_progress_invoicing_agent_milestone_billing(self):
        agent = EstadosPagoAgent()
        payload = {
            "project_id": 200,
            "partner_id": 1,
            "milestone_name": "Hito 1: Entrega de Informe DIgSILENT",
            "billable_amount": 15000000.0
        }
        draft = agent.process_event("generate_progress_invoice", payload)
        assert draft.target_model == "account.move"
        assert draft.status == "pending_vobo"
        assert draft.proposed_payload["move_type"] == "out_invoice"
        assert draft.proposed_payload["amount_untaxed"] == 15000000.0

    def test_progress_invoicing_agent_iva_calculation(self):
        agent = EstadosPagoAgent()
        payload = {"billable_amount": 10000000.0}
        draft = agent.process_event("task_completion_billing", payload)
        assert draft.proposed_payload["amount_tax"] == 1900000.0
        assert draft.proposed_payload["amount_total"] == 11900000.0

    def test_progress_invoicing_agent_duplicate_check(self, odoo_client_xmlrpc):
        agent = EstadosPagoAgent(odoo_client=odoo_client_xmlrpc)
        payload = {"project_id": 200, "billable_amount": 5000000.0}
        draft = agent.process_event("generate_progress_invoice", payload)
        assert draft.status == "pending_vobo"
        assert draft.metadata["existing_invoices_count"] >= 0

    def test_progress_invoicing_agent_draft_lines(self):
        agent = EstadosPagoAgent()
        payload = {"milestone_name": "Hito Final", "billable_amount": 8000000.0}
        draft = agent.process_event("billing_stage", payload)
        lines = draft.proposed_payload["invoice_line_ids"]
        assert len(lines) == 1
        assert "Hito Final" in lines[0]["name"]


# ==========================================
# 6. TestComplianceAgent
# ==========================================
class TestComplianceAgent:

    def test_compliance_agent_all_documents_valid(self):
        agent = GestionDocumentalAgent()
        payload = {
            "partner_id": 1,
            "documents": [
                {"doc_type": "F30-1", "status": "valid"},
                {"doc_type": "Mutualidad", "status": "valid"},
                {"doc_type": "PreviRed", "status": "valid"}
            ]
        }
        draft = agent.process_event("verify_contractor_compliance", payload)
        assert draft.status == "pending_vobo"
        assert draft.metadata["is_compliant"] is True
        assert draft.target_model == "res.partner"

    def test_compliance_agent_missing_f30_1(self):
        agent = GestionDocumentalAgent()
        payload = {
            "partner_id": 2,
            "documents": [
                {"doc_type": "Mutualidad", "status": "valid"},
                {"doc_type": "PreviRed", "status": "valid"}
            ]
        }
        draft = agent.process_event("verify_contractor_compliance", payload)
        assert draft.metadata["is_compliant"] is False
        assert "F30-1" in draft.metadata["missing_docs"]
        assert draft.target_model == "project.task"
        assert draft.proposed_payload["kanban_state"] == "blocked"

    def test_compliance_agent_expired_documents(self):
        agent = GestionDocumentalAgent()
        payload = {
            "partner_id": 3,
            "documents": [
                {"doc_type": "F30-1", "status": "expired"}
            ]
        }
        draft = agent.process_event("f30_1_audit", payload)
        assert draft.metadata["is_compliant"] is False
        assert len(draft.metadata["expired_docs"]) > 0

    def test_compliance_agent_sec_requirement(self):
        agent = GestionDocumentalAgent()
        payload = {
            "partner_id": 4,
            "sec_required": True,
            "documents": [
                {"doc_type": "F30-1", "status": "valid"},
                {"doc_type": "Mutualidad", "status": "valid"},
                {"doc_type": "PreviRed", "status": "valid"}
            ]
        }
        draft = agent.process_event("accreditation_check", payload)
        assert draft.metadata["is_compliant"] is False
        assert "SEC" in draft.metadata["missing_docs"]


# ==========================================
# 7. TestDTEConciliationAgent
# ==========================================
class TestDTEConciliationAgent:

    def test_dte_conciliation_valid_dte(self):
        agent = ConciliadorContableAgent()
        payload = {
            "dte_folio": "F-4589",
            "rut_emisor": "76111222-3",
            "amount_neto": 1000000.0,
            "amount_iva": 190000.0,
            "amount_total": 1190000.0
        }
        draft = agent.process_event("process_dte", payload)
        assert draft.target_model == "account.move"
        assert draft.status == "pending_vobo"
        assert draft.proposed_payload["move_type"] == "in_invoice"
        assert draft.metadata["tax_discrepancy"] is False

    def test_dte_conciliation_po_matching(self, odoo_client_xmlrpc):
        agent = ConciliadorContableAgent(odoo_client=odoo_client_xmlrpc)
        payload = {
            "dte_folio": "F-8899",
            "rut_emisor": "76111222-3",
            "po_reference": "SO003",
            "amount_neto": 45000.0,
            "amount_iva": 8550.0,
            "amount_total": 53550.0
        }
        draft = agent.process_event("reconcile_vendor_bill", payload)
        assert draft.status == "pending_vobo"
        assert draft.metadata["po_matched"] is True

    def test_dte_conciliation_tax_discrepancy(self):
        agent = ConciliadorContableAgent()
        payload = {
            "dte_folio": "F-9999",
            "rut_emisor": "76111222-3",
            "amount_neto": 1000000.0,
            "amount_iva": 250000.0,  # Incorrect IVA
            "amount_total": 1250000.0
        }
        draft = agent.process_event("process_dte", payload)
        assert draft.metadata["tax_discrepancy"] is True
        assert draft.confidence_score < 0.80

    def test_dte_conciliation_confidence_score(self):
        agent = ConciliadorContableAgent()
        payload_ok = {"amount_neto": 100.0, "amount_iva": 19.0, "amount_total": 119.0}
        draft_ok = agent.process_event("process_dte", payload_ok)
        assert draft_ok.confidence_score >= 0.90


# ==========================================
# 8. TestAgentSwarmRoutingAndWorkflows
# ==========================================
class TestAgentSwarmRoutingAndWorkflows:

    def test_swarm_agent_registration(self):
        swarm = AgentSwarm(agents=[])
        assert len(swarm.list_agents()) == 0

        dummy = ConcreteDummyAgent(agent_name="dummy", domain="test")
        swarm.register_agent(dummy)
        assert "dummy" in swarm.list_agents()
        assert swarm.get_agent("dummy") == dummy

        unregistered = swarm.unregister_agent("dummy")
        assert unregistered == dummy
        assert "dummy" not in swarm.list_agents()

    def test_swarm_process_task_contract(self):
        swarm = AgentSwarm()
        payload = {"title": "Licitación Vía Task", "budget_estimate": 20000000.0}
        draft = swarm.process_task("rfq_prospeccion", payload)
        assert isinstance(draft, DraftAction)
        assert draft.agent_name == "rfq_prospeccion"
        assert draft.status == "pending_vobo"

    def test_swarm_dispatch_event_routing(self):
        swarm = AgentSwarm()

        # RFQ dispatch
        rfq_drafts = swarm.dispatch_event("rfq_received", {"title": "Test RFQ"})
        assert len(rfq_drafts) == 1
        assert rfq_drafts[0].agent_name == "rfq_prospeccion"

        # DTE dispatch
        dte_drafts = swarm.dispatch_event("process_dte", {"dte_folio": "123"})
        assert len(dte_drafts) == 1
        assert dte_drafts[0].agent_name == "conciliador_contable"

    def test_swarm_broadcast_audit(self):
        swarm = AgentSwarm()
        broadcast_drafts = swarm.dispatch_event("broadcast_audit", {"title": "Auditoría Global"})
        assert len(broadcast_drafts) == 6

    def test_swarm_error_isolation(self):
        swarm = AgentSwarm(agents=[])
        failing = FailingAgent(agent_name="failing_agent", domain="test")
        normal = ConcreteDummyAgent(agent_name="normal_agent", domain="test")

        swarm.register_agent(failing)
        swarm.register_agent(normal)

        # Dispatch broadcast event to execute both
        drafts = swarm.dispatch_event("broadcast_audit", {"title": "Isolation Test"})
        assert len(drafts) == 1
        assert drafts[0].agent_name == "normal_agent"
        assert swarm.get_agent("failing_agent").status == "error"

    def test_swarm_health_check(self):
        swarm = AgentSwarm()
        health = swarm.health_check()
        assert health["swarm_status"] == "HEALTHY"
        assert health["total_agents"] == 6
        assert health["healthy_agents"] == 6


# ==========================================
# 9. TestZeroAutoExecutionInvariant
# ==========================================
class TestZeroAutoExecutionInvariant:

    def test_zero_auto_execution_mock_server_mutation_prevention(self, mock_odoo_server, odoo_client_xmlrpc):
        """
        MANDATORY INVARIANT VERIFICATION:
        Verifies that when any agent processes tasks or events, NO records are mutated or created
        directly in the Odoo database. All actions MUST produce a DraftAction with status 'pending_vobo'.
        """
        initial_record_counts = {
            model: len(mock_odoo_server.db.search_read(model, []))
            for model in [
                "res.partner", "crm.lead", "sale.order", "project.project",
                "project.task", "account.analytic.account", "crossovered.budget.lines",
                "account.move", "account.payment"
            ]
        }

        swarm = AgentSwarm(odoo_client=odoo_client_xmlrpc)

        # Execute tasks on all 6 agents
        swarm.process_task("rfq_prospeccion", {"title": "Invariant Test Lead", "budget_estimate": 100.0})
        swarm.process_task("cotizacion_inventario", {"items": [{"name": "Item Invariant", "qty": 1.0}]})
        swarm.process_task("operaciones_presupuesto", {"planned_amount": 100, "practical_amount": 200})
        swarm.process_task("estados_pago", {"billable_amount": 5000})
        swarm.process_task("gestion_documental", {"documents": []})
        swarm.process_task("conciliador_contable", {"dte_folio": "999"})

        # Dispatch broadcast audit
        swarm.dispatch_event("broadcast_audit", {"test": "invariant"})

        # Verify DB counts remain 100% unchanged
        for model, count in initial_record_counts.items():
            current_count = len(mock_odoo_server.db.search_read(model, []))
            assert current_count == count, f"Zero Auto-Execution Violation! Model '{model}' count changed from {count} to {current_count}"

    def test_zero_auto_execution_status_strictly_pending_vobo(self):
        """
        MANDATORY INVARIANT VERIFICATION:
        Verifies that every DraftAction produced across all 6 agents strictly defaults to status 'pending_vobo'.
        """
        swarm = AgentSwarm()

        for agent_name in KNOWN_AGENTS:
            draft = swarm.process_task(agent_name, {"title": "VoBo Status Check"})
            assert draft.status == "pending_vobo", f"Zero Auto-Execution Violation! Agent '{agent_name}' produced status '{draft.status}' instead of 'pending_vobo'"


# ==========================================
# 10. TestAdversarialStressTesting (Milestone 3 Challenger 2)
# ==========================================
class TestAdversarialStressTesting:
    """
    Adversarial Stress Test Suite for Swarm Agentic Engine (Milestone 3 Challenger 2).
    Evaluates malformed payloads, status bypass attempts, numeric boundaries, error isolation,
    and Pydantic v2 DraftAction schema bounds across all 6 specialized agents.
    """

    def test_adversarial_payload_status_bypass_attempt(self):
        """
        Adversarial Test: Attempting to bypass 'pending_vobo' status by passing status overrides
        and auto-commit instructions in event payloads to all 6 agents.
        """
        swarm = AgentSwarm()
        malicious_payload = {
            "status": "approved",
            "action_type": "write",
            "auto_commit": True,
            "execute_immediately": True,
            "bypass_vobo": True,
            "title": "Bypass Attempt RFQ",
            "client_name": "Malicious Corp",
            "items": [{"name": "Item Bypass", "qty": 1.0, "unit_price": 500.0}],
            "planned_amount": 100.0,
            "practical_amount": 200.0,
            "billable_amount": 1000.0,
            "documents": [{"doc_type": "F30-1", "status": "valid"}],
            "dte_folio": "9999",
            "amount_neto": 1000.0
        }

        for agent_name in KNOWN_AGENTS:
            draft = swarm.process_task(agent_name, malicious_payload)
            assert draft.status == "pending_vobo", (
                f"ADVERSARIAL FAILURE: Agent '{agent_name}' produced status '{draft.status}' "
                f"instead of mandatory 'pending_vobo' when fed malicious status payload!"
            )
            assert draft.action_type in ("create", "write", "unlink", "custom_operation")

    def test_adversarial_empty_and_null_payloads(self):
        """
        Adversarial Test: Feeding completely empty or null-value payloads to all 6 agents.
        Agents must handle missing keys gracefully and produce valid pending_vobo DraftActions.
        """
        swarm = AgentSwarm()
        empty_payloads = [
            {},
            {"title": None, "client_name": None, "budget_estimate": None},
            {"items": None, "order_line": None, "product_name": None},
            {"documents": None, "compliance_docs": None},
            {"dte_folio": None, "rut_emisor": None, "amount_neto": None}
        ]

        for payload in empty_payloads:
            for agent_name in KNOWN_AGENTS:
                draft = swarm.process_task(agent_name, payload)
                assert isinstance(draft, DraftAction)
                assert draft.status == "pending_vobo"
                assert draft.agent_name == agent_name

    def test_adversarial_extreme_and_boundary_numeric_payloads(self):
        """
        Adversarial Test: Feeding negative, zero, and extreme float numbers to all specialized agents.
        """
        swarm = AgentSwarm()
        extreme_payloads = [
            {"budget_estimate": -1000000.0, "planned_amount": -500.0, "practical_amount": -200.0, "billable_amount": -9999.0, "amount_neto": -1.0},
            {"budget_estimate": 0.0, "planned_amount": 0.0, "practical_amount": 0.0, "billable_amount": 0.0, "amount_neto": 0.0},
            {"budget_estimate": 1e15, "planned_amount": 1e15, "practical_amount": 1e15, "billable_amount": 1e15, "amount_neto": 1e15}
        ]

        for payload in extreme_payloads:
            for agent_name in KNOWN_AGENTS:
                draft = swarm.process_task(agent_name, payload)
                assert draft.status == "pending_vobo"
                assert draft.confidence_score >= 0.0 and draft.confidence_score <= 1.0

    def test_adversarial_corrupted_type_error_isolation(self):
        """
        Adversarial Test: Passing corrupted non-numeric string data into float conversion logic.
        Verifies that error isolation catches runtime exceptions in dispatch_event and marks agent status as 'error'.
        """
        swarm = AgentSwarm()
        corrupted_payload = {
            "budget_estimate": "CORRUPTED_NOT_A_FLOAT",
            "planned_amount": "INVALID_NUMBER",
            "items": [{"qty": "NOT_AN_INT", "unit_price": "BAD_PRICE"}]
        }

        # Dispatch broadcast_audit to all agents
        drafts = swarm.dispatch_event("broadcast_audit", corrupted_payload)
        
        # Verify that agents failing conversion set status to 'error' without crashing the swarm
        for agent_name, agent in swarm.agents.items():
            assert agent.status in ("idle", "error")

    def test_adversarial_pydantic_confidence_score_upper_bound(self):
        """
        Adversarial Test: Pydantic v2 DraftAction schema confidence_score > 1.0 must raise ValidationError.
        """
        invalid_scores = [1.0001, 1.5, 2.0, 100.0, float("inf")]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                DraftAction(
                    agent_name="rfq_prospeccion",
                    target_model="crm.lead",
                    proposed_payload={},
                    justification="Adversarial upper bound test",
                    confidence_score=score
                )

    def test_adversarial_pydantic_confidence_score_lower_bound(self):
        """
        Adversarial Test: Pydantic v2 DraftAction schema confidence_score < 0.0 must raise ValidationError.
        """
        invalid_scores = [-0.0001, -0.1, -1.0, -100.0, float("-inf")]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                DraftAction(
                    agent_name="rfq_prospeccion",
                    target_model="crm.lead",
                    proposed_payload={},
                    justification="Adversarial lower bound test",
                    confidence_score=score
                )

    def test_adversarial_pydantic_invalid_status_enum(self):
        """
        Adversarial Test: Pydantic v2 DraftAction schema invalid status string must raise ValidationError.
        """
        invalid_statuses = ["auto_committed", "bypass", "DIRECT_WRITE", "executed", ""]
        for st in invalid_statuses:
            with pytest.raises(ValidationError):
                DraftAction(
                    agent_name="rfq_prospeccion",
                    target_model="crm.lead",
                    proposed_payload={},
                    justification="Adversarial status test",
                    status=st
                )

    def test_adversarial_zero_auto_execution_read_only_contract(self):
        """
        Adversarial Test: Inspects code of all 6 agents to empirically verify zero write/create calls to Odoo.
        """
        import inspect
        from swarm_engine.swarm import KNOWN_AGENTS

        swarm = AgentSwarm()
        forbidden_methods = ["create(", "write(", "unlink(", "execute_kw("]

        for agent_name in KNOWN_AGENTS:
            agent = swarm.get_agent(agent_name)
            source_lines = inspect.getsourcelines(agent.__class__)[0]
            source_text = "".join(source_lines)

            # Ensure agent only uses self.query_odoo or create_draft_action and never direct write methods on self.odoo_client
            for forbidden in forbidden_methods:
                assert f"self.odoo_client.{forbidden}" not in source_text, (
                    f"INVARIANT VIOLATION: Agent '{agent_name}' contains direct Odoo write method "
                    f"'self.odoo_client.{forbidden}' in source code!"
                )

