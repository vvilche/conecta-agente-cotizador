# Comprehensive Test Design Specification & Fixture Strategy: RAG & Historical Memory Engine (`rag_memory`)

**Milestone**: Milestone 2 (RAG & Historical Memory Engine)  
**Target Module**: `src/rag_memory/` (`ingester.py`, `indexer.py`, `few_shot.py`)  
**Target Test File**: `tests/test_rag_memory.py`  
**Author**: Explorer 2 (`explorer_m2_2`)  
**Date**: 2026-07-28  

---

## Executive Summary

This document presents the detailed test design specification and sample dataset fixture architecture for the **RAG & Historical Memory Engine (`rag_memory`)**.

The test design covers:
1. **`tests/test_rag_memory.py`**: A multi-tiered pytest suite validating document ingestion pipelines (multi-format parsers, Pydantic normalization, section-aware sliding-window chunking), in-memory hybrid vector indexing (BM25 Okapi + TF-IDF cosine similarity, tokenization, stop-words, bi-grams), metadata filtering, top-$k$ similarity precision, few-shot prompt formatting, facade contract compliance, and edge/fault-tolerance scenarios.
2. **Sample Test Fixtures**: Production-realistic Chilean electrical engineering and Odoo ERP domain datasets including sample tenders, won/lost historical proposal records, and line-item cost benchmark pricing matrices.

---

## 1. Test Architecture & Modular Hierarchy

```
tests/
├── conftest.py                   <-- Extended with M2 RAG fixtures & dataset providers
└── test_rag_memory.py            <-- Complete unit, integration & edge-case test suite
    ├── TestDocumentIngester      <-- Ingestion & Chunking (JSON, CSV, MD, TXT)
    ├── TestVectorIndexer         <-- In-Memory VectorStore (BM25, Cosine, Tokenizer, Persistence)
    ├── TestMetadataFiltering     <-- Metadata Filter Constraints & Multi-Attribute Logic
    ├── TestTopKPrecisionAndRanking<- Precision@K, Hybrid Score Weights, Score Ordering
    ├── TestFewShotEngine         <-- Winning Proposals, Cost Benchmarks, Prompt Rendering
    ├── TestHistoricalMemoryFacade<-- PROJECT.md Interface Contract Compliance
    └── TestEdgeCasesAndFaults   <-- Corrupt Files, Empty Stores, Boundary Scores, Unicode
```

---

## 2. Fixtures Architecture Specification (`tests/conftest.py` Extensions)

To support repeatable, isolated, and domain-accurate testing, five primary pytest fixtures are defined:

### 2.1 `sample_tenders_dataset`
Provides a rich list of 4 realistic tender specification dictionaries (EDAC/ERAG protection study, PMGD solar integration, SCADA substation digitalization, and Substation maintenance).

