"""
Comprehensive Pytest Suite for Supervisor Human-in-the-Loop Web Console (Milestone 4).
Tests SupervisorConsole queue management, approve/reject workflows, SupervisorAuditLogger,
REST API endpoints (/api/drafts, /api/drafts/<id>/approve, /api/drafts/<id>/reject, /api/audit-logs),
and strictly enforces the Zero Auto-Execution Invariant.
"""

import pytest
import tempfile
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

from odoo_ecosystem.mock_server import MockOdooServer, OdooVersion
from odoo_ecosystem.client import OdooClient, OdooConfig
from swarm_engine.base_agent import DraftAction
from swarm_engine.swarm import AgentSwarm
from supervisor_ui.audit_logger import SupervisorAuditLogger, SupervisorAuditEntry
from supervisor_ui.console import SupervisorConsole, DraftNotFoundError, InvalidDraftStateError
from supervisor_ui.app import create_app


# ==========================================
# PYTEST FIXTURES
# ==========================================

@pytest.fixture
def mock_odoo_server():
    """Provides a fresh MockOdooServer instance pre-seeded with model records."""
    return MockOdooServer(version=OdooVersion.V16)


@pytest.fixture
def odoo_client(mock_odoo_server):
    """OdooClient connected to MockOdooServer."""
    cfg = OdooConfig(protocol="xmlrpc", max_retries=3, rate_limit_rps=100.0)
    return OdooClient(config=cfg, mock_server=mock_odoo_server)


@pytest.fixture
def temp_audit_logger(tmp_path):
    """Provides an isolated SupervisorAuditLogger using pytest tmp_path."""
    log_file = os.path.join(tmp_path, "test_supervisor_audit.jsonl")
    return SupervisorAuditLogger(log_file_path=log_file)


@pytest.fixture
def supervisor_console(odoo_client, temp_audit_logger):
    """SupervisorConsole instance wired with MockOdooServer and isolated audit logger."""
    swarm = AgentSwarm(odoo_client=odoo_client)
    return SupervisorConsole(swarm=swarm, odoo_client=odoo_client, audit_logger=temp_audit_logger)


@pytest.fixture
def sample_drafts():
    """Provides a set of 6 distinct DraftActions generated across all specialized agents."""
    return [
        DraftAction(
            agent_name="rfq_prospeccion",
            target_model="crm.lead",
            action_type="create",
            proposed_payload={"name": "Oportunidad Licitación Solar", "expected_revenue": 50000.0, "password": "secret_pass_123"},
            justification="RAG few-shot match high win rate",
            confidence_score=0.92
        ),
        DraftAction(
            agent_name="cotizacion_inventario",
            target_model="sale.order",
            action_type="create",
            proposed_payload={"partner_id": 1, "amount_untaxed": 20000.0, "amount_total": 23800.0},
            justification="Stock matched in warehouse",
            confidence_score=0.88
        ),
        DraftAction(
            agent_name="operaciones_presupuesto",
            target_model="crossovered.budget.lines",
            action_type="write",
            proposed_payload={"planned_amount": 120000.0},
            justification="Budget adjustment required",
            confidence_score=0.95
        ),
        DraftAction(
            agent_name="estados_pago",
            target_model="account.move",
            action_type="create",
            proposed_payload={"move_type": "out_invoice", "amount_total": 11900.0},
            justification="Milestone 2 completed",
            confidence_score=0.90
        ),
        DraftAction(
            agent_name="gestion_documental",
            target_model="res.partner",
            action_type="write",
            proposed_payload={"compliance_status": "audited"},
            justification="F30-1 and Mutualidad verified",
            confidence_score=0.99
        ),
        DraftAction(
            agent_name="conciliador_contable",
            target_model="account.move",
            action_type="create",
            proposed_payload={"move_type": "in_invoice", "ref": "DTE-9988"},
            justification="DTE matched with PO SO003",
            confidence_score=0.65
        )
    ]


@pytest.fixture
def api_test_client(supervisor_console):
    """Test client fixture for Supervisor UI Flask REST API."""
    app = create_app(console=supervisor_console)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ==========================================
