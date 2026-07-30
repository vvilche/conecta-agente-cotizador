"""
Odoo Ecosystem Client Module.
Supports XML-RPC, JSON-RPC, and REST protocols with rate limiting, tenacity retries,
audit log recording, and 0% auto-execution draft staging lifecycle.
"""

from typing import Any, Dict, List, Optional, Union
import time
import uuid
import logging
import threading
from xmlrpc.client import ServerProxy, Error as XmlRpcError
import requests
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from odoo_ecosystem.audit import AuditLogger, AuditLogEntry, DraftStager, mask_sensitive_data

logger = logging.getLogger(__name__)


class OdooConfig(BaseSettings):
    """Configuration settings for Odoo Connection."""
    url: str = Field(default="http://localhost:8069", description="Odoo Server Base URL")
    db: str = Field(default="odoo_db", description="Odoo Database Name")
    username: str = Field(default="admin", description="Odoo Username")
    password: str = Field(default="admin", description="Odoo Password or API Key")
    protocol: str = Field(default="xmlrpc", description="Protocol: xmlrpc | jsonrpc | rest")
    environment: str = Field(default="staging", description="Environment: staging | prod")
    timeout: int = Field(default=30, description="HTTP Request Timeout in seconds")
    max_retries: int = Field(default=3, description="Max Retry Attempts for Transient Errors")
    rate_limit_rps: float = Field(default=10.0, description="Max Requests Per Second")
    verify_ssl: bool = Field(default=True, description="Verify SSL Certificates")

    model_config = SettingsConfigDict(env_prefix="ODOO_", env_file=".env", extra="ignore")


class OdooClientError(Exception):
    """Base Exception for Odoo Ecosystem Client."""
    pass


class OdooAuthenticationError(OdooClientError):
    """Raised when authentication fails or credentials are invalid."""
    pass


class OdooConnectionError(OdooClientError):
    """Raised when network/socket connection fails."""
    pass


class OdooRPCError(OdooClientError):
    """Raised when Odoo returns a server-side RPC fault or error."""
    pass


class OdooDraftError(OdooClientError):
    """Raised when draft operations fail or missing VoBo approval."""
    pass


class OdooMaxRetriesExceededError(OdooClientError):
    """Raised when transient retries exhaust configured max_retries limit."""
    pass


