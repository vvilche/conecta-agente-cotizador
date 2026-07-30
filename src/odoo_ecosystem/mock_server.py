"""
In-Memory Mock Odoo Server Harness for Multi-Protocol Testing.
Simulates Odoo 14, 15, 16, 17 across XML-RPC, JSON-RPC, and REST protocols with domain filtering
and controllable fault injection.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
import time
import re
import uuid
import logging
import threading

logger = logging.getLogger(__name__)


class OdooVersion:
    V14 = "14.0"
    V15 = "15.0"
    V16 = "16.0"
    V17 = "17.0"


@dataclass
class FaultInjectionConfig:
    """Controllable fault injection configuration for mock server testing."""
    simulate_rate_limit: bool = False
    simulate_auth_failure: bool = False
    simulate_network_timeout: bool = False
    timeout_delay_seconds: float = 0.5
    simulate_server_error: bool = False
    simulate_validation_error: bool = False
    faulty_methods: Dict[str, str] = field(default_factory=dict)  # method_name -> error_type


class DomainEvaluator:
    """Evaluates Odoo Polish notation domain filter tuples against dictionary records."""

    @classmethod
    def evaluate(cls, record: Dict[str, Any], domain: Optional[List[Any]]) -> bool:
        if not domain:
            return True

        tokens = list(domain)
        idx = 0

        def _eval_token() -> bool:
            nonlocal idx
            if idx >= len(tokens):
                return True

            token = tokens[idx]
            idx += 1

            if token == "&":
                left = _eval_token()
                right = _eval_token()
                return left and right
            elif token == "|":
                left = _eval_token()
                right = _eval_token()
                return left or right
            elif token == "!":
                sub = _eval_token()
                return not sub
            elif isinstance(token, (list, tuple)) and len(token) == 3:
                field_name, op, val = token
                return cls._compare(record.get(field_name), op, val)
            else:
                return True

        res = True
        while idx < len(tokens):
            sub_res = _eval_token()
            res = res and sub_res

        return res

    @classmethod
    def _compare(cls, field_val: Any, op: str, val: Any) -> bool:
        # Extract ID if field_val is Many2one tuple
        if isinstance(field_val, (list, tuple)) and len(field_val) > 0:
            raw_id = field_val[0]
        else:
            raw_id = field_val

        try:
            if op == "=" or op == "==":
                return field_val == val or raw_id == val
            elif op == "!=" or op == "<>":
                return field_val != val and raw_id != val
            elif op == ">":
                return field_val is not None and field_val > val
            elif op == ">=":
                return field_val is not None and field_val >= val
            elif op == "<":
                return field_val is not None and field_val < val
            elif op == "<=":
                return field_val is not None and field_val <= val
            elif op == "in":
                if isinstance(val, (list, tuple, set)):
                    if isinstance(field_val, (list, tuple)):
                        if len(field_val) > 0 and field_val[0] in val:
                            return True
                        try:
                            if tuple(field_val) in val:
                                return True
                        except TypeError:
                            pass
                        return False
                    else:
                        try:
                            return field_val in val or raw_id in val
                        except TypeError:
                            return raw_id in val
                return False
            elif op == "not in":
                if isinstance(val, (list, tuple, set)):
                    if isinstance(field_val, (list, tuple)):
                        if len(field_val) > 0 and field_val[0] in val:
                            return False
                        try:
                            if tuple(field_val) in val:
                                return False
                        except TypeError:
                            pass
                        return True
                    else:
                        try:
                            return field_val not in val and raw_id not in val
                        except TypeError:
                            return raw_id not in val
                return True
            elif op in ("ilike", "like", "=ilike", "=like"):
                if field_val is None:
                    return False
                str_val = str(field_val)
                pattern = re.escape(str(val)).replace(r"\%", ".*").replace(r"\_", ".")
                if "ilike" in op:
                    return bool(re.search(pattern, str_val, re.IGNORECASE))
                return bool(re.search(pattern, str_val))
        except TypeError:
            return False
        return True


class MockOdooDB:
    """In-memory seed database with full CRUD capabilities for 9 core Odoo models."""

    def __init__(self):
        self.tables: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self.auto_ids: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._seed_default_data()

    def _get_next_id(self, model: str) -> int:
        curr = self.auto_ids.get(model, 100)
        self.auto_ids[model] = curr + 1
        return curr

    def _seed_default_data(self):
        # Initialize tables
        models = [
            "res.partner", "crm.lead", "sale.order", "sale.order.line",
            "project.project", "project.task", "account.analytic.account",
            "crossovered.budget", "crossovered.budget.lines",
            "account.move", "account.move.line", "account.payment"
        ]
        for m in models:
            self.tables[m] = {}

        # 1. res.partner
        self.tables["res.partner"][1] = {
            "id": 1, "name": "Empresa Electrica COMASA S.A.", "is_company": True,
            "email": "contacto@comasa.cl", "phone": "+56221234567", "vat": "76111222-3",
            "street": "Av. Las Condes 1234", "city": "Santiago", "country_id": [43, "Chile"],
            "credit_limit": 5000000.0, "active": True
        }
        self.tables["res.partner"][2] = {
            "id": 2, "name": "Transelec S.A.", "is_company": True,
            "email": "contacto@transelec.cl", "phone": "+56229876543", "vat": "96555111-2",
            "street": "Orrego Luco 056", "city": "Santiago", "country_id": [43, "Chile"],
            "credit_limit": 10000000.0, "active": True
        }
        self.tables["res.partner"][3] = {
            "id": 3, "name": "Juan Perez", "is_company": False,
            "email": "jperez@comasa.cl", "phone": "+56999887766", "vat": "15444333-5",
            "street": "Providencia 456", "city": "Santiago", "country_id": [43, "Chile"],
            "credit_limit": 0.0, "active": True
        }

        # 2. crm.lead
        self.tables["crm.lead"][10] = {
            "id": 10, "name": "Licitación Mantenimiento Subestación 2026",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "email_from": "contacto@comasa.cl", "phone": "+56221234567",
            "expected_revenue": 150000.0, "probability": 80.0,
            "stage_id": [2, "Propuesta Enviada"], "user_id": [1, "Admin"],
            "description": "Licitación anual de mantenimiento preventivo y correctivo", "type": "opportunity"
        }
        self.tables["crm.lead"][11] = {
            "id": 11, "name": "Prospección Servicio SSCC",
            "partner_id": [2, "Transelec S.A."],
            "email_from": "contacto@transelec.cl", "phone": "+56229876543",
            "expected_revenue": 85000.0, "probability": 40.0,
            "stage_id": [1, "Nuevo"], "user_id": [1, "Admin"],
            "description": "Servicios complementarios de regulación de frecuencia", "type": "opportunity"
        }

        # 3. sale.order & sale.order.line
        self.tables["sale.order.line"][101] = {
            "id": 101, "order_id": [100, "SO001"], "product_id": [5, "Inspección Electromecánica"],
            "name": "Servicio de auditoría de aislamiento transformador",
            "product_uom_qty": 2.0, "price_unit": 25000.0, "price_subtotal": 50000.0, "price_total": 59500.0
        }
        self.tables["sale.order"][100] = {
            "id": 100, "name": "SO001", "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "date_order": "2026-07-01T10:00:00", "state": "draft",
            "amount_untaxed": 50000.0, "amount_tax": 9500.0, "amount_total": 59500.0,
            "order_line": [101], "analytic_account_id": [300, "CC-COMASA-001"]
        }
        self.tables["sale.order"][101] = {
            "id": 101, "name": "SO002", "partner_id": [2, "Transelec S.A."],
            "date_order": "2026-07-15T14:30:00", "state": "sale",
            "amount_untaxed": 120000.0, "amount_tax": 22800.0, "amount_total": 142800.0,
            "order_line": [], "analytic_account_id": [301, "CC-TRANSELEC-002"]
        }
        self.tables["sale.order"][102] = {
            "id": 102, "name": "SO003", "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "date_order": "2026-07-20T09:00:00", "state": "sale",
            "amount_untaxed": 45000.0, "amount_tax": 8550.0, "amount_total": 53550.0,
            "order_line": [], "analytic_account_id": [300, "CC-COMASA-001"]
        }

        # 4. account.analytic.account
        self.tables["account.analytic.account"][300] = {
            "id": 300, "name": "CC-COMASA-001", "code": "CC001",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "balance": 150000.0, "debit": 200000.0, "credit": 50000.0
        }
        self.tables["account.analytic.account"][301] = {
            "id": 301, "name": "CC-TRANSELEC-002", "code": "CC002",
            "partner_id": [2, "Transelec S.A."],
            "balance": 80000.0, "debit": 100000.0, "credit": 20000.0
        }

        # 5. project.project
        self.tables["project.project"][200] = {
            "id": 200, "name": "Proyecto Digitalización COMASA",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "user_id": [1, "Admin"], "analytic_account_id": [300, "CC-COMASA-001"],
            "privacy_visibility": "portal", "active": True,
            "date_start": "2026-01-01", "date": "2026-12-31"
        }

        # 6. project.task
        self.tables["project.task"][201] = {
            "id": 201, "name": "Auditoría SITR AT-SITR-1",
            "project_id": [200, "Proyecto Digitalización COMASA"],
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "user_id": [1, "Admin"], "stage_id": [1, "En Progreso"],
            "planned_hours": 40.0, "effective_hours": 15.0, "remaining_hours": 25.0,
            "kanban_state": "normal", "progress": 37.5, "description": "Verificación de cumplimiento telemetría CEN"
        }

        # 7. crossovered.budget & lines
        self.tables["crossovered.budget.lines"][401] = {
            "id": 401, "crossovered_budget_id": [400, "Presupuesto Operativo Anual 2026"],
            "analytic_account_id": [300, "CC-COMASA-001"], "general_budget_id": [1, "Mantenimiento"],
            "date_from": "2026-01-01", "date_to": "2026-12-31",
            "planned_amount": 500000.0, "practical_amount": 150000.0,
            "theoritical_amount": 250000.0, "percentage": 30.0
        }
        self.tables["crossovered.budget"][400] = {
            "id": 400, "name": "Presupuesto Operativo Anual 2026",
            "user_id": [1, "Admin"], "date_from": "2026-01-01", "date_to": "2026-12-31",
            "state": "validate", "crossovered_budget_line": [401]
        }

        # 8. account.move & account.move.line
        self.tables["account.move.line"][501] = {
            "id": 501, "move_id": [500, "INV/2026/0001"], "name": "Servicios Mantenimiento Subestación",
            "product_id": [10, "Servicio Mantenimiento"], "quantity": 1.0,
            "price_unit": 100000.0, "debit": 0.0, "credit": 100000.0, "price_subtotal": 100000.0,
            "analytic_account_id": [300, "CC-COMASA-001"]
        }
        self.tables["account.move"][500] = {
            "id": 500, "name": "INV/2026/0001", "ref": "PO-2026-99", "move_type": "out_invoice",
            "partner_id": [1, "Empresa Electrica COMASA S.A."], "invoice_date": "2026-07-20",
            "state": "posted", "amount_untaxed": 100000.0, "amount_tax": 19000.0, "amount_total": 119000.0,
            "payment_state": "not_paid", "invoice_line_ids": [501]
        }

        # 9. account.payment
        self.tables["account.payment"][600] = {
            "id": 600, "name": "PAY/2026/0001", "payment_type": "inbound", "partner_type": "customer",
            "partner_id": [1, "Empresa Electrica COMASA S.A."], "amount": 119000.0,
            "currency_id": [1, "CLP"], "date": "2026-07-25", "state": "posted",
            "ref": "Transferencia Banco de Chile 489201", "journal_id": [1, "Banco"]
        }

    def search_read(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            table = self.tables.get(model, {})
            matched = []
            for r_id, rec in table.items():
                if DomainEvaluator.evaluate(rec, domain):
                    matched.append(rec)

            # Slice
            matched = matched[offset:]
            if limit:
                matched = matched[:limit]

            # Filter fields
            if fields:
                out = []
                for rec in matched:
                    filtered_rec = {"id": rec["id"]}
                    for f in fields:
                        filtered_rec[f] = rec.get(f, False)
                    out.append(filtered_rec)
                return out
            return [dict(rec) for rec in matched]

    def create(self, model: str, vals: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[int, List[int]]:
        with self._lock:
            if model not in self.tables:
                self.tables[model] = {}

            if isinstance(vals, list):
                ids = []
                for item in vals:
                    new_id = self._get_next_id(model)
                    rec = dict(item)
                    rec["id"] = new_id
                    self.tables[model][new_id] = rec
                    ids.append(new_id)
                return ids
            else:
                new_id = self._get_next_id(model)
                rec = dict(vals)
                rec["id"] = new_id
                self.tables[model][new_id] = rec
                return new_id

    def write(self, model: str, ids: List[int], vals: Dict[str, Any]) -> bool:
        with self._lock:
            table = self.tables.get(model, {})
            for r_id in ids:
                if r_id in table:
                    table[r_id].update(vals)
            return True

    def unlink(self, model: str, ids: List[int]) -> bool:
        with self._lock:
            table = self.tables.get(model, {})
            for r_id in ids:
                table.pop(r_id, None)
            return True

    def read(self, model: str, ids: List[int], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self._lock:
            table = self.tables.get(model, {})
            results = []
            for r_id in ids:
                if r_id in table:
                    rec = table[r_id]
                    if fields:
                        filtered = {"id": r_id}
                        for f in fields:
                            filtered[f] = rec.get(f, False)
                        results.append(filtered)
                    else:
                        results.append(dict(rec))
            return results


class MockOdooServer:
    """Central mock server simulating XML-RPC, JSON-RPC, and REST protocols."""

    def __init__(self, version: str = OdooVersion.V16, fault_config: Optional[FaultInjectionConfig] = None):
        self.version = version
        self.db = MockOdooDB()
        self.fault_config = fault_config or FaultInjectionConfig()
        self.valid_credentials = {
            ("odoo_db", "admin", "admin"): 1,
            ("odoo_db", "user", "pass"): 2,
        }

    def inject_error(self, method: str, error_type: str):
        """Inject artificial fault for testing retry and error handling."""
        self.fault_config.faulty_methods[method] = error_type

    def _check_fault(self, method: str):
        if self.fault_config.simulate_rate_limit or self.fault_config.faulty_methods.get(method) == "rate_limit":
            raise RuntimeError("HTTP 429 Too Many Requests: Rate Limit Exceeded")
        if self.fault_config.simulate_auth_failure or self.fault_config.faulty_methods.get(method) == "auth_failure":
            raise ValueError("Odoo Authentication Failure: Invalid credentials")
        if self.fault_config.simulate_server_error or self.fault_config.faulty_methods.get(method) == "server_error":
            raise RuntimeError("Odoo Internal Server Error 500")

    def authenticate(self, db: str, login: str, password: str, env: Any = None) -> int:
        self._check_fault("authenticate")
        uid = self.valid_credentials.get((db, login, password))
        if uid:
            return uid
        return 0

    def execute_kw(self, db: str, uid: int, password: str, model: str, method: str, args: List[Any], kwargs: Optional[Dict[str, Any]] = None) -> Any:
        self._check_fault(method)

        if not uid or uid <= 0:
            raise ValueError("Access Denied: Invalid UID")

        kwargs = kwargs or {}

        if method == "search_read":
            domain = args[0] if len(args) > 0 else []
            return self.db.search_read(
                model=model,
                domain=domain,
                fields=kwargs.get("fields"),
                offset=kwargs.get("offset", 0),
                limit=kwargs.get("limit"),
                order=kwargs.get("order")
            )
        elif method == "create":
            vals = args[0] if len(args) > 0 else {}
            return self.db.create(model=model, vals=vals)
        elif method == "write":
            ids = args[0] if len(args) > 0 else []
            vals = args[1] if len(args) > 1 else {}
            return self.db.write(model=model, ids=ids, vals=vals)
        elif method == "unlink":
            ids = args[0] if len(args) > 0 else []
            return self.db.unlink(model=model, ids=ids)
        elif method == "read":
            ids = args[0] if len(args) > 0 else []
            fields = kwargs.get("fields")
            return self.db.read(model=model, ids=ids, fields=fields)
        else:
            raise NotImplementedError(f"Method {method} not implemented in MockOdooServer")

    def jsonrpc_dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handles JSON-RPC 2.0 requests."""
        req_id = payload.get("id", 1)
        params = payload.get("params", {})
        service = params.get("service")
        method = params.get("method")
        args = params.get("args", [])

        try:
            if service == "common" and method == "authenticate":
                db, login, password, env = args[0], args[1], args[2], args[3] if len(args) > 3 else {}
                uid = self.authenticate(db, login, password, env)
                if not uid:
                    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": 100, "message": "AccessDenied"}}
                return {"jsonrpc": "2.0", "id": req_id, "result": uid}
            elif service == "object" and method == "execute_kw":
                db, uid, password, model, exec_method, exec_args = args[0], args[1], args[2], args[3], args[4], args[5]
                kwargs = args[6] if len(args) > 6 else {}
                res = self.execute_kw(db, uid, password, model, exec_method, exec_args, kwargs)
                return {"jsonrpc": "2.0", "id": req_id, "result": res}
            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": 500, "message": str(e)}}

    def rest_dispatch(self, http_method: str, path: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handles REST API dispatching (Odoo 17)."""
        body = body or {}

        if path == "/api/v1/auth/token":
            db = body.get("db", "odoo_db")
            username = body.get("username", "admin")
            password = body.get("password", "")
            uid = self.authenticate(db, username, password)
            if uid:
                return {"status": 200, "result": {"token": f"bearer_token_uid_{uid}", "uid": uid}}
            return {"status": 401, "error": "Unauthorized"}

        match = re.match(r"^/api/v1/models/([^/]+)(?:/(\d+))?$", path)
        if match:
            model = match.group(1)
            rec_id = int(match.group(2)) if match.group(2) else None

            if http_method == "GET":
                if rec_id:
                    res = self.db.read(model, [rec_id])
                    return {"status": 200, "result": res[0] if res else None}
                else:
                    domain = body.get("domain", [])
                    fields = body.get("fields")
                    res = self.db.search_read(model, domain=domain, fields=fields)
                    return {"status": 200, "result": res}
            elif http_method == "POST":
                new_id = self.db.create(model, body)
                return {"status": 201, "result": {"id": new_id}}
            elif http_method == "PUT" and rec_id:
                self.db.write(model, [rec_id], body)
                return {"status": 200, "result": True}
            elif http_method == "DELETE" and rec_id:
                self.db.unlink(model, [rec_id])
                return {"status": 204, "result": True}

        return {"status": 404, "error": "Not Found"}