```python
@pytest.fixture
def sample_tenders_dataset():
    """Provides realistic Chilean electrical domain tender specifications."""
    return [
        {
            "doc_id": "TENDER-2025-001",
            "title": "Licitación Estudio de Coordinación de Protecciones EDAC/ERAG Subestación Ancoa",
            "category": "tender",
            "client": "Transelec S.A.",
            "date": "2025-10-15",
            "domain": "edac_erag",
            "tags": ["edac", "erag", "protecciones", "di gsilent"],
            "raw_content": (
                "Requerimientos Términos de Referencia Licitación TDR-2025-001:\n"
                "Se solicita consultoría especializada para realizar el estudio de coordinación de protecciones "
                "y ajuste de esquemas EDAC (Esquema Desconexión Automática de Carga) y ERAG (Esquema de Alivio "
                "de Generación) en la Subestación Ancoa 220kV. Requisitos obligatorios: Simulación en DIgSILENT "
                "PowerFactory v2023, auditoría ante el Coordinador Eléctrico Nacional (CEN), verificación de "
                "tiempos de despeje de fallas y emisión de informe técnico certificado por SEC."
            )
        },
        {
            "doc_id": "TENDER-2025-002",
            "title": "Licitación Integración y Telemetría SITR PMGD Solar El Monte",
            "category": "tender",
            "client": "Empresa Electrica COMASA S.A.",
            "date": "2025-11-01",
            "domain": "pmgd_sitr",
            "tags": ["pmgd", "sitr", "telemetria", "cen"],
            "raw_content": (
                "Bases de Licitación PMGD Solar El Monte 9MW:\n"
                "Implementación de sistema de medición y telemetría en tiempo real (SITR) según normativa "
                "AT-SITR-1 del CEN. Incluye instalación de reconectador en punto de conexión a media tensión (13.8kV), "
                "remota DNP3.0 sobre enlace enlace GPRS redundante, integración con SCADA central y pruebas "
                "de comunicación de punta a punta con el Coordinador Eléctrico Nacional."
            )
        },
        {
            "doc_id": "TENDER-2026-001",
            "title": "Licitación Digitalización de Tableros y Telemedición Subestación Polpaico",
            "category": "tender",
            "client": "Enel Distribución Chile S.A.",
            "date": "2026-01-20",
            "domain": "digitalizacion_scada",
            "tags": ["scada", "telemedicion", "tableros", "iec61850"],
            "raw_content": (
                "Términos Técnicos Digitalización Polpaico:\n"
                "Suministro, montaje y configuración de tableros de control y protección con protocolo IEC 61850. "
                "Integración a Odoo ERP módulo de proyectos y activos para mantenimiento predictivo. Pruebas de "
                "interoperabilidad de relés de protección Siemens SIPROTEC y SEL-751."
            )
        },
        {
            "doc_id": "TENDER-2026-002",
            "title": "Licitación Mantenimiento Preventivo y Calibración de Relés Subestaciones CGE",
            "category": "tender",
            "client": "CGE Distribución S.A.",
            "date": "2026-02-10",
            "domain": "mantenimiento_reles",
            "tags": ["mantenimiento", "reles", "calibracion", "sec"],
            "raw_content": (
                "Bases Mantenimiento Subestaciones CGE Zona Sur:\n"
                "Servicio de inyección de corriente secundaria, prueba de curvas de tiempo-corriente (50/51, 50N/51N), "
                "verificación de transformadores de medida (TC/TP) y certificación de protocolos de prueba ante la SEC."
            )
        }
    ]
```

### 2.2 `historical_proposals_dataset`
Provides 6 historical proposal documents with clear outcomes (`won`, `lost`, `pending`), technical details, price points, and winning strategies.

