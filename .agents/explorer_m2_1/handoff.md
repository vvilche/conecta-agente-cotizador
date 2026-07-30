# Handoff Report - Explorer 1 (Milestone 2: RAG & Historical Memory Engine)

## 1. Observation

1. **Workspace Inspection & Status**:
   - Milestone 1 is completed with clean Pydantic v2 models in `src/odoo_ecosystem/models.py`, `src/odoo_ecosystem/client.py`, `src/odoo_ecosystem/mock_server.py`, and `src/odoo_ecosystem/audit.py`.
   - `PROJECT.md` lines 27–30 defines contract interfaces for `rag_memory`:
     ```python
     ### rag_memory ↔ swarm_engine
     - HistoricalMemory.ingest_document(doc_type: str, content: dict) -> str
     - HistoricalMemory.get_few_shot_context(query: str, domain: str, top_k: int = 5) -> list[dict]
     ```
   - `pyproject.toml` lists dependencies including `pydantic>=2.5.0`, `pydantic-settings>=2.1.0`, `requests>=2.31.0`, `urllib3>=2.0.0`, `tenacity>=8.2.0`, `python-dotenv>=1.0.0`, `typing-extensions>=4.8.0`, and pytest plugins. No binary vector database or heavy C dependencies are included, requiring standard library / pure Python vector indexing for optimal performance and portability.

2. **Target Components for Milestone 2**:
   - `src/rag_memory/ingester.py`: Ingestion pipeline for historical tenders, won/lost proposals, historical price lists, and cost structures supporting JSON, CSV, Markdown, and TXT with structured Pydantic metadata.
   - `src/rag_memory/indexer.py`: Vector embeddings indexer and retriever (`VectorStore`) implementing fast in-memory BM25 + TF-IDF cosine similarity search, pre-retrieval metadata filtering, and JSON persistence (`.agents/rag_store.json`).
   - `src/rag_memory/few_shot.py`: Dynamic context engine (`FewShotEngine`) and `HistoricalMemory` facade providing past winning proposals, cost benchmarks, and prompt context formatting for AI swarm agents.

## 2. Logic Chain

1. **Document Ingestion Logic**:
   - Raw multi-format documents (JSON, CSV, Markdown, TXT) must be normalized into standard Pydantic models (`Document` and `DocumentChunk`).
   - Standardized metadata extraction ensures filtering attributes (`category`, `outcome`, `price`, `client`, `date`, `domain`, `tags`) are present on both the top-level document and all generated chunks.
   - Section-aware sliding window chunking ensures long documents are split into contextual passages (e.g. 500 chars with 100 char overlap) without breaking domain section headers.

2. **Vector Indexer & Retrieval Logic**:
   - Pure Python sparse vector implementation using BM25 Okapi ($k_1=1.5, b=0.75$) and TF-IDF Cosine Similarity guarantees zero external C dependencies, high speed, and cross-platform reliability on macOS/Linux.
   - Pre-retrieval metadata filtering reduces search search-space from $O(N)$ to $O(K)$, accelerating response times for filtered queries (e.g. `outcome=won` & `category=proposal`).
   - JSON persistence at `.agents/rag_store.json` provides simple, atomic state save and restore.

3. **Few-Shot Engine Logic**:
   - AI Swarm agents require concrete context (past winning proposals and cost benchmarks) to produce accurate RFQs, quotations, and budgets.
   - `FewShotEngine` queries `VectorStore` with metadata filters (`outcome=won`, `category=proposal` / `cost_structure`), formats excerpts, pricing parameters, and winning strategies into Markdown blocks, and injects them directly into prompt templates.
   - Exposing `HistoricalMemory` facade satisfies the exact interface defined in `PROJECT.md`.

## 3. Caveats

- **Vector Store Scale**: The pure-Python BM25 + TF-IDF cosine vector store is designed for tens of thousands of document chunks in-memory. For millions of documents, a vector database like FAISS or Qdrant would be needed, but for the scope of project tenders/proposals, in-memory BM25 + TF-IDF is optimal.
- **Language Tokenization**: Stop-word filtering and tokenizer handle both Spanish (dominant for Odoo/Chilean context) and English.

## 4. Conclusion

The technical design and architectural specifications for `src/rag_memory/ingester.py`, `src/rag_memory/indexer.py`, and `src/rag_memory/few_shot.py` are fully defined in `.agents/explorer_m2_1/analysis.md`. The design fulfills all requirements from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `.agents/orchestrator/plan.md`.

## 5. Verification Method

1. Inspect `.agents/explorer_m2_1/analysis.md` for complete technical details, code structures, math formulas, Pydantic schemas, and JSON persistence layouts.
2. Once implementation begins, run pytest:
   `pytest tests/test_rag_memory.py -v`
3. Verify JSON persistence file `.agents/rag_store.json` is created and valid.
