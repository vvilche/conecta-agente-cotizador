# Summary of Changes — Remediation Pass (Milestone 1: `odoo_ecosystem`)

**Agent**: Worker 1 (`worker_m1`)  
**Date**: 2026-07-28  

The following changes were implemented across `src/odoo_ecosystem` to address the 4 edge-case issues identified in Challenger 1's empirical challenge report.

---

### 1. `src/odoo_ecosystem/mock_server.py` (`DomainEvaluator`)
- **Polish Prefix Domain Evaluation**:
  - Replaced the flawed `while True:` iterator loop in `DomainEvaluator.evaluate()` with an index-based recursive AST parser (`_eval_token()`).
  - Added a top-level loop (`while idx < len(tokens):`) that evaluates top-level sub-expressions (both simple tuples and operator trees) and combines them via logical `AND`.
  - Fixes evaluation of domains like `[('c', '=', 3), '|', ('a', '=', 999), ('b', '=', 2)]`.
- **Regex Injection Prevention (`ilike` / `like`)**:
  - Sanitized target search patterns using `re.escape(str(val))` before transforming Odoo wildcards (`%` to `.*` and `_` to `.`).
  - Prevents `re.error` regex syntax crashes on strings containing `[`, `(`, `*`, `+`, `\`, etc.
- **Many2one Unhashable List handling (`in` / `not in`)**:
  - Updated `_compare` for `in` and `not in` operators to check if `field_val` is a list or tuple (e.g. Many2one `[id, name]`).
  - Automatically unwraps `field_val[0]` (the integer ID) and tests membership against `val` without attempting unhashable list lookups in Python sets.
- **Type Mismatch Comparison Safety**:
  - Wrapped comparisons (`>`, `>=`, `<`, `<=`, `=`, `!=`) in `try...except TypeError` blocks to safely handle string vs number or invalid type comparisons.

---

### 2. `src/odoo_ecosystem/mock_server.py` (`MockOdooDB`)
- **Thread Lock Protection**:
  - Added `self._lock = threading.Lock()` to `MockOdooDB.__init__()`.
  - Protected all internal state operations (`search_read`, `create`, `write`, `unlink`, `read`) with `with self._lock:`.
  - Prevents ID counter collision race conditions and `RuntimeError: dictionary changed size during iteration` when readers and writers access the in-memory database concurrently.

---

### 3. `src/odoo_ecosystem/client.py` (`TokenBucketRateLimiter`)
- **Thread Lock Synchronization**:
  - Added `self._lock = threading.Lock()` to `TokenBucketRateLimiter.__init__()`.
  - Enclosed `self.tokens` refill calculations and token consumption inside `with self._lock:`.
  - Released lock prior to executing `time.sleep(sleep_time)` so sleeping threads do not block rate limit calculations for other threads.

---

### 4. `src/odoo_ecosystem/audit.py` (`DraftStager` & `AuditLogger`)
- **DraftStager Concurrency**:
  - Added `self._lock = threading.RLock()` to `DraftStager.__init__()`.
  - Wrapped `_load_drafts()`, `_save_drafts()`, `create_draft()`, `approve_draft()`, and `reject_draft()` with `with self._lock:`.
  - Protects `self.drafts` dictionary mutations and `staged_drafts.json` file writes under concurrent multi-threaded usage.
- **AuditLogger Concurrency**:
  - Added `self._lock = threading.Lock()` to `AuditLogger.__init__()`.
  - Wrapped `log_call()`, `get_entries_by_model()`, and `clear()` with `with self._lock:` for thread-safe JSONL appending and in-memory list updates.
