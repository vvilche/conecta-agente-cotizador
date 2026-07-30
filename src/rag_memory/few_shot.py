"""
Few-Shot Dynamic Context Engine & HistoricalMemory Facade for rag_memory.
Bridges ingestion, indexing, winning proposal extraction, cost benchmark retrieval, and dynamic prompt construction.
"""

from typing import Optional, List, Dict, Any
from rag_memory.ingester import DocumentIngester, DocumentCategory, ProposalOutcome
from rag_memory.indexer import VectorStore, SearchResult


class FewShotEngine:
    """Engine for retrieving winning proposal patterns, cost benchmarks, and constructing dynamic few-shot prompts."""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def get_winning_proposal_examples(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k past winning proposal chunks matching the query and domain filters.
        """
        filters: Dict[str, Any] = {
            "category": DocumentCategory.PROPOSAL.value,
            "outcome": ProposalOutcome.WON.value,
        }
        if domain:
            filters["domain"] = domain

        results = self.vector_store.search(query=query, filters=filters, top_k=top_k)

        # Fallback to domain-agnostic search if no domain hits
        if not results and domain:
            fallback_filters = {
                "category": DocumentCategory.PROPOSAL.value,
                "outcome": ProposalOutcome.WON.value,
            }
            results = self.vector_store.search(query=query, filters=fallback_filters, top_k=top_k)

        examples: List[Dict[str, Any]] = []
        for r in results:
            meta = r.metadata
            examples.append({
                "doc_id": r.doc_id,
                "chunk_id": r.chunk_id,
                "title": meta.get("title", f"Proposal {r.doc_id}"),
                "client": meta.get("client", "N/A"),
                "price": meta.get("price"),
                "outcome": meta.get("outcome", "won"),
                "domain": meta.get("domain", "N/A"),
                "text": r.text,
                "score": r.score,
                "metadata": meta
            })

        return examples

    def get_cost_benchmarks(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k historical price list items and cost structures matching the query.
        """
        filters: Dict[str, Any] = {
            "category": [DocumentCategory.COST_STRUCTURE.value, DocumentCategory.PRICE_LIST.value]
        }
        if domain:
            filters["domain"] = domain

        results = self.vector_store.search(query=query, filters=filters, top_k=top_k)

        if not results and domain:
            fallback_filters = {
                "category": [DocumentCategory.COST_STRUCTURE.value, DocumentCategory.PRICE_LIST.value]
            }
            results = self.vector_store.search(query=query, filters=fallback_filters, top_k=top_k)

        benchmarks: List[Dict[str, Any]] = []
        for r in results:
            meta = r.metadata
            benchmarks.append({
                "doc_id": r.doc_id,
                "chunk_id": r.chunk_id,
                "title": meta.get("title", f"Benchmark {r.doc_id}"),
                "price": meta.get("price"),
                "unit": meta.get("unit", "CLP"),
                "category": meta.get("category"),
                "domain": meta.get("domain", "N/A"),
                "text": r.text,
                "score": r.score,
                "metadata": meta
            })

        return benchmarks

    def build_few_shot_prompt(
        self,
        task_type: str,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 3
    ) -> str:
        """
        Assembles a structured Markdown prompt block containing winning proposals and cost benchmarks.
        """
        winning_examples = self.get_winning_proposal_examples(query=query, domain=domain, top_k=top_k)
        cost_benchmarks = self.get_cost_benchmarks(query=query, domain=domain, top_k=top_k)

        lines: List[str] = []
        lines.append("### HISTORICAL FEW-SHOT CONTEXT & WINNING PATTERNS")
        lines.append(f"Task Type: {task_type.upper()} | Query Domain: {domain or 'General'}\n")

        if winning_examples:
            lines.append("#### Past Winning Proposals & Successful Strategies:")
            for idx, ex in enumerate(winning_examples, 1):
                price_str = f"${ex['price']:,.0f} CLP" if isinstance(ex['price'], (int, float)) else "N/A"
                lines.append(f"**Example {idx}: {ex['title']}**")
                lines.append(f"- **Client**: {ex['client']} | **Price**: {price_str} | **Domain**: {ex['domain']}")
                lines.append(f"- **Key Strategy / Technical Content**:\n  \"{ex['text']}\"\n")
        else:
            lines.append("#### Past Winning Proposals:\nNo directly matching winning proposals found in historical memory.\n")

        if cost_benchmarks:
            lines.append("#### Historical Cost Benchmarks & Pricing Reference:")
            for idx, bm in enumerate(cost_benchmarks, 1):
                price_str = f"${bm['price']:,.2f} {bm['unit']}" if isinstance(bm['price'], (int, float)) else "N/A"
                lines.append(f"- **Benchmark {idx}**: {bm['title']} -> Price: {price_str}")
                lines.append(f"  *Detail*: \"{bm['text']}\"")
            lines.append("")

        lines.append("Use these historical benchmarks and winning strategy parameters to guide output generation.")
        return "\n".join(lines)


class HistoricalMemory:
    """
    High-level Facade bridging Ingester, VectorStore, and FewShotEngine.
    Exposes the public contracts required by PROJECT.md.
    """

    def __init__(self, storage_path: str = ".agents/rag_store.json"):
        self.storage_path = storage_path
        self.ingester = DocumentIngester()
        self.vector_store = VectorStore(storage_path=self.storage_path)
        self.few_shot_engine = FewShotEngine(self.vector_store)

    def ingest_document(self, doc_type: str, content: dict) -> str:
        """
        Ingests a document payload into the memory engine and updates persistence store.
        Satisfies `HistoricalMemory.ingest_document(doc_type: str, content: dict) -> str`.
        """
        payload = dict(content) if content else {}
        doc = self.ingester.ingest_dict(payload, category=doc_type)
        self.vector_store.add_document(doc)
        if self.storage_path:
            self.vector_store.save_to_json(self.storage_path)
        return doc.doc_id

    def get_few_shot_context(self, query: str, domain: str = None, top_k: int = 5) -> list[dict]:
        """
        Retrieves few-shot context examples for agent prompts.
        Satisfies `HistoricalMemory.get_few_shot_context(query: str, domain: str, top_k: int = 5) -> list[dict]`.
        """
        return self.few_shot_engine.get_winning_proposal_examples(query=query, domain=domain, top_k=top_k)