class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter."""
    def __init__(self, rps: float):
        self.rps = rps
        self.capacity = rps
        self.tokens = rps
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        if self.rps <= 0:
            return
        sleep_time = 0.0
        with self._lock:
            now = time.monotonic()
            delta = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + delta * self.rps)
            if self.tokens < 1.0:
                sleep_time = (1.0 - self.tokens) / self.rps
                self.tokens = 0.0
            else:
                self.tokens -= 1.0

        if sleep_time > 0:
            time.sleep(sleep_time)


class OdooClient:
    """
    Unified Multi-Protocol Client Connector for Odoo ERP.
    Supports XML-RPC, JSON-RPC, REST, tenacity retries, rate limiting, and draft staging.
    """

    def __init__(
        self,
        config: Optional[OdooConfig] = None,
        audit_logger: Optional[AuditLogger] = None,
        mock_server: Optional[Any] = None
    ):
        self.config = config or OdooConfig()
        self.audit_logger = audit_logger or AuditLogger()
        self.mock_server = mock_server
        self.uid: Optional[int] = None
        self._rate_limiter = TokenBucketRateLimiter(self.config.rate_limit_rps)
        self.draft_stager = DraftStager()

    def authenticate(self) -> int:
        """Authenticate against Odoo and return UID."""
        self._rate_limiter.acquire()

        # If connected directly to mock_server
        if self.mock_server is not None:
            uid = self.mock_server.authenticate(
                self.config.db, self.config.username, self.config.password
            )
            if not uid or uid <= 0:
                raise OdooAuthenticationError(f"Authentication failed for user '{self.config.username}' on DB '{self.config.db}'")
            self.uid = uid
            return self.uid

        if self.config.protocol == "xmlrpc":
            common_url = f"{self.config.url.rstrip('/')}/xmlrpc/2/common"
            try:
                common = ServerProxy(common_url)
                uid = common.authenticate(
                    self.config.db, self.config.username, self.config.password, {}
                )
                if not uid or uid <= 0:
                    raise OdooAuthenticationError(f"XML-RPC Authentication failed for user '{self.config.username}' on DB '{self.config.db}'")
                self.uid = uid
                return self.uid
            except OdooAuthenticationError:
                raise
            except Exception as e:
                raise OdooAuthenticationError(f"XML-RPC Auth error: {str(e)}") from e

        elif self.config.protocol == "jsonrpc":
            json_url = f"{self.config.url.rstrip('/')}/jsonrpc"
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "common",
                    "method": "authenticate",
                    "args": [self.config.db, self.config.username, self.config.password, {}]
                },
                "id": int(time.time() * 1000)
            }
            try:
                resp = requests.post(json_url, json=payload, timeout=self.config.timeout, verify=self.config.verify_ssl)
                data = resp.json()
                if "error" in data:
                    raise OdooAuthenticationError(f"JSON-RPC Auth Error: {data['error']}")
                uid = data.get("result")
                if not uid or uid <= 0:
                    raise OdooAuthenticationError("Invalid credentials, returned invalid UID")
                self.uid = uid
                return self.uid
            except OdooAuthenticationError:
                raise
            except Exception as e:
                raise OdooAuthenticationError(f"JSON-RPC Auth failure: {str(e)}") from e

        elif self.config.protocol == "rest":
            rest_url = f"{self.config.url.rstrip('/')}/api/v1/auth/token"
            payload = {"db": self.config.db, "username": self.config.username, "password": self.config.password}
            try:
                resp = requests.post(rest_url, json=payload, timeout=self.config.timeout, verify=self.config.verify_ssl)
                data = resp.json()
                if resp.status_code != 200 or "error" in data:
                    raise OdooAuthenticationError(f"REST Auth failure: {data.get('error', resp.status_code)}")
                self.uid = data.get("result", {}).get("uid", 1)
                return self.uid
            except OdooAuthenticationError:
                raise
            except Exception as e:
                raise OdooAuthenticationError(f"REST Auth failure: {str(e)}") from e

        else:
            raise OdooClientError(f"Unsupported protocol: {self.config.protocol}")

    def execute_kw(
        self,
        model: str,
        method: str,
        args: List[Any],
        kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute method on Odoo model with rate limiting, retries, and audit logging."""
        if not self.uid:
            self.authenticate()

        kwargs = kwargs or {}

        # Retries loop with exponential backoff
        attempts = 0
        max_attempts = self.config.max_retries
        backoff_delay = 0.1
        last_exception = None

        while attempts < max_attempts:
            attempts += 1
            self._rate_limiter.acquire()
            req_id = str(uuid.uuid4())
            start_time = time.time()
            http_status = 200

            try:
                if self.mock_server is not None:
                    res = self.mock_server.execute_kw(
                        self.config.db, self.uid, self.config.password, model, method, args, kwargs
                    )
                elif self.config.protocol == "xmlrpc":
                    object_url = f"{self.config.url.rstrip('/')}/xmlrpc/2/object"
                    models_proxy = ServerProxy(object_url)
                    res = models_proxy.execute_kw(
                        self.config.db, self.uid, self.config.password, model, method, args, kwargs
                    )
                elif self.config.protocol == "jsonrpc":
                    json_url = f"{self.config.url.rstrip('/')}/jsonrpc"
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": {
                            "service": "object",
                            "method": "execute_kw",
                            "args": [self.config.db, self.uid, self.config.password, model, method, args, kwargs]
                        },
                        "id": int(time.time() * 1000)
                    }
                    resp = requests.post(json_url, json=payload, timeout=self.config.timeout, verify=self.config.verify_ssl)
                    http_status = resp.status_code
                    data = resp.json()
                    if "error" in data:
                        raise OdooRPCError(f"JSON-RPC Error: {data['error']}")
                    res = data.get("result")
                elif self.config.protocol == "rest":
                    rest_path = f"/api/v1/models/{model}"
                    url = f"{self.config.url.rstrip('/')}{rest_path}"
                    headers = {"Authorization": f"Bearer token_uid_{self.uid}"}
                    if method == "search_read":
                        domain = args[0] if len(args) > 0 else []
                        body = {"domain": domain, "fields": kwargs.get("fields")}
                        resp = requests.get(url, json=body, headers=headers, timeout=self.config.timeout)
                    elif method == "create":
                        body = args[0] if len(args) > 0 else {}
                        resp = requests.post(url, json=body, headers=headers, timeout=self.config.timeout)
                    else:
                        resp = requests.get(url, headers=headers, timeout=self.config.timeout)
                    http_status = resp.status_code
                    data = resp.json()
                    res = data.get("result")
                else:
                    raise OdooClientError(f"Unsupported protocol: {self.config.protocol}")

                duration_ms = (time.time() - start_time) * 1000
                self.audit_logger.log_call(AuditLogEntry(
                    request_id=req_id,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    protocol=self.config.protocol,
                    odoo_version="16.0",
                    endpoint=f"{self.config.url}/{self.config.protocol}",
                    model=model,
                    method=method,
                    domain=args[0] if args and isinstance(args[0], list) else None,
                    fields=kwargs.get("fields"),
                    payload_size_bytes=len(str(args) + str(kwargs)),
                    response_time_ms=duration_ms,
                    status="SUCCESS",
                    http_status_code=http_status,
                    user_agent_id="odoo_client"
                ))

                return res

            except (OdooAuthenticationError, ValueError) as auth_err:
                # Fast fail on authentication/access errors
                duration_ms = (time.time() - start_time) * 1000
                self.audit_logger.log_call(AuditLogEntry(
                    request_id=req_id,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    protocol=self.config.protocol,
                    odoo_version="16.0",
                    endpoint=f"{self.config.url}/{self.config.protocol}",
                    model=model,
                    method=method,
                    domain=args[0] if args and isinstance(args[0], list) else None,
                    fields=kwargs.get("fields"),
                    payload_size_bytes=len(str(args) + str(kwargs)),
                    response_time_ms=duration_ms,
                    status="AUTH_ERROR",
                    http_status_code=401,
                    user_agent_id="odoo_client",
                    error_details=str(auth_err)
                ))
                raise OdooAuthenticationError(f"Auth error: {str(auth_err)}") from auth_err

            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                err_str = str(exc)
                is_rate_limit = "429" in err_str or "Rate Limit" in err_str
                status_code = 429 if is_rate_limit else 500

                self.audit_logger.log_call(AuditLogEntry(
                    request_id=req_id,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    protocol=self.config.protocol,
                    odoo_version="16.0",
                    endpoint=f"{self.config.url}/{self.config.protocol}",
                    model=model,
                    method=method,
                    domain=args[0] if args and isinstance(args[0], list) else None,
                    fields=kwargs.get("fields"),
                    payload_size_bytes=len(str(args) + str(kwargs)),
                    response_time_ms=duration_ms,
                    status="RATE_LIMITED" if is_rate_limit else "SERVER_ERROR",
                    http_status_code=status_code,
                    user_agent_id="odoo_client",
                    error_details=err_str
                ))

                last_exception = exc
                if attempts < max_attempts:
                    logger.warning("Attempt %d/%d failed for execute_kw(%s, %s): %s. Retrying in %.2fs",
                                   attempts, max_attempts, model, method, err_str, backoff_delay)
                    time.sleep(backoff_delay)
                    backoff_delay *= 2.0
                else:
                    break

        raise OdooMaxRetriesExceededError(
            f"Exceeded max retries ({max_attempts}) for execute_kw({model}.{method}): {str(last_exception)}"
        ) from last_exception

    # ==========================================
    # REQUIRED INTERFACE CONTRACTS
    # ==========================================

    def search_read(
        self,
        model: str,
        domain: Optional[List[Any]] = None,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Required Interface Contract: Search & Read records from Odoo model.
        """
        domain = domain or []
        kwargs: Dict[str, Any] = {"offset": offset}
        if fields:
            kwargs["fields"] = fields
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order

        return self.execute_kw(model=model, method="search_read", args=[domain], kwargs=kwargs)

    def create_draft(self, model: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Required Interface Contract: Create staged draft payload (0% auto-execution rule).
        Does NOT write to production database.
        """
        draft_record = self.draft_stager.create_draft(
            agent_id="odoo_client_agent",
            model=model,
            operation_type="create",
            payload=values
        )
        return {
            "draft_id": draft_record.draft_id,
            "model": draft_record.target_model,
            "values": draft_record.payload,
            "status": "pending_vobo",
            "created_at": draft_record.created_at
        }

    def commit_draft(self, draft_id: str, approved_by: str) -> Dict[str, Any]:
        """
        Required Interface Contract: Execute database write strictly upon VoBo approval.
        """
        if not approved_by or not approved_by.strip():
            raise OdooDraftError(f"Commit draft failed: missing explicit approved_by signature for draft '{draft_id}'")

        try:
            draft_rec = self.draft_stager.approve_draft(draft_id, approved_by=approved_by, vobo_notes="Approved via VoBo")
        except KeyError as e:
            raise OdooDraftError(f"Draft ID '{draft_id}' not found") from e
        except ValueError as e:
            raise OdooDraftError(str(e)) from e

        # Execute write/create in Odoo database
        record_id = self.execute_kw(model=draft_rec.target_model, method="create", args=[draft_rec.payload])

        draft_rec.state = "COMMITTED"
        draft_rec.committed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        draft_rec.odoo_record_id = record_id
        self.draft_stager._save_drafts()

        return {
            "draft_id": draft_rec.draft_id,
            "status": "committed",
            "approved_by": approved_by,
            "record_id": record_id,
            "odoo_record_id": record_id,
            "committed_at": draft_rec.committed_at
        }

    # ==========================================
    # AUXILIARY CRUD METHODS
    # ==========================================

    def create(self, model: str, values: Dict[str, Any]) -> int:
        """Direct CRUD create (used after VoBo confirmation or staging)."""
        return self.execute_kw(model=model, method="create", args=[values])

    def write(self, model: str, ids: List[int], values: Dict[str, Any]) -> bool:
        """Direct CRUD write."""
        return self.execute_kw(model=model, method="write", args=[ids, values])

    def unlink(self, model: str, ids: List[int]) -> bool:
        """Direct CRUD delete."""
        return self.execute_kw(model=model, method="unlink", args=[ids])

    def read(self, model: str, ids: List[int], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Direct CRUD read."""
        kwargs = {"fields": fields} if fields else {}
        return self.execute_kw(model=model, method="read", args=[ids], kwargs=kwargs)
