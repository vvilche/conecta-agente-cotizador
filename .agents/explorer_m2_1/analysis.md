# Technical Analysis & Architecture Specification: RAG & Historical Memory Engine (`rag_memory`)

**Milestone**: Milestone 2  
**Target Package**: `src/rag_memory`  
**Author**: Explorer 1 (`explorer_m2_1`)  
**Date**: 2026-07-28  

---

## Executive Summary

The **RAG & Historical Memory Engine (`rag_memory`)** serves as the collective knowledge backbone for the **Sistema Agenticio Inteligente Ecosistémico para Odoo ERP**. It provides fast document ingestion, multi-format parsing, structured metadata tagging, hybrid vector retrieval (TF-IDF + BM25 + Cosine Similarity with metadata filtering), and dynamic few-shot prompt construction for the 6 specialized AI Swarm Agents.

This document specifies the end-to-end architecture, data schemas, algorithmic specifications, persistence mechanics, and code structure for:
1. `src/rag_memory/ingester.py` (Document Ingestion Pipeline)
2. `src/rag_memory/indexer.py` (VectorStore Embeddings & Retrieval Engine)
3. `src/rag_memory/few_shot.py` (FewShotEngine & HistoricalMemory Contract)

---

## 1. High-Level System Architecture

```
[ Unstructured / Structured Data Sources ]
  - JSON Tenders & Proposals
  - CSV Price Lists & Budgets
  - Markdown Technical Specifications
  - TXT Historical Bids & RFQs
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                 src/rag_memory/ingester.py                 │
│  - Multi-Format Parsers (JSON, CSV, MD, TXT)                │
│  - Pydantic v2 Document & Chunk Schema Normalization       │
│  - Metadata Extraction (category, outcome, price, etc.)     │
│  - Sliding Window & Section-Based Chunking Engine           │
└──────────────────────────────┬──────────────────────────────┘
                               │ Document / DocumentChunk Objects
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 src/rag_memory/indexer.py                  │
│  - In-Memory VectorStore                                    │
│  - Spanish/English Tokenizer & Normalizer                   │
│  - Hybrid Retrieval Engine (BM25 + TF-IDF Cosine Sim)       │
│  - Pre-Retrieval Metadata Filter (category, outcome, domain) │
│  - JSON Persistence (.agents/rag_store.json)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ SearchResult Hits
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                src/rag_memory/few_shot.py                  │
│  - FewShotEngine                                            │
│  - HistoricalMemory Facade Contract                         │
│  - Winning Proposals & Cost Benchmark Filtering             │
│  - Few-Shot Context Prompt Builder for Swarm Agents         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Pipeline Specification (`src/rag_memory/ingester.py`)

### 2.1 Pydantic Data Models

```python
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime

class DocumentCategory(str, Enum):
    TENDER = "tender"
    PROPOSAL = "proposal"
    PRICE_LIST = "price_list"
    COST_STRUCTURE = "cost_structure"
    OTHER = "other"

class ProposalOutcome(str, Enum):
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    NA = "n_a"

