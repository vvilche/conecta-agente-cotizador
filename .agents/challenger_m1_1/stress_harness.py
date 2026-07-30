"""
Empirical Stress Test Harness for odoo_ecosystem (Milestone 1).
Tests DomainEvaluator, MockOdooDB, OdooClient, RateLimiter, and DraftStager under edge conditions and rapid load.
"""

import sys
import os
import time
import math
import re
import uuid
import threading
import concurrent.futures
import tempfile
import traceback
from typing import List, Dict, Any

# Ensure src directory is on sys.path
sys.path.insert(0, os.path.abspath("src"))

from odoo_ecosystem.mock_server import MockOdooServer, MockOdooDB, DomainEvaluator, FaultInjectionConfig
from odoo_ecosystem.client import OdooClient, OdooConfig, TokenBucketRateLimiter, OdooDraftError, OdooMaxRetriesExceededError
from odoo_ecosystem.audit import AuditLogger, DraftStager, mask_sensitive_data, CredentialManager, AuditLogEntry
from odoo_ecosystem.models import ResPartner, CrmLead, SaleOrder, AccountMove


class StressTestRunner:
    def __init__(self):
        self.results = []
        self.failures = []

    def record(self, test_name: str, passed: bool, duration_ms: float, details: str = "", exception: Exception = None):
        res = {
            "test_name": test_name,
            "passed": passed,
            "duration_ms": round(duration_ms, 2),
            "details": details,
            "exception": str(exception) if exception else None
        }
        self.results.append(res)
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {test_name} ({res['duration_ms']} ms) - {details}")
        if not passed:
            self.failures.append(res)
            if exception:
                traceback.print_exc()

    def summarize(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        print("\n" + "="*60)
        print(f"STRESS TEST SUMMARY: Total={total}, Passed={passed}, Failed={failed}")
        print("="*60)
        return passed, failed


runner = StressTestRunner()

# =====================================================================
# CATEGORY 1: DomainEvaluator Edge Cases & Deep Polish Notation
# =====================================================================

def test_domain_evaluator_deep_negation():
    t0 = time.time()
    rec = {"active": True, "id": 1}
    # 100 nested ! operators
    domain = ["!"] * 100 + [("active", "=", True)]
    # 100 negations on True -> even number of negations = True
    try:
        res = DomainEvaluator.evaluate(rec, domain)
        dur = (time.time() - t0) * 1000
        runner.record("DomainEvaluator Deep Negation (100 '!')", res is True, dur, f"Result={res}")
    except Exception as e:
        runner.record("DomainEvaluator Deep Negation (100 '!')", False, (time.time() - t0) * 1000, f"Exception: {e}", e)

def test_domain_evaluator_deep_binary_tree():
    t0 = time.time()
    rec = {"val": 50}
    # Construct Polish tree of depth 200: & (& (& ... (val > 0, val < 100)))
    depth = 200
    domain = ["&"] * depth + [("val", ">", 0)] + [("val", "<", 100)] * (depth)
    try:
        res = DomainEvaluator.evaluate(rec, domain)
        dur = (time.time() - t0) * 1000
        runner.record(f"DomainEvaluator Deep Binary Tree (depth={depth})", res is True, dur, f"Result={res}")
    except Exception as e:
        runner.record(f"DomainEvaluator Deep Binary Tree (depth={depth})", False, (time.time() - t0) * 1000, f"Exception: {e}", e)

def test_domain_evaluator_unbalanced_expression():
    t0 = time.time()
    rec = {"name": "test"}
    # Unbalanced domain: operator '&' expects 2 operands but only 1 provided
    domain = ["&", ("name", "=", "test")]
    try:
        res = DomainEvaluator.evaluate(rec, domain)
        dur = (time.time() - t0) * 1000
        # Check if it crashes or handles gracefully
        runner.record("DomainEvaluator Unbalanced Expression ['&', leaf]", True, dur, f"Graceful handle, returned={res}")
    except Exception as e:
        runner.record("DomainEvaluator Unbalanced Expression ['&', leaf]", False, (time.time() - t0) * 1000, f"Crashed on unbalanced domain: {e}", e)

def test_domain_evaluator_regex_injection_ilike():
    t0 = time.time()
    rec = {"name": "COMASA S.A. [100%] (Chile)"}
    # Test regex special characters in search string for ilike
    patterns = [
        "COMASA S.A. [100%]",
        "COMASA (Chile)",
        "COMASA*",
        "COMASA+?",
        "[unclosed character set",
        "(unclosed group",
        "\\",
        "^COMASA$",
    ]
    all_passed = True
    details = []
    for pat in patterns:
        try:
            res = DomainEvaluator.evaluate(rec, [("name", "ilike", pat)])
            details.append(f"pat '{pat}' -> {res}")
        except Exception as e:
            all_passed = False
            details.append(f"pat '{pat}' -> CRASH: {e}")

    dur = (time.time() - t0) * 1000
    runner.record("DomainEvaluator Regex Injection in ilike", all_passed, dur, "; ".join(details))

def test_domain_evaluator_unhashable_types():
    t0 = time.time()
    # Many2one field stored as list [43, "Chile"]
    rec = {"country_id": [43, "Chile"], "tags": ["A", "B"]}
    try:
        # Check 'in' where val is a set or list
        res1 = DomainEvaluator.evaluate(rec, [("country_id", "in", [43, 99])])
        res2 = DomainEvaluator.evaluate(rec, [("country_id", "in", {43, 99})])
        dur = (time.time() - t0) * 1000
        passed = (res1 is True) and (res2 is True)
        runner.record("DomainEvaluator Unhashable Many2one list with 'in' operator", passed, dur, f"res1={res1}, res2={res2}")
    except Exception as e:
        runner.record("DomainEvaluator Unhashable Many2one list with 'in' operator", False, (time.time() - t0) * 1000, f"Exception: {e}", e)

def test_domain_evaluator_type_mismatch_comparisons():
    t0 = time.time()
    rec = {"credit_limit": 50000.0, "name": "Company"}
    # Compare string vs number, or None vs number
    tests = [
        [("name", ">", 100)],
        [("credit_limit", "<", "invalid_number")],
        [("non_existent", ">=", 0)],
        [("non_existent", "<=", 100)],
    ]
    all_passed = True
    details = []
    for dom in tests:
        try:
            res = DomainEvaluator.evaluate(rec, dom)
            details.append(f"{dom} -> {res}")
        except Exception as e:
            all_passed = False
            details.append(f"{dom} -> CRASH ({type(e).__name__}: {e})")

    dur = (time.time() - t0) * 1000
    runner.record("DomainEvaluator Type Mismatch Comparisons (string vs num, None vs num)", all_passed, dur, "; ".join(details))

def test_domain_evaluator_boundary_numbers():
    t0 = time.time()
    recs = [
        {"val": 0},
        {"val": -1},
        {"val": float("inf")},
        {"val": float("-inf")},
        {"val": float("nan")},
        {"val": 2**63 - 1},
        {"val": -(2**63)},
    ]
    all_passed = True
    details = []
    for r in recs:
        try:
            res_gt = DomainEvaluator.evaluate(r, [("val", ">", 0)])
            res_eq = DomainEvaluator.evaluate(r, [("val", "=", r["val"])])
            details.append(f"val={r['val']} -> eq:{res_eq}, gt:{res_gt}")
        except Exception as e:
            all_passed = False
            details.append(f"val={r['val']} -> CRASH: {e}")

    dur = (time.time() - t0) * 1000
    runner.record("DomainEvaluator Boundary Numbers (INF, NAN, Max/Min Int)", all_passed, dur, "; ".join(details[:3]))

def test_domain_evaluator_positional_remaining_tokens():
    t0 = time.time()
    rec = {"a": 1, "b": 2, "c": 3}
    # Domain: [('c', '=', 3), '|', ('a', '=', 999), ('b', '=', 2)]
    # First token ('c', '=', 3) is evaluated. Then remaining loop gets '|', ('a', '=', 999), ('b', '=', 2).
    # In standard Odoo logic, this means (c=3) AND (a=999 OR b=2) = True.
    domain = [("c", "=", 3), "|", ("a", "=", 999), ("b", "=", 2)]
    try:
        res = DomainEvaluator.evaluate(rec, domain)
        dur = (time.time() - t0) * 1000
        # If '|' was ignored by pass, it would evaluate c=3 AND a=999 (False) AND b=2 (True) -> False!
        # Let's see what res is!
        runner.record("DomainEvaluator Positional Remaining Tokens with '|'", res is True, dur, f"Result={res} (Expected True if '|' processed properly)")
    except Exception as e:
        runner.record("DomainEvaluator Positional Remaining Tokens with '|'", False, (time.time() - t0) * 1000, f"Exception: {e}", e)


# =====================================================================
# CATEGORY 2: MockOdooDB & RateLimiter Rapid Load & Concurrency
# =====================================================================

def test_mock_odb_concurrent_writes():
    t0 = time.time()
    db = MockOdooDB()
    num_threads = 50
    records_per_thread = 20
    created_ids = []
    lock = threading.Lock()

    def worker(thread_idx: int):
        local_ids = []
        for i in range(records_per_thread):
            rec_id = db.create("res.partner", {
                "name": f"Thread-{thread_idx}-Partner-{i}",
                "is_company": False,
                "email": f"t{thread_idx}_{i}@test.com"
            })
            local_ids.append(rec_id)
        with lock:
            created_ids.extend(local_ids)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    dur = (time.time() - t0) * 1000
    expected_count = num_threads * records_per_thread
    unique_ids = set(created_ids)
    passed = (len(created_ids) == expected_count) and (len(unique_ids) == expected_count)
    details = f"Total created={len(created_ids)}, Unique IDs={len(unique_ids)}, Expected={expected_count}"
    runner.record("MockOdooDB Concurrent Writes (50 threads x 20 records)", passed, dur, details)

def test_mock_odb_concurrent_read_write():
    t0 = time.time()
    db = MockOdooDB()
    errors = []
    stop_flag = threading.Event()

    def writer():
        for i in range(100):
            if stop_flag.is_set():
                break
            try:
                db.create("sale.order", {
                    "name": f"SO_CONC_{i}",
                    "partner_id": 1,
                    "amount_total": 1000.0 * i
                })
            except Exception as e:
                errors.append(f"Writer error: {e}")
            time.sleep(0.001)

    def reader():
        for i in range(100):
            if stop_flag.is_set():
                break
            try:
                res = db.search_read("sale.order", domain=[("amount_total", ">=", 0)])
            except Exception as e:
                errors.append(f"Reader error: {e}")
            time.sleep(0.001)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader), threading.Thread(target=reader)]
    for t in threads:
        t.start()
    time.sleep(0.3)
    stop_flag.set()
    for t in threads:
        t.join()

    dur = (time.time() - t0) * 1000
    passed = len(errors) == 0
    details = f"Errors count: {len(errors)}" + (f" ({errors[:2]})" if errors else "")
    runner.record("MockOdooDB Concurrent Read/Write Iteration Safety", passed, dur, details)