```python
@pytest.fixture
def historical_proposals_dataset():
    """Provides historical won and lost proposals with pricing & winning strategy metadata."""
    return [
        {
            "doc_id": "PROP-2024-WON-01",
            "title": "Propuesta Técnica y Económica Estudio EDAC/ERAG Transelec S.A.",
            "category": "proposal",
            "outcome": "won",
            "price": 45000000.0,
            "client": "Transelec S.A.",
            "date": "2024-05-10",
            "domain": "edac_erag",
            "tags": ["edac", "erag", "digsilent", "propuesta_ganada"],
            "raw_content": (
                "Propuesta Adjudicada PROP-2024-WON-01:\n"
                "Se propone estudio integral de estabilidad transitoria y ajuste de relés EDAC/ERAG "
                "para la Subestación Ancoa. Metodología basada en simulación DIgSILENT PowerFactory con "
                "modelación de cortocircuito trifásico y monofásico a tierra. Factor clave de adjudicación: "
                "Inclusión de soporte directo durante el proceso de auditoría y aprobación ante la DTR del CEN, "
                "junto con entrega de archivos .pfd listos para ejecución."
            )
        },
        {
            "doc_id": "PROP-2024-WON-02",
            "title": "Propuesta Habilitación Telemetría SITR PMGD Solar del Norte",
            "category": "proposal",
            "outcome": "won",
            "price": 18500000.0,
            "client": "Generadora Solar del Norte SpA",
            "date": "2024-08-22",
            "domain": "pmgd_sitr",
            "tags": ["pmgd", "sitr", "dnp3", "propuesta_ganada"],
            "raw_content": (
                "Propuesta Adjudicada PROP-2024-WON-02:\n"
                "Solución llave en mano de telemetría SITR para PMGD 3MW. Incluye medidor de respaldo clase 0.2S, "
                "RTU de campo con soporte DNP3.0 sobre TCP/IP y módem router industrial con VPN IPsec hacia el CEN. "
                "Ventaja competitiva: Tiempo de ejecución garantizado en 15 días hábiles con aprobación previa de "
                "diagramas unilineales por la SEC."
            )
        },
        {
            "doc_id": "PROP-2024-LOST-01",
            "title": "Propuesta Estudio Cortocircuito y Coordinación Parque Eólico Biobío",
            "category": "proposal",
            "outcome": "lost",
            "price": 68000000.0,
            "client": "Colbún S.A.",
            "date": "2024-03-15",
            "domain": "edac_erag",
            "tags": ["cortocircuito", "propuesta_perdida"],
            "raw_content": (
                "Propuesta Rechazada PROP-2024-LOST-01:\n"
                "Estudio de flujo de potencia y cortocircuito en Parque Eólico 50MW. Motivo de rechazo: "
                "Precio un 25% por encima del presupuesto referencial del cliente ($50.000.000 CLP) y plazo "
                "de entrega excesivo (60 días vs 30 días solicitados)."
            )
        },
        {
            "doc_id": "PROP-2025-WON-03",
            "title": "Propuesta Digitalización Tableros IEC 61850 Subestación San Bernardo",
            "category": "proposal",
            "outcome": "won",
            "price": 32000000.0,
            "client": "Enel Distribución Chile S.A.",
            "date": "2025-02-14",
            "domain": "digitalizacion_scada",
            "tags": ["iec61850", "scada", "propuesta_ganada"],
            "raw_content": (
                "Propuesta Adjudicada PROP-2025-WON-03:\n"
                "Digitalización de 8 paños de distribución en IEC 61850 GOOSE/MMS. Factor decisivo: "
                "Integración nativa de conectores con Odoo ERP para trazabilidad de repuestos y módulos de "
                "mantenimiento de activos."
            )
        },
        {
            "doc_id": "PROP-2025-LOST-02",
            "title": "Propuesta Telemedición y SCADA Subestación Quillota",
            "category": "proposal",
            "outcome": "lost",
            "price": 28000000.0,
            "client": "Empresa Electrica COMASA S.A.",
            "date": "2025-06-01",
            "domain": "pmgd_sitr",
            "tags": ["scada", "propuesta_perdida"],
            "raw_content": (
                "Propuesta Rechazada PROP-2025-LOST-02:\n"
                "Suministro de Gateway SCADA. Motivo de rechazo: Falta de acreditación en norma ISO 27001 "
                "para ciberseguridad en redes OT exigida en las bases administrativas."
            )
        },
        {
            "doc_id": "PROP-2026-PEND-01",
            "title": "Propuesta Auditoría Cumplimiento Normativo CEN 2026",
            "category": "proposal",
            "outcome": "pending",
            "price": 22000000.0,
            "client": "Transelec S.A.",
            "date": "2026-01-10",
            "domain": "auditoria_cen",
            "tags": ["auditoria", "cen", "propuesta_pendiente"],
            "raw_content": (
                "Propuesta en Evaluación PROP-2026-PEND-01:\n"
                "Servicio de auditoría preventiva de cumplimiento normativo técnico para instalaciones de transmisión."
            )
        }
    ]
```

### 2.3 `pricing_matrices_dataset`
Provides structured CSV pricing lists and cost benchmark data.

```python
@pytest.fixture
def pricing_matrices_dataset():
    """Provides CSV string payloads representing historical cost benchmarks & pricing matrices."""
    return """item,descripcion,categoria,precio_unitario,unidad,dominio
ITEM-001,Estudio de Coordinación de Protecciones EDAC/ERAG,cost_structure,45000000,CLP,edac_erag
ITEM-002,Simulación Cortocircuito DIgSILENT por Subestación,cost_structure,10000000,CLP,edac_erag
ITEM-003,Habilitación Enlace SITR Telemetría CEN PMGD,price_list,18500000,CLP,pmgd_sitr
ITEM-004,Ingeniero Senior Electricista UF/Hora,cost_structure,2.5,UF,general
ITEM-005,Ingeniero Especialista SCADA UF/Hora,cost_structure,2.8,UF,digitalizacion_scada
ITEM-006,Prueba de Inyección Secundaria Relé de Protección,price_list,750000,CLP,mantenimiento_reles
ITEM-007,Certificación de Informe Técnico ante SEC,price_list,1500000,CLP,general
"""
```

### 2.4 `temp_rag_store`
Provides a clean, temporary `.json` storage path isolated per test run.

