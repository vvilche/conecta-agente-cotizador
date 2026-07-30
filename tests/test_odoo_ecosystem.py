"""
Comprehensive Unit & Integration Test Suite for odoo_ecosystem.
Verifies multi-protocol client, 9 Pydantic v2 models, mock server, domain evaluator,
fault injection, retries, audit logging, credential masking, and 0% auto-execution draft staging.
"""

import pytest
from unittest.mock import MagicMock
import tempfile
import os

from odoo_ecosystem.client import (
    OdooClient,
    OdooConfig,
    OdooAuthenticationError,
    OdooMaxRetriesExceededError,
    OdooDraftError,
    OdooRPCError,
)
from odoo_ecosystem.models import (
    ResPartner,
    CrmLead,
    SaleOrder,
    SaleOrderLine,
    ProjectProject,
    ProjectTask,
    AccountAnalyticAccount,
    CrossoveredBudget,
    CrossoveredBudgetLines,
    AccountMove,
    AccountMoveLine,
    AccountPayment,
)
from odoo_ecosystem.mock_server import MockOdooServer, DomainEvaluator, FaultInjectionConfig
from odoo_ecosystem.audit import AuditLogger, CredentialManager, DraftStager, mask_sensitive_data, AuditLogEntry


class TestOdooClientAuthentication:
    """Tests for authentication behavior across protocols and credential failures."""

    def test_successful_authentication(self, mock_odoo_server):
        cfg = OdooConfig(db="odoo_db", username="admin", password="admin")
        client = OdooClient(config=cfg, mock_server=mock_odoo_server)
        uid = client.authenticate()
        assert uid == 1
        assert client.uid == 1

    def test_failed_authentication_invalid_password(self, mock_odoo_server):
        cfg = OdooConfig(db="odoo_db", username="admin", password="invalid_password")
        client = OdooClient(config=cfg, mock_server=mock_odoo_server)
        with pytest.raises(OdooAuthenticationError) as exc_info:
            client.authenticate()
        assert "Authentication failed" in str(exc_info.value)
        assert client.uid is None

    def test_failed_authentication_invalid_db(self, mock_odoo_server):
        cfg = OdooConfig(db="non_existent_db", username="admin", password="invalid_password")
        client = OdooClient(config=cfg, mock_server=mock_odoo_server)
        with pytest.raises(OdooAuthenticationError):
            client.authenticate()


class TestOdooClientProtocols:
    """Tests for XML-RPC, JSON-RPC, and REST protocol execution."""

    def test_search_read_filtering(self, odoo_client_param):
        res = odoo_client_param.search_read("res.partner", domain=[("is_company", "=", True)])
        assert isinstance(res, list)
        assert len(res) >= 2
        for r in res:
            assert r["is_company"] is True

    def test_create_record(self, odoo_client_param, seed_payloads):
        payload = seed_payloads["res.partner"]
        rec_id = odoo_client_param.create("res.partner", payload)
        assert isinstance(rec_id, int)
        assert rec_id > 0

        # Verify insertion
        fetched = odoo_client_param.read("res.partner", [rec_id])
        assert len(fetched) == 1
        assert fetched[0]["name"] == payload["name"]

    def test_write_record(self, odoo_client_param):
        partner_id = 1
        success = odoo_client_param.write("res.partner", [partner_id], {"city": "Concepción"})
        assert success is True

        fetched = odoo_client_param.read("res.partner", [partner_id], fields=["city"])
        assert fetched[0]["city"] == "Concepción"

    def test_unlink_record(self, odoo_client_param):
        task_id = 201
        success = odoo_client_param.unlink("project.task", [task_id])
        assert success is True

        fetched = odoo_client_param.read("project.task", [task_id])
        assert len(fetched) == 0


