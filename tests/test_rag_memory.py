"""
Comprehensive Unit & Integration Test Suite for RAG & Historical Memory Engine (`rag_memory`).
Covers Document Ingestion, Hybrid Vector Indexing (BM25 + Cosine), Metadata Filtering,
Top-K Precision, Few-Shot Dynamic Context Engine, HistoricalMemory Facade, and Edge Cases.
"""

import os
import pytest
import json
from rag_memory import (
    Document,
    DocumentChunk,
    DocumentCategory,
    ProposalOutcome,
    DocumentIngester,
    JSONIngester,
    CSVIngester,
    MarkdownIngester,
    TextIngester,
    VectorStore,
    SearchResult,
    FewShotEngine,
    HistoricalMemory,
    tokenize,
    strip_diacritics,
)


class TestDocumentIngester:
    """Tests for multi-format parsers, sliding-window chunking, and metadata propagation."""

    def test_ingest_json_dict_valid(self, sample_tenders_dataset):
        ingester = DocumentIngester()
        doc_data = sample_tenders_dataset[0]
        doc = ingester.ingest_json(doc_data)

        assert isinstance(doc, Document)
        assert doc.doc_id == "TENDER-2025-001"
        assert doc.category == DocumentCategory.TENDER
        assert doc.client == "Transelec S.A."
        assert len(doc.chunks) > 0
        assert doc.chunks[0].metadata["client"] == "Transelec S.A."

    def test_ingest_csv_pricing_matrix(self, pricing_matrices_dataset):
        ingester = DocumentIngester()
        docs = ingester.ingest_csv(pricing_matrices_dataset, category="cost_structure")

        assert len(docs) == 7
        doc0 = docs[0]
        assert doc0.doc_id == "ITEM-001"
        assert doc0.price == 45000000.0
        assert doc0.domain == "edac_erag"
        assert doc0.category == DocumentCategory.COST_STRUCTURE
        assert len(doc0.chunks) > 0

    def test_ingest_markdown_frontmatter(self):
        md_content = """---
doc_id: PROP-MD-01
title: Propuesta Markdown Test
category: proposal
outcome: won
price: 15000000
client: Enel Distribución Chile S.A.
domain: digitalizacion_scada
tags: scada, iec61850
---

# Propuesta Markdown Test

## Sección 1: Introducción
Se presenta la solución técnica para digitalización de tableros IEC 61850.

## Sección 2: Alcance Técnico
Suministro e instalación de relés de protección Siemens SIPROTEC con conector Odoo.
"""
        ingester = DocumentIngester()
        doc = ingester.ingest_markdown(md_content)

        assert doc.doc_id == "PROP-MD-01"
        assert doc.title == "Propuesta Markdown Test"
        assert doc.category == DocumentCategory.PROPOSAL
        assert doc.outcome == ProposalOutcome.WON
        assert doc.price == 15000000.0
        assert doc.client == "Enel Distribución Chile S.A."
        assert "scada" in doc.tags
        assert len(doc.chunks) >= 1

    def test_ingest_plain_text_regex_parsing(self):
        txt_content = """
ID: PROP-TXT-99
Título: Propuesta en Texto Plano
Cliente: Empresa Electrica COMASA S.A.
Resultado: Adjudicada
Monto: $ 25.000.000

Detalle de la propuesta de servicios de mantenimiento preventivo de subestaciones.
"""
        ingester = DocumentIngester()
        doc = ingester.ingest_text(txt_content)

        assert doc.doc_id == "PROP-TXT-99"
        assert doc.title == "Propuesta en Texto Plano"
        assert doc.client == "Empresa Electrica COMASA S.A."
        assert doc.outcome == ProposalOutcome.WON
        assert doc.price == 25000000.0
        assert len(doc.chunks) > 0

    def test_chunking_sliding_window_overlap(self):
        long_text = "Esta es una frase repetida para probar el algoritmo de chunking sliding window. " * 30
        ingester = DocumentIngester()
        doc = ingester.ingest_dict({
            "doc_id": "LONG-01",
            "title": "Long Document",
            "raw_content": long_text
        })

        assert len(doc.chunks) >= 2
        chunk0 = doc.chunks[0]
        chunk1 = doc.chunks[1]

        assert chunk0.chunk_index == 0
        assert chunk1.chunk_index == 1
        # Overlap check
        overlap_part = chunk0.text[-50:]
        assert overlap_part in chunk1.text or chunk1.text[:50] in chunk0.text

    def test_metadata_inheritance_to_chunks(self):
        ingester = DocumentIngester()
        doc = ingester.ingest_dict({
            "doc_id": "META-01",
            "title": "Meta Test",
            "category": "proposal",
            "outcome": "won",
            "price": 5000000.0,
            "client": "Transelec",
            "domain": "edac_erag",
            "raw_content": "Texto largo para generar chunks " * 20
        })

        for chunk in doc.chunks:
            assert chunk.metadata["category"] == "proposal"
            assert chunk.metadata["outcome"] == "won"
            assert chunk.metadata["client"] == "Transelec"
            assert chunk.metadata["domain"] == "edac_erag"
            assert chunk.metadata["price"] == 5000000.0

    def test_ingest_file_auto_dispatch(self, tmp_path):
        json_file = tmp_path / "test_doc.json"
        json_file.write_text(json.dumps({
            "doc_id": "FILE-01",
            "title": "File Dispatch Test",
            "content": "Contenido del archivo JSON"
        }), encoding="utf-8")

        ingester = DocumentIngester()
        doc = ingester.ingest_file(str(json_file))

        assert isinstance(doc, Document)
        assert doc.doc_id == "FILE-01"


