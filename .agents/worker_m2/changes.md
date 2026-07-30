# Changes Log - Worker 1 (Milestone 2: RAG & Historical Memory Engine)

**Milestone**: Milestone 2 (`rag_memory`)  
**Date**: 2026-07-28  
**Worker**: Worker 1 (`worker_m2`)  

---

## Summary of Implementation

Implemented the complete **RAG & Historical Memory Engine (`rag_memory`)** package, including multi-format ingestion pipelines, Pydantic data models, in-memory BM25 + TF-IDF hybrid vector indexing, Spanish text normalization, metadata filtering, JSON persistence, Few-Shot dynamic prompt engine, and `HistoricalMemory` facade contract.

---

## Modified & Created Files

### 1. `src/rag_memory/ingester.py` (New File)
- **Data Models**:
  - `DocumentCategory` (Enum: `tender`, `proposal`, `price_list`, `cost_structure`, `other`).
  - `ProposalOutcome` (Enum: `won`, `lost`, `pending`, `n_a`).
  - `DocumentChunk` (Pydantic BaseModel, frozen): `chunk_id`, `doc_id`, `chunk_index`, `text`, `metadata`.
  - `Document` (Pydantic BaseModel): `doc_id`, `title`, `category`, `outcome`, `price`, `client`, `date`, `domain`, `tags`, `raw_content`, `metadata`, `chunks`, `created_at`.
- **Coercion Helpers**: `_coerce_category`, `_coerce_outcome` supporting Spanish/English aliases.
- **Chunking Engine**: `create_sliding_window_chunks` implementing hybrid section-aware sliding window chunking with metadata inheritance.
- **Format Parsers**:
  - `JSONIngester`: Parses JSON dicts/files, flattens non-metadata attributes.
  - `CSVIngester`: Parses CSV tables with alias mapping (`item`, `descripcion`, `precio`, `costo`, `cliente`, `resultado`, `fecha`, `categoria`, `dominio`).
  - `MarkdownIngester`: Parses Markdown with YAML frontmatter (`--- ... ---`) and header splits (`#`, `##`).
  - `TextIngester`: Parses plain text with regex header auto-detection (`Cliente:`, `Resultado:`, `Monto:`).
- **Unified Wrapper**: `DocumentIngester` exposing `ingest_dict`, `ingest_json`, `ingest_csv`, `ingest_markdown`, `ingest_text`, `ingest_file`.

### 2. `src/rag_memory/indexer.py` (New File)
- **Models**: `SearchResult` (`chunk_id`, `doc_id`, `text`, `score`, `bm25_score`, `cosine_score`, `metadata`).
- **Text Normalization**: `strip_diacritics` (NFD unicodedata normalization) and `tokenize` (lowercasing, stop-word removal for Spanish & English, bi-gram extraction for technical terms like `estudio_edac`, `crossovered_budget`).
- **VectorStore**:
  - Pure-Python sparse vector indexing combining Okapi BM25 ($k_1=1.5, b=0.75$) and TF-IDF Cosine Similarity with weight parameter $\alpha=0.6$.
  - Pre-retrieval metadata filtering (`category`, `outcome`, `client`, `domain`, `min_price`, `max_price`, `date_start`, `date_end`, `tags`).
  - Score normalization to range $[0.0, 1.0]$.
  - JSON persistence via `save_to_json()` and `load_from_json()` defaulting to `.agents/rag_store.json`.

### 3. `src/rag_memory/few_shot.py` (New File)
- **FewShotEngine**:
  - `get_winning_proposal_examples(query, domain, top_k)`: Queries vector store for won proposals matching query and domain filters. Includes fallback logic.
  - `get_cost_benchmarks(query, domain, top_k)`: Queries vector store for cost structure and price list items.
  - `build_few_shot_prompt(task_type, query, domain, top_k)`: Assembles formatted Markdown prompt block ready for injection into Swarm Agent prompts.
- **HistoricalMemory Facade**:
  - Satisfies `PROJECT.md` interface contract:
    - `ingest_document(doc_type: str, content: dict) -> str`
    - `get_few_shot_context(query: str, domain: str = None, top_k: int = 5) -> list[dict]`

### 4. `src/rag_memory/__init__.py` (New File)
- Exports all public classes and helper functions for external consumption by `swarm_engine` and tests.

### 5. `tests/conftest.py` (Updated File)
- Retained all existing Milestone 1 fixtures (`mock_odoo_server`, `audit_logger`, `odoo_client_*`, `seed_payloads`).
- Extended with Milestone 2 fixtures:
  - `sample_tenders_dataset` (4 Chilean electrical tender specifications).
  - `historical_proposals_dataset` (6 won/lost/pending historical proposals with pricing details).
  - `pricing_matrices_dataset` (CSV cost benchmarks).
  - `temp_rag_store` (isolated temporary JSON file path).
  - `historical_memory_instance` (pre-populated facade instance).

### 6. `tests/test_rag_memory.py` (New File)
- Implemented 32 unit and integration tests across 7 test classes:
  - `TestDocumentIngester` (7 tests)
  - `TestVectorIndexer` (6 tests)
  - `TestMetadataFiltering` (6 tests)
  - `TestTopKPrecisionAndRanking` (3 tests)
  - `TestFewShotEngine` (3 tests)
  - `TestHistoricalMemoryFacade` (1 test)
  - `TestEdgeCasesAndFaultTolerance` (6 tests)

---

## Verification & Quality Assurance

- Code layout complies strictly with `PROJECT.md` code structure.
- No binary C-dependencies introduced.
- Genuine implementation with no hardcoded mocks or dummy values.