```python
@pytest.fixture
def temp_rag_store(tmp_path):
    """Provides an isolated JSON storage path in pytest temp directory."""
    store_file = tmp_path / "rag_store_test.json"
    return str(store_file)
```

### 2.5 `historical_memory_instance`
Provides a fully initialized `HistoricalMemory` instance pre-loaded with tenders, proposals, and pricing data.

```python
@pytest.fixture
def historical_memory_instance(temp_rag_store, sample_tenders_dataset, historical_proposals_dataset, pricing_matrices_dataset):
    """Provides a HistoricalMemory instance populated with sample dataset fixtures."""
    from rag_memory.few_shot import HistoricalMemory
    
    memory = HistoricalMemory(storage_path=temp_rag_store)
    
    # Ingest tenders
    for t in sample_tenders_dataset:
        memory.ingest_document(doc_type=t["category"], content=t)
        
    # Ingest proposals
    for p in historical_proposals_dataset:
        memory.ingest_document(doc_type=p["category"], content=p)
        
    # Ingest CSV pricing matrix
    memory.ingester.ingest_csv(pricing_matrices_dataset, category="cost_structure")
    
    return memory
```

---

## 3. Test Suite Design Specification (`tests/test_rag_memory.py`)

### Class 1: `TestDocumentIngester`

Validates format parsers, Pydantic schema coercion, chunking parameters, and metadata propagation.

| Test Function | Description & Assertion Targets |
|---------------|--------------------------------|
| `test_ingest_json_dict_valid()` | Ingest valid JSON dictionary. Verify returns `doc_id`, `Document` instance has correct title, category enum (`TENDER`), client, and chunks created with inherited metadata. |
| `test_ingest_csv_pricing_matrix()` | Ingest CSV pricing matrix string/file. Verify standard column aliases (`item`, `descripcion`, `precio_unitario`, `dominio`) map correctly to document metadata and line-item documents/chunks. |
| `test_ingest_markdown_frontmatter()` | Ingest Markdown file with YAML frontmatter (`--- title: ... ---`). Verify frontmatter key-values parse as metadata, and header splits (`#`, `##`) generate logical chunks. |
| `test_ingest_plain_text_regex_parsing()` | Ingest raw plain text containing regex key-values (`Cliente: Transelec`). Verify auto-detection of metadata and text sliding window chunking. |
| `test_chunking_sliding_window_overlap()` | Ingest long document (>1500 chars). Verify `chunk_size` (e.g. 500), `chunk_overlap` (e.g. 100), sequential `chunk_index`, and that text overlaps between adjacent chunks `chk_0` and `chk_1`. |
| `test_metadata_inheritance_to_chunks()` | Ingest document with custom metadata (`{"project_code": "PRJ-99", "outcome": "won"}`). Verify EVERY chunk in `Document.chunks` contains `chunk.metadata["project_code"] == "PRJ-99"` and `chunk.metadata["outcome"] == "won"`. |
| `test_ingest_invalid_schema_coercion()` | Ingest dictionary missing title or doc_id. Verify auto-generation of fallback `doc_id` or explicit validation error according to Pydantic schema rules. |

---

### Class 2: `TestVectorIndexer`

Validates text tokenization, diacritic stripping, BM25 scoring, TF-IDF cosine similarity, hybrid combination, and JSON persistence.

| Test Function | Description & Assertion Targets |
|---------------|--------------------------------|
| `test_tokenization_spanish_diacritics()` | Pass text `"Coordinación de protecciones eléctricas en Subestación Ancoa"`. Verify normalized tokens strip accents (`coordinacion`, `protecciones`, `electricas`), lowercase, and remove Spanish stop-words (`de`, `en`). |
| `test_tokenization_bi_grams()` | Pass technical text `"estudio edac crossovered budget"`. Verify bigram extraction yields `estudio_edac` and `crossovered_budget`. |
| `test_bm25_okapi_scoring()` | Add 3 distinct document chunks. Query for exact terms in Chunk A. Verify Chunk A receives the highest positive BM25 score, while non-matching chunks receive 0.0. |
| `test_tfidf_cosine_similarity_scoring()` | Compute TF-IDF vector dot product and cosine normalization. Verify identical text yields cosine similarity of `1.0`, completely orthogonal text yields `0.0`. |
| `test_hybrid_scoring_combination()` | Test search with `alpha=0.6`. Verify combined score formula: $Score = 0.6 \cdot BM25_{norm} + 0.4 \cdot Cosine$. Verify varying $\alpha$ (0.0, 0.5, 1.0) adjusts relative ranking appropriately. |
| `test_vector_store_persistence_save_load()` | Add 5 documents to `VectorStore`, invoke `save_to_json(temp_rag_store)`. Instantiate new `VectorStore` from `load_from_json(temp_rag_store)`. Verify document count, chunk count, and search query results match identically. |

