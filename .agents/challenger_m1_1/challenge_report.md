# Empirical Challenge Report — Odoo Ecosystem (`odoo_ecosystem`)

**Agent**: Challenger 1 (`challenger_m1_1`)  
**Milestone**: Milestone 1 (Odoo Core Connector & Models - `odoo_ecosystem`)  
**Date**: 2026-07-28  
**Verdict**: **VETO**  

---

## Executive Summary

An empirical challenge and stress-test evaluation of `odoo_ecosystem` was conducted, focusing on `DomainEvaluator`, `MockOdooDB`, `OdooClient`, `TokenBucketRateLimiter`, and `DraftStager`. While basic CRUD workflows and single-operator queries pass basic unit tests, deep stress testing and trace analysis revealed **multiple high-severity bugs and concurrency race conditions**. 

Most critically:
1. **DomainEvaluator Compound Expression Failure**: Domain filters containing logical operators (`|`, `&`) following a top-level condition (e.g. `[('c', '=', 3), '|', ('a', '=', 999), ('b', '=', 2)]`) incorrectly bypass operator evaluation, causing valid queries to evaluate incorrectly.
2. **Regex Injection Crash in `ilike`**: Search strings containing unescaped regex special characters (e.g. `[`, `(`, `*`, `+`, `\`) trigger uncaught `re.error` exceptions, crashing search requests with 500 errors.
3. **Unhashable Type Exception in `in` Queries**: Comparing Many2one list representations `[id, name]` against a Python `set` target raises `TypeError: unhashable type: 'list'`.
4. **Concurrency Flaws**: `MockOdooDB`, `TokenBucketRateLimiter`, and `DraftStager` lack thread locking mechanisms, resulting in ID collision races, `RuntimeError: dictionary changed size during iteration`, and JSON file corruption under concurrent workloads.

---

## Challenge Summary

- **Overall risk assessment**: **HIGH**
- **Verdict**: **VETO** (Requires fixes to `DomainEvaluator` logic/regex handling and thread synchronization in mock components before production release).

---

## Detailed Challenges

### [HIGH] Challenge 1: DomainEvaluator Fails to Process Polish Operators After Top-Level Tuples
- **Assumption challenged**: `DomainEvaluator.evaluate()` correctly parses standard Odoo Polish domain notation with mixed top-level tuples and compound operators.
- **Attack scenario**: Pass a domain where a logical operator appears after a preceding tuple, such as `[('c', '=', 3), '|', ('a', '=', 999), ('b', '=', 2)]` against record `{'a': 1, 'b': 2, 'c': 3}`.
- **Blast radius**: The `while True:` loop in `DomainEvaluator` hits `elif token in ("&", "|", "!"): pass` and skips consuming operands for `'|'`. It treats all subsequent tuples as implicit `AND` conditions. For record `{'a': 1, 'b': 2, 'c': 3}`, the expression evaluates to `False` instead of `True`.
- **Mitigation**: Refactor `DomainEvaluator` to construct a complete recursive AST parser or stack-based Polish notation evaluator that processes prefix operators consistently regardless of token offset.

### [HIGH] Challenge 2: Search Query Crash via Unescaped Regex Characters in `ilike`/`like`
- **Assumption challenged**: `DomainEvaluator._compare()` safely handles arbitrary text patterns in `ilike` and `like` search operators.
- **Attack scenario**: Execute `search_read` with a query containing regex special characters such as `[("name", "ilike", "COMASA [100%]")]` or `[("name", "ilike", "Transelec (Chile")]`.
- **Blast radius**: `pattern = str(val).replace("%", ".*").replace("_", ".")` passes unescaped regex syntax to `re.search()`, causing `re.error: unterminated character set` or invalid grouping errors. This crashes the server process with an unhandled 500 error.
- **Mitigation**: Apply `re.escape(str(val))` prior to converting `%` to `.*` and `_` to `.`.

### [MEDIUM] Challenge 3: Unhashable Type Crash When Testing Many2one Lists Against Set Targets
- **Assumption challenged**: `DomainEvaluator` gracefully compares Many2one list representations `[id, name]` with container targets.
- **Attack scenario**: Perform domain query `[("country_id", "in", {43, 99})]` against record `{"country_id": [43, "Chile"]}`.
- **Blast radius**: `DomainEvaluator._compare()` executes `field_val in val`. Checking if list `[43, "Chile"]` is in `set` `{43, 99}` raises `TypeError: unhashable type: 'list'`.
- **Mitigation**: Check `raw_id in val` or ensure `field_val` is converted to a hashable tuple before performing `set` lookup.

### [MEDIUM] Challenge 4: Race Conditions in `MockOdooDB`, `TokenBucketRateLimiter`, and `DraftStager`
- **Assumption challenged**: The mock harness and client components are thread-safe under concurrent multi-threaded usage.
- **Attack scenario**:
  1. Execute concurrent `create` operations from 50 parallel threads on `MockOdooDB`.
  2. Execute concurrent `search_read` and `create` operations simultaneously.
  3. Perform concurrent `create_draft` calls from multiple threads.
- **Blast radius**:
  1. `_get_next_id()` without locks causes ID collisions and overwritten records.
  2. Concurrent read/write triggers `RuntimeError: dictionary changed size during iteration`.
  3. `DraftStager._save_drafts()` overwrites `staged_drafts.json` without lock protection, corrupting staged data.
  4. `TokenBucketRateLimiter.acquire()` suffers from race conditions on `self.tokens` and `self.last_update`.
- **Mitigation**: Introduce `threading.Lock()` or `threading.RLock()` in `MockOdooDB`, `TokenBucketRateLimiter`, and `DraftStager`.

---

## Stress Test Results

| Test Scenario | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|
| Deep Negation (100 `!`) | Evaluates without error to `True` | Evaluates to `True` | **PASS** |
| Deep Binary Tree (Depth 200) | Evaluates without error | Evaluates correctly | **PASS** |
| Unbalanced Expression `['&', ('a','=',1)]` | Validates syntax or raises error | Returns `True` (silently ignores missing right operand) | **FAIL** |
| Positional Remaining Tokens `[('c', '=', 3), '\|', ...]` | Returns `True` | Returns `False` (skips `\|` via `pass`) | **FAIL** |
| Regex Injection in `ilike` (`"COMASA [100%]"`) | Escapes regex and matches string | Crashes with `re.error: unterminated character set` | **FAIL** |
| Unhashable Many2one List in Set `in` | Returns `True` by matching ID | Crashes with `TypeError: unhashable type: 'list'` | **FAIL** |
| Concurrent Write (50 threads x 20 recs) | 1,000 unique records created | Race conditions cause ID collisions without locks | **FAIL** |
| Concurrent Read/Write Iteration | Safe concurrent access | Crashes with `RuntimeError: dictionary changed size during iteration` | **FAIL** |
| Rate Limiter Thread Safety | Thread-safe token acquisition | Race conditions on `tokens` and `last_update` state | **FAIL** |
| Draft Stager Concurrent Creation | 200 drafts persisted cleanly | File write race conditions on JSON persistence | **FAIL** |

---

## Unchallenged Areas

- **Actual Odoo Server XML-RPC/JSON-RPC Live Network Integration**: Tested via `MockOdooServer` harness since external Odoo instance is offline.
- **Pydantic v2 Serialization Performance under 100k records**: Out of scope for unit harness depth limit.

---

## Final Verdict Rationale

**VERDICT: VETO**

The implementation of `odoo_ecosystem` demonstrates good structure and overall contract alignment (Pydantic v2 models, 0% auto-execution draft staging, credential masking, audit logging). However, **VETO** is issued due to critical edge-case flaws in `DomainEvaluator` and concurrency risks:
1. Correctness bug in compound Polish domain evaluation.
2. Unhandled exception crash on search queries with special characters (`ilike`).
3. Absence of thread-safety locks across `MockOdooDB`, `TokenBucketRateLimiter`, and `DraftStager`.

These issues must be remediated before Milestone 1 code can be approved.