def test_rate_limiter_concurrency():
    t0 = time.time()
    limiter = TokenBucketRateLimiter(rps=100.0)
    num_threads = 20
    acquires_per_thread = 10
    errors = []

    def worker():
        for _ in range(acquires_per_thread):
            try:
                limiter.acquire()
            except Exception as e:
                errors.append(str(e))

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    dur = (time.time() - t0) * 1000
    passed = len(errors) == 0
    runner.record("TokenBucketRateLimiter Concurrency Under 20 Threads", passed, dur, f"Errors={len(errors)}")

def test_mock_odb_high_volume_scale():
    t0 = time.time()
    db = MockOdooDB()
    n_records = 5000
    # Seed 5000 records
    vals = [{"name": f"Partner_{i}", "credit_limit": float(i), "is_company": (i % 2 == 0)} for i in range(n_records)]
    t_seed_start = time.time()
    db.create("res.partner", vals)
    t_seed_dur = (time.time() - t_seed_start) * 1000

    # Search query
    t_search_start = time.time()
    res = db.search_read("res.partner", domain=[("&", ("is_company", "=", True), ("credit_limit", ">=", 2500.0))])
    t_search_dur = (time.time() - t_search_start) * 1000

    dur = (time.time() - t0) * 1000
    expected_matches = 2500 // 2 + (1 if 5000 % 2 == 0 else 0)
    passed = abs(len(res) - 1250) <= 2
    details = f"Seed time: {round(t_seed_dur, 2)}ms, Search time: {round(t_search_dur, 2)}ms for {n_records} recs (Matched {len(res)})"
    runner.record(f"MockOdooDB High Volume Search ({n_records} records)", passed, dur, details)


