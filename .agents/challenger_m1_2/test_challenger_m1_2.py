"""
Empirical Challenge & Stress Test Harness for Challenger 2
Milestone 1: Odoo Core Connector & Models (`odoo_ecosystem`)
"""

import time
import threading
import random
import pytest
from pydantic import ValidationError

from odoo_ecosystem.client import (
    OdooClient,
    OdooConfig,
    TokenBucketRateLimiter,
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
    extract_m2o_id,
    extract_m2o_name,
)
from odoo_ecosystem.mock_server import MockOdooServer, FaultInjectionConfig
from odoo_ecosystem.audit import AuditLogger


# =====================================================================
# 1. RATE LIMITER STRESS TESTS
# =====================================================================

def test_rate_limiter_burst_capacity():
    """Verify that a burst of up to RPS capacity is served immediately without sleep."""
    limiter = TokenBucketRateLimiter(rps=10.0)
    start = time.monotonic()
    for _ in range(10):
        limiter.acquire()
    elapsed = time.monotonic() - start
    print(f"\n[Rate Limiter] Burst of 10 requests took {elapsed*1000:.2f} ms")
    assert elapsed < 0.05, f"Burst capacity failed: took {elapsed:.3f}s instead of <0.05s"


def test_rate_limiter_exhaustion_behavior():
    """Verify that request #11 after a 10-token burst experiences sleep delay of ~0.1s."""
    limiter = TokenBucketRateLimiter(rps=10.0)
    for _ in range(10):
        limiter.acquire()
    
    start = time.monotonic()
    limiter.acquire()  # Request #11
    elapsed = time.monotonic() - start
    print(f"[Rate Limiter] Request #11 sleep delay: {elapsed*1000:.2f} ms")
    assert 0.08 <= elapsed <= 0.15, f"Exhaustion behavior anomaly: sleep delay was {elapsed:.3f}s (expected ~0.10s)"


def test_rate_limiter_sustained_throughput():
    """Verify sustained throughput over 25 requests at 20 RPS (50ms per request after initial 20 burst)."""
    limiter = TokenBucketRateLimiter(rps=20.0)
    start = time.monotonic()
    for _ in range(25):
        limiter.acquire()
    elapsed = time.monotonic() - start
    print(f"[Rate Limiter] 25 requests at 20 RPS took {elapsed:.3f} s")
    # Initial 20 served instantly, remaining 5 require 5/20 = 0.25s
    assert 0.20 <= elapsed <= 0.35, f"Sustained throughput timing unexpected: {elapsed:.3f}s"


def test_rate_limiter_concurrency_race_condition():
    """Stress test multi-threaded access on TokenBucketRateLimiter to check thread-safety."""
    limiter = TokenBucketRateLimiter(rps=10.0)
    errors = []
    
    def worker(worker_id):
        try:
            for _ in range(5):
                limiter.acquire()
        except Exception as e:
            errors.append((worker_id, e))
            
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - start
    
    print(f"[Rate Limiter Concurrency] 5 threads x 5 acquires took {elapsed:.3f} s. Token balance: {limiter.tokens:.3f}")
    assert len(errors) == 0, f"Thread execution produced errors: {errors}"


def test_rate_limiter_zero_or_negative_rps():
    """Verify rate limiter behavior when RPS is <= 0."""
    limiter = TokenBucketRateLimiter(rps=0.0)
    start = time.monotonic()
    for _ in range(100):
        limiter.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05, f"Zero RPS hung or delayed execution: {elapsed:.3f}s"


# =====================================================================
# 2. FAULT INJECTION & EXPONENTIAL BACKOFF STRESS TESTS
# =====================================================================

class FlakyMockServer(MockOdooServer):
    """Mock server with configurable failure count before success."""
    def __init__(self, fail_count: int, error_type: str = "rate_limit"):
        super().__init__()
        self.fail_count = fail_count
        self.attempts = 0
        self.error_type = error_type

    def execute_kw(self, db, uid, password, model, method, args, kwargs=None):
        self.attempts += 1
        if self.attempts <= self.fail_count:
            if self.error_type == "rate_limit":
                raise RuntimeError("HTTP 429 Too Many Requests: Rate Limit Exceeded")
            elif self.error_type == "server_error":
                raise RuntimeError("Odoo Internal Server Error 500")
            elif self.error_type == "timeout":
                raise TimeoutError("Connection to Odoo timed out")
        return super().execute_kw(db, uid, password, model, method, args, kwargs)