---

### Class 3: `TestMetadataFiltering`

Validates strict metadata constraints applied prior to similarity scoring.

| Test Function | Description & Assertion Targets |
|---------------|--------------------------------|
| `test_filter_by_outcome_won()` | Search query `"estudio de protecciones"` with filter `outcome="won"`. Verify ALL returned hits have `metadata["outcome"] == "won"`. Ensure losing proposals (e.g. `PROP-2024-LOST-01`) are excluded. |
| `test_filter_by_category()` | Search query `"licitacion"` with filter `category="proposal"`. Verify returned hits exclude documents with `category="tender"` or `category="cost_structure"`. |
| `test_filter_by_client_substring()` | Search query `"telemetria"` with filter `client="Transelec"`. Verify case-insensitive match for `"Transelec S.A."` and exclusion of `"COMASA"`. |
| `test_filter_by_price_range()` | Search with `min_price=20000000.0` and `max_price=50000000.0`. Verify returned hits have `price` strictly within `[20000000, 50000000]`. |
| `test_multi_attribute_filter_conjunction()` | Filter with `category="proposal"`, `outcome="won"`, and `domain="edac_erag"`. Verify only chunks satisfying ALL three conditions simultaneously are returned. |
| `test_filter_no_matches_fallback()` | Search with impossible filter `client="NonExistentCompany"`. Verify search returns empty list `[]` without throwing exception. |

---

### Class 4: `TestTopKPrecisionAndRanking`

Validates ranking accuracy, score ordering, Precision@K, and top-$k$ cutoffs.

| Test Function | Description & Assertion Targets |
|---------------|--------------------------------|
| `test_top_k_cutoff()` | Query `VectorStore` containing 20 chunks with `top_k=3`. Verify `len(results) == 3`. |
| `test_score_monotonic_decreasing_order()` | Query `VectorStore`. Verify returned `SearchResult` list satisfies `results[i].score >= results[i+1].score` for all $i$. |
| `test_precision_at_k_winning_proposals()` | Execute query `"EDAC DIgSILENT Transelec"` with `top_k=2`. Verify target document `PROP-2024-WON-01` is ranked `#1` (Precision@1 = 1.0). |
| `test_score_normalization_range()` | Execute various queries. Verify all returned `score`, `bm25_score`, and `cosine_score` values are bounded in $[0.0, 1.0]$. |

---

### Class 5: `TestFewShotEngine`

Validates prompt assembly, winning proposal extraction, cost benchmark retrieval, and `HistoricalMemory` facade compliance.

| Test Function | Description & Assertion Targets |
|---------------|--------------------------------|
| `test_get_winning_proposal_examples()` | Call `few_shot_engine.get_winning_proposal_examples(query="EDAC", domain="edac_erag", top_k=2)`. Verify returns list of dicts with keys (`doc_id`, `client`, `price`, `outcome`, `text`), where `outcome == "won"`. |
| `test_get_cost_benchmarks()` | Call `few_shot_engine.get_cost_benchmarks(query="Ingeniero Senior UF", top_k=3)`. Verify returns cost structure items with pricing units and rates. |
| `test_build_few_shot_prompt_formatting()` | Call `few_shot_engine.build_few_shot_prompt(task_type="rfq", query="Estudio EDAC", domain="edac_erag")`. Verify output string is valid Markdown containing header `### HISTORICAL FEW-SHOT CONTEXT`, formatted winning examples, and benchmark parameters. |
| `test_historical_memory_facade_contract()` | Test `HistoricalMemory.ingest_document(doc_type, content)` and `HistoricalMemory.get_few_shot_context(query, domain, top_k)`. Verify exact interface signature and return types match `PROJECT.md` specification. |