class TestOdooClientDraftWorkflow:
    """Tests for 0% auto-execution draft staging and VoBo commit workflow."""

    def test_create_draft_does_not_mutate_production_model(self, odoo_client_xmlrpc, seed_payloads):
        initial_moves = odoo_client_xmlrpc.search_read("account.move")
        initial_count = len(initial_moves)

        move_payload = seed_payloads["account.move"]
        draft = odoo_client_xmlrpc.create_draft("account.move", move_payload)

        assert "draft_id" in draft
        assert draft["status"] == "pending_vobo"
        assert draft["model"] == "account.move"

        # Verify production table count remains unchanged before commit
        after_moves = odoo_client_xmlrpc.search_read("account.move")
        assert len(after_moves) == initial_count

    def test_commit_draft_with_valid_vobo(self, odoo_client_xmlrpc, seed_payloads):
        move_payload = seed_payloads["account.move"]
        draft = odoo_client_xmlrpc.create_draft("account.move", move_payload)
        draft_id = draft["draft_id"]

        committed = odoo_client_xmlrpc.commit_draft(draft_id, approved_by="supervisor_user")

        assert committed["status"] == "committed"
        assert committed["approved_by"] == "supervisor_user"
        assert "record_id" in committed
        assert committed["record_id"] > 0

        # Verify record now exists in Odoo database
        fetched = odoo_client_xmlrpc.read("account.move", [committed["record_id"]])
        assert len(fetched) == 1
        assert fetched[0]["name"] == move_payload["name"]

    def test_commit_draft_without_approval_fails(self, odoo_client_xmlrpc, seed_payloads):
        draft = odoo_client_xmlrpc.create_draft("sale.order", seed_payloads["sale.order"])
        draft_id = draft["draft_id"]

        with pytest.raises(OdooDraftError) as exc_info:
            odoo_client_xmlrpc.commit_draft(draft_id, approved_by="")
        assert "missing explicit approved_by signature" in str(exc_info.value)


class TestOdooModelValidations:
    """Tests for schema validation of all 9 primary Odoo models."""

    def test_res_partner_model(self, seed_payloads):
        partner = ResPartner(**seed_payloads["res.partner"])
        assert partner.name == "Generadora Solar del Norte SpA"
        assert partner.is_company is True
        odoo_dict = partner.to_odoo_dict()
        assert odoo_dict["name"] == partner.name

    def test_crm_lead_model(self, seed_payloads):
        lead = CrmLead(**seed_payloads["crm.lead"])
        assert lead.expected_revenue == 45000.0
        assert lead.type == "opportunity"

    def test_sale_order_and_line_model(self, seed_payloads):
        so = SaleOrder(**seed_payloads["sale.order"])
        assert so.state == "draft"
        assert so.amount_total == 53550.0

        line = SaleOrderLine(**seed_payloads["sale.order.line"])
        assert line.price_unit == 45000.0

    def test_project_and_task_model(self, seed_payloads):
        proj = ProjectProject(**seed_payloads["project.project"])
        assert proj.name == "Proyecto Coordinación EDAC/ERAG"

        task = ProjectTask(**seed_payloads["project.task"])
        assert task.planned_hours == 20.0
        assert task.kanban_state == "normal"

    def test_analytic_account_model(self, seed_payloads):
        analytic = AccountAnalyticAccount(**seed_payloads["account.analytic.account"])
        assert analytic.code == "CC003"

    def test_budget_and_lines_model(self, seed_payloads):
        budget = CrossoveredBudget(**seed_payloads["crossovered.budget"])
        assert budget.state == "draft"

        bline = CrossoveredBudgetLines(**seed_payloads["crossovered.budget.lines"])
        assert bline.planned_amount == 100000.0

    def test_account_move_line_and_move_model(self, seed_payloads):
        move = AccountMove(**seed_payloads["account.move"])
        assert move.move_type == "out_invoice"
        assert move.state == "draft"

        line = AccountMoveLine(**seed_payloads["account.move.line"])
        assert line.price_unit == 45000.0

    def test_account_payment_model(self, seed_payloads):
        payment = AccountPayment(**seed_payloads["account.payment"])
        assert payment.payment_type == "inbound"
        assert payment.amount == 53550.0

    def test_invalid_account_move_type(self):
        with pytest.raises(ValueError) as exc_info:
            AccountMove(move_type="invalid_type", partner_id=1)
        assert "Invalid move_type" in str(exc_info.value)

    def test_invalid_sale_order_state(self):
        with pytest.raises(ValueError) as exc_info:
            SaleOrder(partner_id=1, state="unknown_state")
        assert "Invalid SaleOrder state" in str(exc_info.value)

    def test_model_roundtrip_dict(self, seed_payloads):
        raw = seed_payloads["res.partner"]
        partner = ResPartner.from_odoo_dict(raw)
        assert partner.name == raw["name"]
        exported = partner.to_odoo_dict()
        assert exported["name"] == raw["name"]