# =====================================================================
# CATEGORY 3: OdooClient & DraftStager Staging Lifecycle Under Load
# =====================================================================

def test_draft_stager_rapid_creations():
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "drafts.json")
        stager = DraftStager(storage_path=storage_path)

        n_drafts = 500
        for i in range(n_drafts):
            stager.create_draft(
                agent_id="test_agent",
                model="account.move",
                operation_type="create",
                payload={"name": f"INV/{i}", "amount_total": 100.0 + i}
            )

        dur = (time.time() - t0) * 1000
        file_size_kb = os.path.getsize(storage_path) / 1024.0
        passed = len(stager.drafts) == n_drafts
        details = f"Created {len(stager.drafts)} drafts in {round(dur, 2)}ms. Disk file size: {round(file_size_kb, 2)} KB"
        runner.record(f"DraftStager Rapid Creation ({n_drafts} drafts)", passed, dur, details)

def test_draft_stager_concurrent_creations():
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "drafts.json")
        stager = DraftStager(storage_path=storage_path)

        num_threads = 10
        drafts_per_thread = 20
        errors = []

        def worker(thread_idx: int):
            for i in range(drafts_per_thread):
                try:
                    stager.create_draft(
                        agent_id=f"agent_{thread_idx}",
                        model="sale.order",
                        operation_type="create",
                        payload={"name": f"SO_{thread_idx}_{i}"}
                    )
                except Exception as e:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        dur = (time.time() - t0) * 1000
        expected = num_threads * drafts_per_thread
        actual = len(stager.drafts)
        passed = actual == expected and len(errors) == 0
        details = f"Expected={expected}, Actual={actual}, Errors={len(errors)}"
        runner.record("DraftStager Concurrent Creation Under 10 Threads", passed, dur, details)

