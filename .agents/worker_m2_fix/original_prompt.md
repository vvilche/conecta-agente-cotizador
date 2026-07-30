## 2026-07-28T08:22:54Z
You are Worker 1 (M2 Remediation Pass) operating in directory `.agents/worker_m2_fix/`.

Your task is to fix 3 specific issues in `src/rag_memory/indexer.py` identified by Reviewer 2, and add corresponding test coverage in `tests/test_rag_memory.py`:

1. **Import `Enum`**: In `src/rag_memory/indexer.py`, add `from enum import Enum` import at the top of the file to fix `NameError` in `_matches_filters()` when callers pass Enum instances.
2. **Thread Safety**: In `src/rag_memory/indexer.py`, initialize `self._lock = threading.Lock()` (or `RLock`) in `VectorStore.__init__()`. Acquire `self._lock` during store state modifications and reads (`add_document`, `add_chunk`, `search`, `save_to_json`, `load_from_json`).
3. **Atomic File Persistence**: In `src/rag_memory/indexer.py`, refactor `VectorStore.save_to_json()` to write JSON data to a temporary file (e.g. `filepath + ".tmp"` or via `tempfile`) and use `os.replace()` to atomically swap the file into place.
4. **Unit Tests**: Update `tests/test_rag_memory.py` to add explicit tests verifying:
   - Enum-based filter queries (e.g. passing `DocumentCategory.PROPOSAL` or `ProposalOutcome.WON` in `filters`).
   - Thread locking under concurrent reader and writer threads.
   - Atomic JSON persistence and clean replacement.
5. **Verification**: Execute `pytest tests/test_rag_memory.py -v` and `pytest -v` to confirm all tests pass cleanly.
6. **Handoff**: Write your report to `.agents/worker_m2_fix/handoff.md` summarizing changes made, test output, and file paths.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