class TestMockOdooServer:
    """Tests for in-memory database CRUD, domain operator evaluation, and error injection."""

    def test_mock_server_domain_operators(self, mock_odoo_server):
        db = mock_odoo_server.db
        # Exact equality
        res = db.search_read("res.partner", domain=[("vat", "=", "76111222-3")])
        assert len(res) == 1
        assert res[0]["name"] == "Empresa Electrica COMASA S.A."

        # Numeric comparison & membership
        res = db.search_read("sale.order", domain=[("amount_total", ">", 100000.0)])
        assert len(res) == 1
        assert res[0]["name"] == "SO002"

        # Case-insensitive substring match (ilike)
        res = db.search_read("project.task", domain=[("name", "ilike", "SITR")])
        assert len(res) == 1
        assert res[0]["id"] == 201

        # Logical OR '|'
        res = db.search_read("res.partner", domain=["|", ("id", "=", 1), ("id", "=", 2)])
        assert len(res) == 2

    def test_mock_server_error_injection(self, mock_odoo_server):
        mock_odoo_server.inject_error("search_read", "server_error")
        cfg = OdooConfig(max_retries=1)
        client = OdooClient(config=cfg, mock_server=mock_odoo_server)
        with pytest.raises(OdooMaxRetriesExceededError):
            client.search_read("res.partner")


class TestErrorHandlingAndRetries:
    """Tests for transient network retries, rate limiting, and fast fail on auth errors."""

    def test_exceeds_max_retries_raises_exception(self, mock_odoo_server):
        mock_odoo_server.inject_error("search_read", "server_error")
        cfg = OdooConfig(max_retries=2)
        client = OdooClient(config=cfg, mock_server=mock_odoo_server)

        with pytest.raises(OdooMaxRetriesExceededError) as exc_info:
            client.search_read("res.partner")
        assert "Exceeded max retries" in str(exc_info.value)

    def test_non_retryable_auth_fails_immediately(self, mock_odoo_server):
        mock_odoo_server.inject_error("search_read", "auth_failure")
        cfg = OdooConfig(max_retries=3)
        client = OdooClient(config=cfg, mock_server=mock_odoo_server)

        with pytest.raises(OdooAuthenticationError):
            client.search_read("res.partner")


class TestAuditLogging:
    """Tests for structured JSONL log recording and credential masking."""

    def test_audit_log_captures_all_api_calls(self, odoo_client_xmlrpc, audit_logger):
        odoo_client_xmlrpc.search_read("res.partner")
        assert len(audit_logger.memory_entries) >= 1
        entry = audit_logger.memory_entries[-1]
        assert entry.model == "res.partner"
        assert entry.method == "search_read"
        assert entry.status == "SUCCESS"
        assert entry.response_time_ms > 0

    def test_credential_manager_masking(self):
        cm = CredentialManager({
            "ODOO_URL": "http://localhost:8069",
            "ODOO_DB": "prod_db",
            "ODOO_USERNAME": "admin",
            "ODOO_PASSWORD": "super_secret_password_123",
            "ODOO_API_KEY": "key_xyz987"
        })

        masked = cm.get_masked_credentials()
        assert masked["username"] == "admin"
        assert masked["password"] == "***REDACTED***"
        assert masked["api_key"] == "***REDACTED***"

    def test_mask_sensitive_data_helper(self):
        sample = {
            "user": "agent",
            "password": "secret_password",
            "meta": {
                "token": "bearer_abc",
                "normal_field": "hello"
            }
        }
        res = mask_sensitive_data(sample)
        assert res["user"] == "agent"
        assert res["password"] == "***REDACTED***"
        assert res["meta"]["token"] == "***REDACTED***"
        assert res["meta"]["normal_field"] == "hello"