class TestVectorIndexer:
    """Tests for tokenization, diacritic removal, BM25, Cosine similarity, and JSON persistence."""

    def test_tokenization_spanish_diacritics(self):
        text = "Coordinación de protecciones eléctricas en Subestación Ancoa!"
        tokens = tokenize(text)

        assert "coordinacion" in tokens
        assert "protecciones" in tokens
        assert "electricas" in tokens
        assert "subestacion" in tokens
        assert "ancoa" in tokens
        assert "de" not in tokens  # Stop word removed
        assert "en" not in tokens  # Stop word removed

    def test_tokenization_bi_grams(self):
        text = "estudio edac crossovered budget"
        tokens = tokenize(text, extract_bigrams=True)

        assert "estudio_edac" in tokens
        assert "crossovered_budget" in tokens

    def test_bm25_okapi_scoring(self):
        store = VectorStore(storage_path=None)

        doc1 = Document(
            doc_id="D1",
            title="EDAC",
            raw_content="Estudio de protecciones EDAC y ERAG en Subestación Ancoa",
            chunks=[
                DocumentChunk(
                    chunk_id="D1_c0",
                    doc_id="D1",
                    chunk_index=0,
                    text="Estudio de protecciones EDAC y ERAG en Subestación Ancoa",
                    metadata={}
                )
            ]
        )
        doc2 = Document(
            doc_id="D2",
            title="SCADA",
            raw_content="Suministro de tableros SCADA e IEC 61850",
            chunks=[
                DocumentChunk(
                    chunk_id="D2_c0",
                    doc_id="D2",
                    chunk_index=0,
                    text="Suministro de tableros SCADA e IEC 61850",
                    metadata={}
                )
            ]
        )

        store.add_document(doc1)
        store.add_document(doc2)

        results = store.search(query="protecciones EDAC Ancoa", alpha=1.0)
        assert len(results) > 0
        assert results[0].doc_id == "D1"
        assert results[0].bm25_score > 0.0

    def test_tfidf_cosine_similarity_scoring(self):
        store = VectorStore(storage_path=None)

        doc1 = Document(
            doc_id="C1",
            title="Solar",
            raw_content="Telemetria SITR PMGD solar fotovoltaica",
            chunks=[
                DocumentChunk(
                    chunk_id="C1_c0",
                    doc_id="C1",
                    chunk_index=0,
                    text="Telemetria SITR PMGD solar fotovoltaica",
                    metadata={}
                )
            ]
        )
        store.add_document(doc1)

        results = store.search(query="Telemetria SITR PMGD solar fotovoltaica", alpha=0.0)
        assert len(results) == 1
        assert results[0].cosine_score > 0.99  # Identical text should have ~1.0 cosine similarity

    def test_hybrid_scoring_combination(self):
        store = VectorStore(storage_path=None)

        doc = Document(
            doc_id="H1",
            title="Hybrid",
            raw_content="Inyección de corriente secundaria y relé Siemens",
            chunks=[
                DocumentChunk(
                    chunk_id="H1_c0",
                    doc_id="H1",
                    chunk_index=0,
                    text="Inyección de corriente secundaria y relé Siemens",
                    metadata={}
                )
            ]
        )
        store.add_document(doc)

        res_hybrid = store.search(query="inyeccion corriente relé", alpha=0.6)
        assert len(res_hybrid) == 1
        expected_score = 0.6 * (res_hybrid[0].bm25_score / (res_hybrid[0].bm25_score or 1.0)) + 0.4 * res_hybrid[0].cosine_score
        assert abs(res_hybrid[0].score - round(expected_score, 6)) < 1e-4

    def test_vector_store_persistence_save_load(self, temp_rag_store, sample_tenders_dataset):
        store = VectorStore(storage_path=temp_rag_store)
        ingester = DocumentIngester()

        for t in sample_tenders_dataset:
            doc = ingester.ingest_json(t)
            store.add_document(doc)

        store.save_to_json(temp_rag_store)
        assert os.path.exists(temp_rag_store)

        # Reload in fresh store
        store_new = VectorStore(storage_path=temp_rag_store)
        assert len(store_new.documents) == 4
        assert len(store_new.chunks) > 0

        res = store_new.search("EDAC ERAG Subestación Ancoa")
        assert len(res) > 0
        assert res[0].doc_id == "TENDER-2025-001"