---

### Class 6: `TestEdgeCasesAndFaultTolerance`

Validates resilience against corrupt files, empty stores, boundary scores, unicode characters, and concurrency.

| Test Function | Description & Assertion Targets |
|---------------|--------------------------------|
| `test_query_empty_store()` | Instantiate empty `VectorStore`. Query with any search string. Verify returns `[]` cleanly without zero-division or index errors. |
| `test_ingest_empty_or_whitespace_document()` | Ingest document with `raw_content=""` or `"   \n  "`. Verify handled gracefully with 0 chunks created or single empty chunk without crashing. |
| `test_corrupt_json_store_recovery()` | Write invalid JSON text `"{ corrupt_json ..."` into store file. Call `VectorStore.load_from_json()`. Verify raises clear `ValueError` / `JSONDecodeError` or initializes empty store safely according to fault recovery policy. |
| `test_boundary_scores_zero_overlap()` | Search query with terms that do not appear anywhere in store (e.g. `"xyzqwert12345"`). Verify returned scores are `0.0` or empty results list. |
| `test_non_ascii_unicode_spanish_characters()` | Ingest document with characters `ñ`, `á`, `é`, `í`, `ó`, `ú`, `Ü`, `¿`, `¡`, `€`. Query with diacritics and without diacritics (e.g. `"diseño de línea"` vs `"diseno de linea"`). Verify fuzzy diacritic matching finds the chunk. |
| `test_extreme_large_document_chunking()` | Ingest document with 50,000 characters of repeating text. Verify chunking completes in <50ms without recursion or memory errors, generating ~100 chunks. |

---

## 4. Test Execution & Coverage Matrix

| Test Module / Class | Target Functions | Requirement / Scope | Expected Pass Target | Coverage Goal |
|---------------------|------------------|---------------------|----------------------|---------------|
| `TestDocumentIngester` | `ingest_dict`, `ingest_csv`, `ingest_markdown`, `_chunk_text` | Ingestion, Parsers & Chunking | 100% Pass | >95% |
| `TestVectorIndexer` | `tokenize`, `_compute_bm25`, `_compute_cosine`, `add_document`, `save_to_json`, `load_from_json` | In-Memory Hybrid Search & Persistence | 100% Pass | >95% |
| `TestMetadataFiltering` | `search(filters=...)` | Metadata Filtering Constraints | 100% Pass | >95% |
| `TestTopKPrecisionAndRanking` | `search(top_k=...)` | Retrieval Precision & Ranking Order | 100% Pass | >95% |
| `TestFewShotEngine` | `get_winning_proposal_examples`, `get_cost_benchmarks`, `build_few_shot_prompt` | Prompt Context & Winning Patterns | 100% Pass | >95% |
| `TestHistoricalMemoryFacade` | `ingest_document`, `get_few_shot_context` | `PROJECT.md` Contract Compliance | 100% Pass | 100% |
| `TestEdgeCasesAndFaults` | All module edge cases | Corrupt files, empty stores, unicode, zero match | 100% Pass | >90% |

---

## 5. Implementation Strategy for Implementer (Worker Agent)

When implementing `src/rag_memory/` and `tests/test_rag_memory.py`:

1. **Fixtures Setup (`tests/conftest.py`)**:
   - Add `sample_tenders_dataset`, `historical_proposals_dataset`, `pricing_matrices_dataset`, `temp_rag_store`, and `historical_memory_instance` fixtures to `tests/conftest.py`.

2. **Test Implementation (`tests/test_rag_memory.py`)**:
   - Organize into the 6 specified pytest classes (`TestDocumentIngester`, `TestVectorIndexer`, `TestMetadataFiltering`, `TestTopKPrecisionAndRanking`, `TestFewShotEngine`, `TestEdgeCasesAndFaults`).
   - Ensure all 30 test cases are implemented with clear docstrings and precise assertion messages.

3. **Execution Command**:
   ```bash
   pytest tests/test_rag_memory.py -v --cov=src/rag_memory --cov-report=term-missing
   ```

4. **Coverage Acceptance**:
   - Confirm branch & line coverage $\ge 95\%$ across `src/rag_memory/ingester.py`, `src/rag_memory/indexer.py`, and `src/rag_memory/few_shot.py`.