def test_flaky_service_transient_retry_success():
    """Verify that transient failures (2 failures) are retried and succeed on attempt #3."""
    flaky_server = FlakyMockServer(fail_count=2, error_type="server_error")
    cfg = OdooConfig(max_retries=4)
    client = OdooClient(config=cfg, mock_server=flaky_server)
    
    start = time.monotonic()
    res = client.search_read("res.partner")
    elapsed = time.monotonic() - start
    
    print(f"[Fault Injection] Flaky service resolved on attempt {flaky_server.attempts} after {elapsed*1000:.2f} ms")
    assert flaky_server.attempts == 3
    assert isinstance(res, list)
    assert len(res) >= 2


def test_fault_injection_retries_exhaustion():
    """Verify that persistent transient failures raise OdooMaxRetriesExceededError after max_retries attempts."""
    flaky_server = FlakyMockServer(fail_count=10, error_type="rate_limit")
    cfg = OdooConfig(max_retries=3)
    audit = AuditLogger()
    client = OdooClient(config=cfg, audit_logger=audit, mock_server=flaky_server)
    
    start = time.monotonic()
    with pytest.raises(OdooMaxRetriesExceededError) as exc_info:
        client.search_read("res.partner")
    elapsed = time.monotonic() - start
    
    print(f"[Fault Injection] Exhausted retries after {elapsed*1000:.2f} ms. Error: {exc_info.value}")
    assert "Exceeded max retries (3)" in str(exc_info.value)
    assert flaky_server.attempts == 3
    # Check audit log entries created per attempt
    assert len(audit.memory_entries) == 3
    for entry in audit.memory_entries:
        assert entry.status in ("RATE_LIMITED", "SERVER_ERROR")


def test_fault_injection_fast_fail_on_auth():
    """Verify non-retryable authentication failure fast-fails on attempt 1 without backoff delays."""
    server = MockOdooServer()
    server.inject_error("search_read", "auth_failure")
    cfg = OdooConfig(max_retries=5)
    client = OdooClient(config=cfg, mock_server=server)
    
    start = time.monotonic()
    with pytest.raises(OdooAuthenticationError) as exc_info:
        client.search_read("res.partner")
    elapsed = time.monotonic() - start
    
    print(f"[Fault Injection] Auth fast-fail executed in {elapsed*1000:.2f} ms")
    assert elapsed < 0.05, f"Auth failure should not sleep or retry: took {elapsed:.3f}s"
    assert "Auth error" in str(exc_info.value) or "Authentication Failure" in str(exc_info.value)


def test_randomized_fault_injection_matrix():
    """Stress test 30 operations under 30% randomized fault injection."""
    random.seed(42)
    server = MockOdooServer()
    cfg = OdooConfig(max_retries=3)
    client = OdooClient(config=cfg, mock_server=server)
    
    success_count = 0
    failure_count = 0
    
    for i in range(30):
        # Randomly decide if this call will be faulty
        is_faulty = random.random() < 0.3
        if is_faulty:
            server.fault_config.simulate_server_error = True
        else:
            server.fault_config.simulate_server_error = False
            
        try:
            res = client.search_read("res.partner")
            success_count += 1
        except OdooMaxRetriesExceededError:
            failure_count += 1
            
    print(f"[Randomized Fault Matrix] 30 calls -> Successes: {success_count}, Max-Retry Failures: {failure_count}")
    assert success_count + failure_count == 30


# =====================================================================
# 3. PYDANTIC MODEL INVALID PAYLOAD REJECTION TESTS
# =====================================================================