class TestMetadataFiltering:
    """Tests for metadata constraints prior to similarity scoring."""

    def test_filter_by_outcome_won(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="estudio protecciones",
            filters={"outcome": "won"}
        )
        assert len(results) > 0
        for r in results:
            assert r.metadata["outcome"] == "won"

    def test_filter_by_category(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="licitacion",
            filters={"category": "tender"}
        )
        assert len(results) > 0
        for r in results:
            assert r.metadata["category"] == "tender"

    def test_filter_by_client_substring(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="estudio",
            filters={"client": "Transelec"}
        )
        assert len(results) > 0
        for r in results:
            assert "transelec" in r.metadata["client"].lower()

    def test_filter_by_price_range(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="propuesta",
            filters={"min_price": 20000000.0, "max_price": 50000000.0}
        )
        assert len(results) > 0
        for r in results:
            assert 20000000.0 <= r.metadata["price"] <= 50000000.0

    def test_multi_attribute_filter_conjunction(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="EDAC",
            filters={
                "category": "proposal",
                "outcome": "won",
                "domain": "edac_erag"
            }
        )
        assert len(results) > 0
        for r in results:
            assert r.metadata["category"] == "proposal"
            assert r.metadata["outcome"] == "won"
            assert r.metadata["domain"] == "edac_erag"

    def test_filter_no_matches_fallback(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="protecciones",
            filters={"client": "NonExistentCompanyXYZ"}
        )
        assert results == []

    def test_filter_by_enum_instances(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="estudio protecciones",
            filters={
                "category": DocumentCategory.PROPOSAL,
                "outcome": ProposalOutcome.WON
            }
        )
        assert len(results) > 0
        for r in results:
            assert r.metadata["category"] == "proposal"
            assert r.metadata["outcome"] == "won"

    def test_filter_by_enum_list_instances(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="estudio protecciones",
            filters={
                "category": [DocumentCategory.PROPOSAL],
                "outcome": [ProposalOutcome.WON]
            }
        )
        assert len(results) > 0
        for r in results:
            assert r.metadata["category"] == "proposal"
            assert r.metadata["outcome"] == "won"