def test_draft_commit_edge_cases():
    t0 = time.time()
    mock_server = MockOdooServer()
    cfg = OdooConfig()
    client = OdooClient(config=cfg, mock_server=mock_server)

    # Create draft
    draft = client.create_draft("res.partner", {"name": "Draft Partner", "is_company": True})
    draft_id = draft["draft_id"]

    # 1. Commit with empty approval string -> should fail
    fail_empty_vobo = False
    try:
        client.commit_draft(draft_id, approved_by="")
    except OdooDraftError:
        fail_empty_vobo = True

    # 2. Commit valid
    commit_res = client.commit_draft(draft_id, approved_by="admin_user")
    rec_id = commit_res["record_id"]

    # 3. Commit duplicate (already committed draft) -> should fail
    fail_double_commit = False
    try:
        client.commit_draft(draft_id, approved_by="admin_user")
    except OdooDraftError:
        fail_double_commit = True

    # 4. Commit non-existent draft ID -> should fail
    fail_nonexistent = False
    try:
        client.commit_draft("draft_non_existent_12345", approved_by="admin_user")
    except OdooDraftError:
        fail_nonexistent = True

    dur = (time.time() - t0) * 1000
    passed = fail_empty_vobo and fail_double_commit and fail_nonexistent and (rec_id > 0)
    details = f"EmptyVoBoBlocked={fail_empty_vobo}, DoubleCommitBlocked={fail_double_commit}, NonExistentBlocked={fail_nonexistent}"
    runner.record("OdooClient Draft Staging Commit Edge Cases", passed, dur, details)

def test_audit_logger_high_volume():
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "odoo_api.jsonl")
        logger = AuditLogger(log_file_path=log_path)
        n_logs = 1000

        for i in range(n_logs):
            logger.log_call(AuditLogEntry(
                request_id=str(uuid.uuid4()),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                protocol="xmlrpc",
                odoo_version="16.0",
                endpoint="http://localhost:8069/xmlrpc/2/object",
                model="res.partner",
                method="search_read",
                domain=[("id", "=", i)],
                fields=["name"],
                payload_size_bytes=120,
                response_time_ms=2.5,
                status="SUCCESS",
                http_status_code=200,
                user_agent_id="stress_tester"
            ))

        dur = (time.time() - t0) * 1000
        passed = len(logger.memory_entries) == n_logs
        file_size_kb = os.path.getsize(log_path) / 1024.0
        details = f"Logged {n_logs} entries in {round(dur, 2)}ms. Log file size: {round(file_size_kb, 2)} KB"
        runner.record(f"AuditLogger High Volume Recording ({n_logs} entries)", passed, dur, details)


# =====================================================================
# MAIN RUNNER
# =====================================================================

if __name__ == "__main__":
    print("==========================================================")
    print("STARTING ODOO ECOSYSTEM EMPIRICAL STRESS TEST SUITE")
    print("==========================================================")

    # Category 1
    test_domain_evaluator_deep_negation()
    test_domain_evaluator_deep_binary_tree()
    test_domain_evaluator_unbalanced_expression()
    test_domain_evaluator_regex_injection_ilike()
    test_domain_evaluator_unhashable_types()
    test_domain_evaluator_type_mismatch_comparisons()
    test_domain_evaluator_boundary_numbers()
    test_domain_evaluator_positional_remaining_tokens()

    # Category 2
    test_mock_odb_concurrent_writes()
    test_mock_odb_concurrent_read_write()
    test_rate_limiter_concurrency()
    test_mock_odb_high_volume_scale()

    # Category 3
    test_draft_stager_rapid_creations()
    test_draft_stager_concurrent_creations()
    test_draft_commit_edge_cases()
    test_audit_logger_high_volume()

    passed, failed = runner.summarize()
    sys.exit(0 if failed == 0 else 1)