def test_pydantic_invalid_enum_states():
    """Verify strict rejection of invalid enum states across models."""
    # 1. CrmLead type
    with pytest.raises((ValidationError, ValueError)) as exc:
        CrmLead(name="Test", type="invalid_type")
    assert "Invalid lead type" in str(exc.value)

    # 2. SaleOrder state
    with pytest.raises((ValidationError, ValueError)) as exc:
        SaleOrder(partner_id=1, state="invalid_state")
    assert "Invalid SaleOrder state" in str(exc.value)

    # 3. ProjectTask kanban_state
    with pytest.raises((ValidationError, ValueError)) as exc:
        ProjectTask(name="Task", project_id=1, kanban_state="super_done")
    assert "Invalid kanban_state" in str(exc.value)

    # 4. CrossoveredBudget state
    with pytest.raises((ValidationError, ValueError)) as exc:
        CrossoveredBudget(name="Budget", date_from="2026-01-01", date_to="2026-12-31", state="approved")
    assert "Invalid CrossoveredBudget state" in str(exc.value)

    # 5. AccountMove move_type
    with pytest.raises((ValidationError, ValueError)) as exc:
        AccountMove(move_type="customer_bill", partner_id=1)
    assert "Invalid move_type" in str(exc.value)

    # 6. AccountMove state
    with pytest.raises((ValidationError, ValueError)) as exc:
        AccountMove(move_type="out_invoice", partner_id=1, state="paid")
    assert "Invalid AccountMove state" in str(exc.value)

    # 7. AccountPayment payment_type
    with pytest.raises((ValidationError, ValueError)) as exc:
        AccountPayment(payment_type="transfer", partner_id=1, amount=100.0, date="2026-01-01")
    assert "Invalid payment_type" in str(exc.value)

    # 8. AccountPayment state
    with pytest.raises((ValidationError, ValueError)) as exc:
        AccountPayment(payment_type="inbound", partner_id=1, amount=100.0, date="2026-01-01", state="settled")
    assert "Invalid AccountPayment state" in str(exc.value)


def test_pydantic_wrong_type_fields():
    """Verify rejection of wrong field types in models."""
    # Required string missing/None
    with pytest.raises(ValidationError):
        ResPartner(name=None)

    # Required float given non-numeric string
    with pytest.raises(ValidationError):
        AccountPayment(payment_type="inbound", partner_id=1, amount="one_hundred", date="2026-01-01")

    # Required partner_id missing/None
    with pytest.raises(ValidationError):
        SaleOrder(partner_id=None)

    # Line item description missing
    with pytest.raises(ValidationError):
        SaleOrderLine(product_id=5, name=None)


def test_pydantic_malformed_dates_and_objects():
    """Verify handling of malformed objects and date structures."""
    # List/dict passed to scalar field expecting int/float
    with pytest.raises(ValidationError):
        ResPartner(name="Partner", credit_limit=[1, 2, 3])

    # Unparseable dict passed to date field
    with pytest.raises(ValidationError):
        CrossoveredBudget(name="B", date_from={"year": 2026}, date_to="2026-12-31")


def test_many2one_extract_helpers():
    """Verify behavior of extract_m2o_id and extract_m2o_name helpers."""
    assert extract_m2o_id([42, "Company Name"]) == 42
    assert extract_m2o_id((42, "Company Name")) == 42
    assert extract_m2o_id(42) == 42
    assert extract_m2o_id(None) is None
    assert extract_m2o_id([]) is None

    assert extract_m2o_name([42, "Company Name"]) == "Company Name"
    assert extract_m2o_name((42, "Company Name")) == "Company Name"
    assert extract_m2o_name(42) is None
    assert extract_m2o_name(None) is None


def test_odoo_base_model_null_and_false_conversions():
    """Verify from_odoo_dict converts Odoo False values to None, and to_odoo_dict formats properly."""
    raw_odoo_response = {
        "id": 10,
        "name": "Test Partner",
        "email": False,
        "phone": False,
        "country_id": [43, "Chile"],
        "credit_limit": 1000.0,
        "active": True
    }
    partner = ResPartner.from_odoo_dict(raw_odoo_response)
    assert partner.email is None
    assert partner.phone is None
    assert partner.country_id == [43, "Chile"]
    
    odoo_export = partner.to_odoo_dict()
    assert odoo_export["country_id"] == 43  # Many2one tuple extracted to ID for write/create
    assert odoo_export["name"] == "Test Partner"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