class DocumentChunk(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Document(BaseModel):
    doc_id: str
    title: str
    category: DocumentCategory = DocumentCategory.OTHER
    outcome: ProposalOutcome = ProposalOutcome.NA
    price: Optional[float] = None
    client: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    domain: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    raw_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunks: List[DocumentChunk] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

### 2.2 Ingestion Engine & Parser Architecture

`DocumentIngester` exposes four format-specific parsers:

1. **`JSONIngester`**:
   - Accepts JSON files or dictionaries.
   - Extracts top-level keys matching metadata fields (`doc_id`, `title`, `category`, `outcome`, `price`, `client`, `date`, `domain`, `tags`).
   - Recursively flattens non-metadata structured content into indexed textual blocks.

2. **`CSVIngester`**:
   - Parses tabular data (e.g. historical price lists, line-item cost structures).
   - Dynamically maps standard column aliases (`item`, `descripcion`, `precio`, `costo`, `cliente`, `resultado`, `fecha`, `categoria`, `dominio`).
   - Generates individual documents per row or aggregates row sets by document ID.

3. **`MarkdownIngester`**:
   - Extracts YAML frontmatter key-value pairs (enclosed in `--- ... ---`) or top metadata headers (`# Title`, `Client: ...`, `Outcome: ...`).
   - Splits document body by H1 (`#`), H2 (`##`), or H3 (`###`) section headers to maintain context integrity.

4. **`TextIngester`**:
   - Parses plain text documents.
   - Uses regex extraction to auto-detect header key-values if available (e.g., `Cliente: Transelec`, `Resultado: Ganada`, `Monto: 45000000`).

### 2.3 Text Chunking Algorithm

- **Chunking Strategy**: Hybrid Section-Aware Sliding Window.
- **Parameters**:
  - `chunk_size`: 500 characters (approx. 80-100 words).
  - `chunk_overlap`: 100 characters.
  - `min_chunk_size`: 50 characters.
- **Rules**:
  - Respect section/paragraph boundaries (`\n\n`) when possible.
  - Inherit all top-level document metadata (`category`, `outcome`, `client`, `domain`, `price`, `date`) into every `DocumentChunk.metadata`.

---

## 3. Vector Embeddings Indexer & Retriever Specification (`src/rag_memory/indexer.py`)

### 3.1 VectorStore Architecture

To maintain zero external C-dependency overhead while achieving millisecond retrieval speeds, `VectorStore` implements a pure-Python high-efficiency sparse vector indexer combining **BM25 Okapi** and **TF-IDF Cosine Similarity**.

```python
class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    bm25_score: float
    cosine_score: float
    metadata: Dict[str, Any]
```

### 3.2 Tokenization & Text Normalization

- Lowercasing and strip diacritics / punctuation using regex `r'\b\w+\b'`.
- Spanish & English Stop-Word Removal (e.g., `de`, `en`, `para`, `el`, `la`, `los`, `un`, `una`, `con`, `por`, `the`, `and`, `or`, `in`).
- Optional Bi-gram Extraction for technical electrical/Odoo terms (e.g., `estudio_edac`, `crossovered_budget`, `licitacion_transelec`, `medicion_pmgd`).

### 3.3 Math & Weighting Algorithms

#### 1. BM25 Okapi Algorithm
For a query $Q = \{q_1, q_2, \dots, q_n\}$ and document chunk $D$:
$$IDF(q_i) = \ln \left( \frac{N - n(q_i) + 0.5}{n(q_i) + 0.5} + 1 \right)$$
$$BM25(D, Q) = \sum_{i=1}^n IDF(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left( 1 - b + b \cdot \frac{|D|}{avgdl} \right)}$$
Parameters: $k_1 = 1.5$, $b = 0.75$.

#### 2. TF-IDF Cosine Similarity
$$\text{TF}(t, D) = 1 + \ln(\text{count}(t, D)) \quad \text{if count} > 0 \text{ else } 0$$
$$\text{IDF}(t) = \ln \left( 1 + \frac{N}{\text{df}(t)} \right)$$
$$\text{Vector Dot Product}: \mathbf{q} \cdot \mathbf{d} = \sum_{t \in Q \cap D} w(t, Q) \cdot w(t, D)$$
$$\text{Cosine Similarity}: \cos(\mathbf{q}, \mathbf{d}) = \frac{\mathbf{q} \cdot \mathbf{d}}{\|\mathbf{q}\|_2 \cdot \|\mathbf{d}\|_2}$$

#### 3. Hybrid Combined Score
$$\text{Score}(D, Q) = \alpha \cdot \text{Normalized\_BM25}(D, Q) + (1 - \alpha) \cdot \text{Cosine\_Similarity}(D, Q)$$
Default $\alpha = 0.6$.

### 3.4 Pre-Filter Metadata Mechanics

Before running similarity calculations across documents, candidate document chunks are filtered via metadata constraints:
- `category`: Match single category or list (e.g., `DocumentCategory.PROPOSAL`).
- `outcome`: Match proposal outcome (e.g., `ProposalOutcome.WON`).
- `client`: Match client name (case-insensitive substring or exact match).
- `domain`: Match domain tag (e.g. `electrical`, `edac_erag`).
- `min_price` / `max_price`: Range filter on numerical price field.
- `date_start` / `date_end`: Date filtering.

Pre-filtering reduces candidate evaluation from $O(N)$ to $O(K)$, where $K \ll N$.

### 3.5 Persistence & Storage (`.agents/rag_store.json`)

The index state is saved to and loaded from a clean JSON file structure:

```json
{
  "version": "1.0",
  "updated_at": "2026-07-28T12:00:00Z",
  "documents": {
    "doc_001": {
      "doc_id": "doc_001",
      "title": "Propuesta Técnica Licitación Transelec EDAC 2025",
      "category": "proposal",
      "outcome": "won",
      "price": 45000000.0,
      "client": "Transelec S.A.",
      "date": "2025-11-15",
      "domain": "edac_erag",
      "tags": ["edac", "protecciones", "di gsilent"],
      "raw_content": "...",
      "metadata": {},
      "created_at": "2026-07-28T12:00:00Z"
    }
  },
  "chunks": {
    "doc_001_chk_0": {
      "chunk_id": "doc_001_chk_0",
      "doc_id": "doc_001",
      "chunk_index": 0,
      "text": "Se presenta la propuesta técnica para el estudio de coordinación...",
      "metadata": {
        "category": "proposal",
        "outcome": "won",
        "client": "Transelec S.A.",
        "domain": "edac_erag",
        "price": 45000000.0
      }
    }
  }
}
```

---

## 4. Few-Shot Dynamic Context Engine Specification (`src/rag_memory/few_shot.py`)

### 4.1 Facade & High-Level Interface Contracts

To satisfy the contract defined in `PROJECT.md`, `rag_memory` exposes `HistoricalMemory`:

```python
class HistoricalMemory:
    """High-level Facade bridging Ingester, VectorStore, and FewShotEngine."""
    
    def __init__(self, storage_path: str = ".agents/rag_store.json"):
        self.ingester = DocumentIngester()
        self.vector_store = VectorStore(storage_path=storage_path)
        self.few_shot_engine = FewShotEngine(self.vector_store)
        
    def ingest_document(self, doc_type: str, content: dict) -> str:
        """Ingests a document payload into the memory engine."""
        doc = self.ingester.ingest_dict({"category": doc_type, **content})
        self.vector_store.add_document(doc)
        self.vector_store.save_to_json()
        return doc.doc_id

    def get_few_shot_context(self, query: str, domain: str = None, top_k: int = 5) -> list[dict]:
        """Retrieves few-shot context examples for agent prompts."""
        return self.few_shot_engine.get_winning_proposal_examples(query=query, domain=domain, top_k=top_k)
```

### 4.2 Specialized Retrieval Methods in `FewShotEngine`

1. **`get_winning_proposal_examples(query, domain, top_k)`**:
   - Queries `VectorStore` with filters: `category=proposal`, `outcome=won`, `domain=domain`.
   - Returns ranked list of winning proposal chunks with pricing and strategy details.

2. **`get_cost_benchmarks(query, domain, top_k)`**:
   - Queries `VectorStore` with filters: `category=cost_structure` or `category=price_list`.
   - Returns pricing line-items and reference costs for quotation agents.

3. **`build_few_shot_prompt(task_type, query, domain, top_k)`**:
   - Assembles a structured Markdown prompt section ready to be injected into an agent system prompt:

```markdown
### HISTORICAL FEW-SHOT CONTEXT & WINNING PATTERNS
The following past winning proposals and historical cost benchmarks match the current task:

#### Example 1: [Propuesta Ganada Transelec EDAC]
- Client: Transelec S.A.
- Outcome: WON | Price: $45,000,000 CLP
- Domain: edac_erag
- Key Excerpt: "Estudio de coordinación de protecciones con simulación DIgSILENT PowerFactory y entrega de informe auditado por SEC."

#### Historical Cost Benchmarks:
- Estudio EDAC / ERAG: $35,000,000 - $50,000,000 CLP
- Simulación Cortocircuito: $8,000,000 - $12,000,000 CLP per substation
- UF/Hour Senior Electrical Engineer: 2.5 UF/hr

Use these historical parameters to guide your proposal generation and budget estimates.
```

---

## 5. Verification Plan & Test Strategy

### 5.1 Unit Tests (`tests/test_rag_memory.py`)
- **Ingester Tests**:
  - Ingestion of JSON files & dicts.
  - Ingestion of CSV price lists with varying column names.
  - Ingestion of Markdown proposals with YAML frontmatter.
  - Ingestion of TXT documents.
  - Chunking behavior (boundary enforcement, overlap, metadata inheritance).
- **VectorStore Tests**:
  - BM25 scoring correctness.
  - Cosine similarity matching.
  - Hybrid scoring ranking.
  - Metadata filtering (`outcome=won`, `category=proposal`, price ranges).
  - Persistence round-trip (`save_to_json` and `load_from_json`).
- **FewShotEngine Tests**:
  - Retrieval of winning proposals.
  - Cost benchmark querying.
  - Dynamic prompt formatting for agents.
  - Interface compliance with `PROJECT.md` contracts.

### 5.2 Test Coverage Goal
- Minimum 95%+ branch and line coverage across `src/rag_memory/ingester.py`, `src/rag_memory/indexer.py`, and `src/rag_memory/few_shot.py`.

---

## 6. Implementation Strategy & Next Steps

1. **Implement `src/rag_memory/ingester.py`**:
   - Define Pydantic models (`DocumentCategory`, `ProposalOutcome`, `DocumentChunk`, `Document`).
   - Implement multi-format parsers (`JSONIngester`, `CSVIngester`, `MarkdownIngester`, `TextIngester`).
   - Implement main `DocumentIngester` wrapper.
2. **Implement `src/rag_memory/indexer.py`**:
   - Implement text normalizer & tokenizer.
   - Build `VectorStore` with BM25 Okapi + TF-IDF Cosine similarity.
   - Implement metadata filter engine.
   - Implement atomic JSON persistence layer (`.agents/rag_store.json`).
3. **Implement `src/rag_memory/few_shot.py`**:
   - Build `FewShotEngine` with winning proposal & benchmark search methods.
   - Build `build_few_shot_prompt` generator.
   - Implement `HistoricalMemory` facade conforming to `PROJECT.md`.
4. **Implement `src/rag_memory/__init__.py`**:
   - Export all public classes and exceptions.
5. **Create Unit Tests (`tests/test_rag_memory.py`)**:
   - Comprehensive test suite covering all tiers and edge cases.