class TestTopKPrecisionAndRanking:
    """Tests for retrieval ordering, Precision@K, and top_k cutoffs."""

    def test_top_k_cutoff(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="estudio protecciones telemetria",
            top_k=2
        )
        assert len(results) <= 2

    def test_score_monotonic_decreasing_order(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="estudio licitacion propuesta",
            top_k=5
        )
        assert len(results) > 1
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_precision_at_k_winning_proposals(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search(
            query="EDAC DIgSILENT Transelec Ancoa",
            filters={"outcome": "won"},
            top_k=1
        )
        assert len(results) == 1
        assert results[0].doc_id == "PROP-2024-WON-01"


class TestFewShotEngine:
    """Tests for FewShotEngine methods and dynamic prompt rendering."""

    def test_get_winning_proposal_examples(self, historical_memory_instance):
        engine = historical_memory_instance.few_shot_engine
        examples = engine.get_winning_proposal_examples(query="EDAC", domain="edac_erag", top_k=2)

        assert len(examples) > 0
        ex0 = examples[0]
        assert ex0["outcome"] == "won"
        assert "price" in ex0
        assert "text" in ex0
        assert "client" in ex0

    def test_get_cost_benchmarks(self, historical_memory_instance):
        engine = historical_memory_instance.few_shot_engine
        benchmarks = engine.get_cost_benchmarks(query="Ingeniero Senior UF", top_k=2)

        assert len(benchmarks) > 0
        bm0 = benchmarks[0]
        assert "price" in bm0
        assert "unit" in bm0
        assert "text" in bm0

    def test_build_few_shot_prompt_formatting(self, historical_memory_instance):
        engine = historical_memory_instance.few_shot_engine
        prompt = engine.build_few_shot_prompt(
            task_type="rfq",
            query="Estudio EDAC ERAG",
            domain="edac_erag",
            top_k=2
        )

        assert "### HISTORICAL FEW-SHOT CONTEXT & WINNING PATTERNS" in prompt
        assert "Past Winning Proposals & Successful Strategies:" in prompt
        assert "Historical Cost Benchmarks & Pricing Reference:" in prompt


class TestHistoricalMemoryFacade:
    """Tests for HistoricalMemory facade contract compliance with PROJECT.md."""

    def test_historical_memory_facade_contract(self, temp_rag_store):
        memory = HistoricalMemory(storage_path=temp_rag_store)

        doc_id = memory.ingest_document(
            doc_type="proposal",
            content={
                "doc_id": "PROP-FACADE-01",
                "title": "Propuesta Facade Contract Test",
                "outcome": "won",
                "price": 12000000.0,
                "client": "COMASA",
                "domain": "pmgd_sitr",
                "raw_content": "Servicio de habilitación telemetría SITR PMGD COMASA"
            }
        )

        assert doc_id == "PROP-FACADE-01"

        context = memory.get_few_shot_context(
            query="telemetria SITR PMGD",
            domain="pmgd_sitr",
            top_k=3
        )

        assert len(context) > 0
        assert context[0]["doc_id"] == "PROP-FACADE-01"
        assert context[0]["outcome"] == "won"


class TestEdgeCasesAndFaultTolerance:
    """Tests for resilience against empty queries, corrupt storage files, non-ASCII Unicode, etc."""

    def test_query_empty_store(self):
        store = VectorStore(storage_path=None)
        results = store.search("query on empty store")
        assert results == []

    def test_ingest_empty_or_whitespace_document(self):
        ingester = DocumentIngester()
        doc = ingester.ingest_dict({
            "doc_id": "EMPTY-01",
            "title": "Empty Doc",
            "raw_content": "   \n\n  "
        })
        assert doc.doc_id == "EMPTY-01"

    def test_corrupt_json_store_recovery(self, tmp_path):
        corrupt_file = tmp_path / "corrupt_rag_store.json"
        corrupt_file.write_text("{ corrupt json syntax ...", encoding="utf-8")

        with pytest.raises(Exception):
            VectorStore(storage_path=str(corrupt_file))

    def test_boundary_scores_zero_overlap(self, historical_memory_instance):
        results = historical_memory_instance.vector_store.search("xyzqwert12345nonexistenttoken")
        assert results == []

    def test_non_ascii_unicode_spanish_characters(self, temp_rag_store):
        store = VectorStore(storage_path=temp_rag_store)
        ingester = DocumentIngester()

        doc = ingester.ingest_dict({
            "doc_id": "UNICODE-01",
            "title": "Diseño de Líneas de Transmisión",
            "raw_content": "Análisis de parámetros de diseño, diseno de linea, ñandú, operación en 220kV"
        })
        store.add_document(doc)

        results_accents = store.search("diseño de línea")
        results_no_accents = store.search("diseno de linea")

        assert len(results_accents) > 0
        assert len(results_no_accents) > 0
        assert results_accents[0].doc_id == "UNICODE-01"
        assert results_no_accents[0].doc_id == "UNICODE-01"

    def test_extreme_large_document_chunking(self):
        ingester = DocumentIngester()
        large_content = "Texto repetido para probar rendimiento en documentos de gran volumen. " * 1000  # ~70k chars
        doc = ingester.ingest_dict({
            "doc_id": "LARGE-01",
            "title": "Large Doc",
            "raw_content": large_content
        })

        assert len(doc.chunks) > 50
        assert doc.chunks[0].chunk_index == 0


class TestThreadSafetyAndAtomicPersistence:
    """Tests for thread safety under concurrency and atomic persistence in VectorStore."""

    def test_concurrent_read_write_thread_safety(self):
        import concurrent.futures

        store = VectorStore(storage_path=None)
        doc_base = Document(
            doc_id="BASE",
            title="Base Doc",
            raw_content="Base content for concurrent indexing testing",
            chunks=[
                DocumentChunk(
                    chunk_id="BASE_c0",
                    doc_id="BASE",
                    chunk_index=0,
                    text="Base content for concurrent indexing testing",
                    metadata={}
                )
            ]
        )
        store.add_document(doc_base)

        def writer(i):
            doc = Document(
                doc_id=f"DOC_{i}",
                title=f"Doc {i}",
                raw_content=f"Concurrent text insertion content number {i}",
                chunks=[
                    DocumentChunk(
                        chunk_id=f"DOC_{i}_c0",
                        doc_id=f"DOC_{i}",
                        chunk_index=0,
                        text=f"Concurrent text insertion content number {i}",
                        metadata={"category": "proposal"}
                    )
                ]
            )
            store.add_document(doc)

        def reader():
            return store.search(query="concurrent text content", top_k=5)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            writer_futures = [executor.submit(writer, i) for i in range(50)]
            reader_futures = [executor.submit(reader) for _ in range(50)]
            concurrent.futures.wait(writer_futures + reader_futures)

            for f in writer_futures:
                assert f.exception() is None
            for f in reader_futures:
                assert f.exception() is None

        assert len(store.documents) == 51

    def test_atomic_json_persistence(self, tmp_path, monkeypatch):
        store_path = str(tmp_path / "atomic_rag_store.json")
        store = VectorStore(storage_path=store_path)
        doc = Document(
            doc_id="ATOMIC-1",
            title="Atomic Save Doc",
            raw_content="Testing atomic write and replace functionality",
            chunks=[
                DocumentChunk(
                    chunk_id="ATOMIC-1_c0",
                    doc_id="ATOMIC-1",
                    chunk_index=0,
                    text="Testing atomic write and replace functionality",
                    metadata={}
                )
            ]
        )
        store.add_document(doc)

        replaced_paths = []
        original_replace = os.replace

        def mock_replace(src, dst):
            replaced_paths.append((src, dst))
            return original_replace(src, dst)

        monkeypatch.setattr(os, "replace", mock_replace)

        saved_path = store.save_to_json(store_path)
        assert saved_path == store_path
        assert os.path.exists(store_path)
        assert len(replaced_paths) == 1
        src, dst = replaced_paths[0]
        assert dst == store_path
        assert src != dst
        assert not os.path.exists(src)  # Temporary file was atomically moved/replaced

        # Reload to verify integrity
        loaded_store = VectorStore(storage_path=store_path)
        assert "ATOMIC-1" in loaded_store.documents