# 1. TestSupervisorConsoleQueue Management
# ==========================================
class TestSupervisorConsoleQueue:

    def test_register_draft_and_get_by_id(self, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        registered = supervisor_console.register_draft(draft)
        assert registered.draft_id == draft.draft_id

        fetched = supervisor_console.get_draft_by_id(draft.draft_id)
        assert fetched.agent_name == "rfq_prospeccion"
        assert fetched.target_model == "crm.lead"

    def test_ingest_swarm_drafts_bulk(self, supervisor_console, sample_drafts):
        ingested = supervisor_console.ingest_swarm_drafts(sample_drafts)
        assert len(ingested) == 6
        stats = supervisor_console.get_stats()
        assert stats["total_drafts"] == 6
        assert stats["by_status"]["pending_vobo"] == 6

    def test_get_pending_drafts_filtering_by_agent(self, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        rfq_drafts = supervisor_console.get_pending_drafts(agent_filter="rfq_prospeccion")
        assert len(rfq_drafts) == 1
        assert rfq_drafts[0].agent_name == "rfq_prospeccion"

        empty_drafts = supervisor_console.get_pending_drafts(agent_filter="non_existent_agent")
        assert len(empty_drafts) == 0

    def test_get_pending_drafts_filtering_by_min_confidence(self, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        high_conf = supervisor_console.get_pending_drafts(min_confidence=0.85)
        # sample_drafts: 0.92, 0.88, 0.95, 0.90, 0.99, 0.65 -> 5 drafts >= 0.85
        assert len(high_conf) == 5

    def test_get_pending_drafts_filtering_by_status(self, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)
        draft1 = sample_drafts[0]
        draft2 = sample_drafts[1]

        supervisor_console.approve_draft(draft1.draft_id, supervisor_id="sup_01")
        supervisor_console.reject_draft(draft2.draft_id, supervisor_id="sup_01", reason="Rejected")

        pending = supervisor_console.get_pending_drafts(status_filter="pending_vobo")
        assert len(pending) == 4

        approved = supervisor_console.get_pending_drafts(status_filter="committed")
        assert len(approved) == 1

        rejected = supervisor_console.get_pending_drafts(status_filter="rejected")
        assert len(rejected) == 1

        all_drafts = supervisor_console.get_pending_drafts(status_filter="all")
        assert len(all_drafts) == 6

    def test_get_pending_drafts_sorting_order(self, supervisor_console):
        d1 = DraftAction(
            agent_name="rfq_prospeccion", target_model="crm.lead",
            proposed_payload={"name": "D1"}, justification="j1", created_at="2026-07-28T10:00:00Z"
        )
        d2 = DraftAction(
            agent_name="rfq_prospeccion", target_model="crm.lead",
            proposed_payload={"name": "D2"}, justification="j2", created_at="2026-07-28T12:00:00Z"
        )
        d3 = DraftAction(
            agent_name="rfq_prospeccion", target_model="crm.lead",
            proposed_payload={"name": "D3"}, justification="j3", created_at="2026-07-28T11:00:00Z"
        )
        supervisor_console.register_draft(d1)
        supervisor_console.register_draft(d2)
        supervisor_console.register_draft(d3)

        res = supervisor_console.get_pending_drafts(status_filter="pending_vobo")
        assert res[0].draft_id == d2.draft_id
        assert res[1].draft_id == d3.draft_id
        assert res[2].draft_id == d1.draft_id

    def test_get_draft_by_id_not_found(self, supervisor_console):
        with pytest.raises(DraftNotFoundError):
            supervisor_console.get_draft_by_id("draft_non_existent")

    def test_get_draft_detail(self, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)
        detail = supervisor_console.get_draft_detail(draft.draft_id)

        assert detail["draft_id"] == draft.draft_id
        assert detail["risk_assessment"]["score"] == "LOW"
        assert "diff" in detail


# ==========================================
# 2. TestApproveDraftWorkflow
# ==========================================
class TestApproveDraftWorkflow:

    def test_approve_draft_commits_to_odoo_db(self, supervisor_console, mock_odoo_server, sample_drafts):
        draft = sample_drafts[0]  # crm.lead
        supervisor_console.register_draft(draft)

        initial_count = len(mock_odoo_server.db.search_read("crm.lead", []))
        result = supervisor_console.approve_draft(
            draft_id=draft.draft_id,
            supervisor_id="supervisor_valencia",
            justification="Approved after technical validation"
        )

        assert result["status"] in ("approved", "committed")
        assert result["supervisor_id"] == "supervisor_valencia"
        assert result["odoo_record_id"] is not None

        new_count = len(mock_odoo_server.db.search_read("crm.lead", []))
        assert new_count == initial_count + 1

        updated_draft = supervisor_console.get_draft_by_id(draft.draft_id)
        assert updated_draft.status in ("approved", "committed")

    def test_approve_draft_without_odoo_client(self, temp_audit_logger, sample_drafts):
        standalone_console = SupervisorConsole(odoo_client=None, audit_logger=temp_audit_logger)
        draft = sample_drafts[0]
        standalone_console.register_draft(draft)

        res = standalone_console.approve_draft(draft_id=draft.draft_id, supervisor_id="sup_01")
        assert res["status"] == "approved"
        assert res["odoo_record_id"] is None
        assert draft.status == "approved"

    def test_approve_draft_creates_audit_log_entry(self, supervisor_console, temp_audit_logger, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)

        supervisor_console.approve_draft(
            draft_id=draft.draft_id,
            supervisor_id="supervisor_valencia",
            justification="Approved VoBo"
        )

        logs = temp_audit_logger.query_logs(draft_id=draft.draft_id)
        assert len(logs) == 1
        assert logs[0].verdict == "approved"
        assert logs[0].supervisor_id == "supervisor_valencia"
        assert logs[0].odoo_model == "crm.lead"

    def test_approve_draft_missing_supervisor_id_validation(self, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)

        with pytest.raises(ValueError):
            supervisor_console.approve_draft(draft_id=draft.draft_id, supervisor_id="")

        with pytest.raises(ValueError):
            supervisor_console.approve_draft(draft_id=draft.draft_id, supervisor_id="   ")

    def test_approve_draft_invalid_state_transition(self, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)

        supervisor_console.approve_draft(draft_id=draft.draft_id, supervisor_id="sup_01")

        # Second approval attempt must raise InvalidDraftStateError
        with pytest.raises(InvalidDraftStateError):
            supervisor_console.approve_draft(draft_id=draft.draft_id, supervisor_id="sup_02")


# ==========================================
# 3. TestRejectDraftWorkflow
# ==========================================
class TestRejectDraftWorkflow:

    def test_reject_draft_updates_status_and_prevents_odoo_mutation(self, supervisor_console, mock_odoo_server, sample_drafts):
        draft = sample_drafts[1]  # sale.order
        supervisor_console.register_draft(draft)

        initial_count = len(mock_odoo_server.db.search_read("sale.order", []))

        result = supervisor_console.reject_draft(
            draft_id=draft.draft_id,
            supervisor_id="supervisor_valencia",
            reason="Margin too low"
        )

        assert result["status"] == "rejected"
        assert result["odoo_record_id"] is None
        assert result["reason"] == "Margin too low"

        # Verify DB mutation did NOT occur
        new_count = len(mock_odoo_server.db.search_read("sale.order", []))
        assert new_count == initial_count

        updated_draft = supervisor_console.get_draft_by_id(draft.draft_id)
        assert updated_draft.status == "rejected"

    def test_reject_draft_creates_audit_log_entry(self, supervisor_console, temp_audit_logger, sample_drafts):
        draft = sample_drafts[1]
        supervisor_console.register_draft(draft)

        supervisor_console.reject_draft(
            draft_id=draft.draft_id,
            supervisor_id="supervisor_valencia",
            reason="Unacceptable terms"
        )

        logs = temp_audit_logger.query_logs(draft_id=draft.draft_id)
        assert len(logs) == 1
        assert logs[0].verdict == "rejected"
        assert logs[0].justification == "Unacceptable terms"
        assert logs[0].odoo_record_id is None

    def test_reject_draft_missing_supervisor_id_validation(self, supervisor_console, sample_drafts):
        draft = sample_drafts[1]
        supervisor_console.register_draft(draft)

        with pytest.raises(ValueError):
            supervisor_console.reject_draft(draft_id=draft.draft_id, supervisor_id="")

    def test_reject_draft_invalid_state_transition(self, supervisor_console, sample_drafts):
        draft = sample_drafts[1]
        supervisor_console.register_draft(draft)

        supervisor_console.reject_draft(draft_id=draft.draft_id, supervisor_id="sup_01")

        with pytest.raises(InvalidDraftStateError):
            supervisor_console.reject_draft(draft_id=draft.draft_id, supervisor_id="sup_02")


# ==========================================
# 4. TestSupervisorRESTAPI Endpoints
# ==========================================
class TestSupervisorRESTAPI:

    def test_api_index_route(self, api_test_client):
        response = api_test_client.get("/")
        assert response.status_code == 200

    def test_api_get_drafts_list(self, api_test_client, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        response = api_test_client.get("/api/drafts")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 6

    def test_api_get_drafts_filtered(self, api_test_client, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        response = api_test_client.get("/api/drafts?agent=rfq_prospeccion")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["drafts"][0]["agent_name"] == "rfq_prospeccion"

    def test_api_get_draft_detail(self, api_test_client, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)

        response = api_test_client.get(f"/api/drafts/{draft.draft_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["draft"]["draft_id"] == draft.draft_id

    def test_api_get_draft_detail_not_found(self, api_test_client):
        response = api_test_client.get("/api/drafts/draft_invalid")
        assert response.status_code == 404

    def test_api_post_approve_draft_success(self, api_test_client, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)

        payload = {"supervisor_id": "sup_api_user", "justification": "API Approval"}
        response = api_test_client.post(f"/api/drafts/{draft.draft_id}/approve", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"] in ("approved", "committed")

    def test_api_post_approve_draft_missing_supervisor_id(self, api_test_client, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)

        response = api_test_client.post(f"/api/drafts/{draft.draft_id}/approve", json={})
        assert response.status_code == 400

    def test_api_post_reject_draft_success(self, api_test_client, supervisor_console, sample_drafts):
        draft = sample_drafts[1]
        supervisor_console.register_draft(draft)

        payload = {"supervisor_id": "sup_api_user", "reason": "API Rejection"}
        response = api_test_client.post(f"/api/drafts/{draft.draft_id}/reject", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"] == "rejected"

    def test_api_get_audit_logs(self, api_test_client, supervisor_console, sample_drafts):
        draft = sample_drafts[0]
        supervisor_console.register_draft(draft)
        supervisor_console.approve_draft(draft.draft_id, supervisor_id="sup_api_user")

        response = api_test_client.get("/api/audit-logs")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] >= 1

    def test_api_get_stats(self, api_test_client, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        response = api_test_client.get("/api/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["stats"]["total_drafts"] == 6


# ==========================================
# 4b. TestOperationsRESTAPI Endpoints
# ==========================================
class TestOperationsRESTAPI:

    def test_ops_doc_automator_generate(self, api_test_client):
        res = api_test_client.post("/api/operations/doc-automator/generate", json={
            "ot_code": "OT-7048", "doc_type": "handover", "client_name": "Transelec"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["doc_type"] == "handover"

    def test_ops_fat_sat_run_fat(self, api_test_client):
        res = api_test_client.post("/api/operations/fat-sat/run-fat", json={"ot_code": "OT-7048"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["result"]["overall_status"] == "APPROVED_100_PERCENT"

    def test_ops_fat_sat_run_sat(self, api_test_client):
        res = api_test_client.post("/api/operations/fat-sat/run-sat", json={"ot_code": "OT-7048"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_ops_fat_sat_certificate(self, api_test_client):
        res = api_test_client.post("/api/operations/fat-sat/certificate", json={"ot_code": "OT-7048"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_ops_kitting_build_kit(self, api_test_client):
        res = api_test_client.post("/api/operations/kitting/build-kit", json={"ot_code": "OT-7050", "kit_type": "PMU_PANEL_KIT_A"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "checklist" in data

    def test_ops_accreditation_compile(self, api_test_client):
        res = api_test_client.post("/api/operations/accreditation/compile", json={"ot_code": "OT-7060", "client": "Enel"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_ops_payment_statement_generate(self, api_test_client):
        res = api_test_client.post("/api/operations/payment-statement/generate", json={"ot_code": "OT-7048", "client_name": "Colbún"})
        assert res.status_code == 201
        data = res.get_json()
        assert data["success"] is True
        assert data["draft_id"] is not None

    def test_ops_metrics(self, api_test_client):
        res = api_test_client.get("/api/operations/metrics?num_ots=5&total_contract_uf=3500")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["metrics"]["retained_gross_margin_pct"] == 54.8



# ==========================================
# 5. TestZeroAutoExecutionInvariantM4
# ==========================================
class TestZeroAutoExecutionInvariantM4:

    def test_unapproved_drafts_in_queue_cannot_affect_odoo_db(self, supervisor_console, mock_odoo_server, sample_drafts):
        """
        MANDATORY INVARIANT VERIFICATION:
        Verifies that staging drafts in SupervisorConsole queue does NOT alter Odoo database state
        until explicit supervisor approval signature is received.
        """
        initial_counts = {
            model: len(mock_odoo_server.db.search_read(model, []))
            for model in ["crm.lead", "sale.order", "account.move", "res.partner", "crossovered.budget.lines"]
        }

        # Ingest all drafts into queue
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        # Confirm queue has drafts
        assert supervisor_console.get_stats()["total_drafts"] == 6

        # Verify DB counts remain 100% unchanged
        for model, initial_c in initial_counts.items():
            current_c = len(mock_odoo_server.db.search_read(model, []))
            assert current_c == initial_c, f"Zero Auto-Execution Violation! Model '{model}' mutated prematurely."

        # Reject a draft
        supervisor_console.reject_draft(sample_drafts[1].draft_id, supervisor_id="sup_test")

        # Verify DB counts STILL unchanged
        for model, initial_c in initial_counts.items():
            current_c = len(mock_odoo_server.db.search_read(model, []))
            assert current_c == initial_c, f"Zero Auto-Execution Violation! Model '{model}' mutated upon rejection."

        # Approve 1 draft (crm.lead)
        supervisor_console.approve_draft(sample_drafts[0].draft_id, supervisor_id="sup_test")

        # Verify ONLY crm.lead count incremented
        assert len(mock_odoo_server.db.search_read("crm.lead", [])) == initial_counts["crm.lead"] + 1
        assert len(mock_odoo_server.db.search_read("sale.order", [])) == initial_counts["sale.order"]


# ==========================================
# 6. TestSupervisorAdversarialAndAudit
# ==========================================
class TestSupervisorAdversarialAndAudit:

    def test_supervisor_console_concurrent_approvals(self, supervisor_console, sample_drafts):
        supervisor_console.ingest_swarm_drafts(sample_drafts)

        def approve_worker(draft):
            try:
                return supervisor_console.approve_draft(draft.draft_id, supervisor_id="thread_sup", justification="Parallel test")
            except Exception as e:
                return e

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(approve_worker, sample_drafts))

        for res in results:
            assert isinstance(res, dict)
            assert res["status"] in ("approved", "committed")

        stats = supervisor_console.get_stats()
        assert stats["by_status"]["committed"] == 6 or stats["by_status"]["approved"] == 6

    def test_sensitive_credential_masking_in_audit_logs(self, supervisor_console, temp_audit_logger, sample_drafts):
        draft = sample_drafts[0] # payload contains "password": "secret_pass_123"
        supervisor_console.register_draft(draft)

        supervisor_console.approve_draft(draft.draft_id, supervisor_id="sup_mask_test")

        logs = temp_audit_logger.query_logs(draft_id=draft.draft_id)
        assert len(logs) == 1
        audit_entry = logs[0]
        assert audit_entry.masked_payload is not None
        assert audit_entry.masked_payload.get("password") == "***REDACTED***"


class TestDedicatedPortalsAndDocumentDownloads:

    def test_comercial_portal_route_returns_200(self, api_test_client):
        res = api_test_client.get("/comercial")
        assert res.status_code == 200
        assert b"Portal Comercial" in res.data

    def test_operaciones_portal_route_returns_200(self, api_test_client):
        res = api_test_client.get("/operaciones")
        assert res.status_code == 200
        assert b"Portal de Operaciones" in res.data

    def test_download_commercial_proposal_document(self, api_test_client):
        res = api_test_client.get("/api/documents/download?doc_type=propuesta_comercial")
        assert res.status_code == 200
        assert res.data.startswith(b"PK\x03\x04")

    def test_download_bom_xlsx_document(self, api_test_client):
        res = api_test_client.get("/api/documents/download?doc_type=bom_xlsx")
        assert res.status_code == 200
        assert res.data.startswith(b"PK\x03\x04")
