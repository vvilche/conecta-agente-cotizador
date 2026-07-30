"""
VectorStore & Retriever Engine using pure-Python BM25 Okapi and TF-IDF Cosine Similarity.
Includes Spanish text normalization (diacritics stripping), metadata pre-filtering, and JSON persistence.
"""

import os
import json
import math
import re
import unicodedata
import threading
import tempfile
from enum import Enum
from typing import Optional, List, Dict, Any, Union, Set
from pydantic import BaseModel, Field
from datetime import datetime

from rag_memory.ingester import Document, DocumentChunk, DocumentCategory, ProposalOutcome


# Spanish and English stop words set
STOP_WORDS: Set[str] = {
    # Spanish
    "de", "la", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no", "una",
    "su", "al", "lo", "como", "mas", "más", "pero", "sus", "le", "ya", "o", "este", "si", "sí", "porque",
    "esta", "entre", "cuando", "muy", "sin", "sobre", "tambien", "también", "me", "hasta", "hay", "donde",
    "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese",
    "eso", "ante", "ellos", "e", "esto", "mi", "mí", "antes", "algunos", "que", "qué", "unos", "yo",
    "otro", "otras", "otra", "el", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos",
    "cual", "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "mis", "tu", "tú", "te",
    "ti", "tus",
    # English
    "the", "and", "is", "in", "to", "of", "for", "with", "on", "at", "by", "from", "an", "a", "or", "it",
    "as", "be", "are", "this", "that", "which", "was", "were", "has", "have", "had", "been", "with"
}


def strip_diacritics(text: str) -> str:
    """Strips diacritics/accents from unicode string."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def tokenize(text: str, extract_bigrams: bool = True) -> List[str]:
    """
    Normalizes and tokenizes string text:
    1. Lowercase & strip diacritics
    2. Extract word tokens
    3. Filter stop words
    4. Optional technical bi-grams
    """
    if not text:
        return []
    
    clean_text = strip_diacritics(text.lower())
    words = re.findall(r'\b[a-z0-9_]+\b', clean_text)
    
    filtered_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    
    tokens = list(filtered_words)
    if extract_bigrams and len(filtered_words) >= 2:
        bigrams = [f"{filtered_words[i]}_{filtered_words[i+1]}" for i in range(len(filtered_words)-1)]
        tokens.extend(bigrams)
        
    return tokens


class SearchResult(BaseModel):
    """Model representing a vector retrieval hit."""
    chunk_id: str
    doc_id: str
    text: str
    score: float
    bm25_score: float
    cosine_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorStore:
    """
    In-Memory Vector Store combining BM25 Okapi & TF-IDF Cosine Similarity.
    Supports metadata pre-filtering, Spanish text normalization, and JSON persistence.
    """

    def __init__(self, storage_path: Optional[str] = ".agents/rag_store.json"):
        self._lock = threading.RLock()
        self.storage_path = storage_path
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, DocumentChunk] = {}
        
        # Index structures
        self.chunk_tokens: Dict[str, List[str]] = {}
        self.chunk_tf: Dict[str, Dict[str, int]] = {}
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0

        if self.storage_path and os.path.exists(self.storage_path):
            self.load_from_json(self.storage_path)

    def add_document(self, doc: Document) -> None:
        """Adds a Document and its chunks to the store and updates inverted index."""
        with self._lock:
            self.documents[doc.doc_id] = doc
            for chunk in doc.chunks:
                self.add_chunk(chunk)

    def add_chunk(self, chunk: DocumentChunk) -> None:
        """Adds a DocumentChunk to index."""
        with self._lock:
            self.chunks[chunk.chunk_id] = chunk
            tokens = tokenize(chunk.text)
            self.chunk_tokens[chunk.chunk_id] = tokens
            
            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            self.chunk_tf[chunk.chunk_id] = tf
            
            self.doc_lengths[chunk.chunk_id] = len(tokens)
            
            # Update document frequencies
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1
                
            self._update_avg_doc_length()

    def _update_avg_doc_length(self) -> None:
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)
        else:
            self.avg_doc_length = 0.0

    def _matches_filters(self, chunk: DocumentChunk, filters: Dict[str, Any]) -> bool:
        """Evaluates metadata pre-filter constraints against chunk metadata."""
        if not filters:
            return True
            
        meta = chunk.metadata
        
        # Category filter
        if "category" in filters and filters["category"] is not None:
            target_cat = filters["category"]
            chunk_cat = meta.get("category")
            if isinstance(target_cat, list):
                target_cats = [c.value if isinstance(c, Enum) else str(c) for c in target_cat]
                if chunk_cat not in target_cats:
                    return False
            else:
                target_val = target_cat.value if isinstance(target_cat, Enum) else str(target_cat)
                if chunk_cat != target_val:
                    return False

        # Outcome filter
        if "outcome" in filters and filters["outcome"] is not None:
            target_out = filters["outcome"]
            chunk_out = meta.get("outcome")
            if isinstance(target_out, list):
                target_outs = [o.value if isinstance(o, Enum) else str(o) for o in target_out]
                if chunk_out not in target_outs:
                    return False
            else:
                target_val = target_out.value if isinstance(target_out, Enum) else str(target_out)
                if chunk_out != target_val:
                    return False

        # Client filter (case-insensitive substring match)
        if "client" in filters and filters["client"]:
            target_client = strip_diacritics(str(filters["client"]).lower())
            chunk_client = strip_diacritics(str(meta.get("client") or "").lower())
            if not chunk_client or target_client not in chunk_client:
                return False

        # Domain filter
        if "domain" in filters and filters["domain"]:
            target_dom = filters["domain"]
            chunk_dom = meta.get("domain")
            if isinstance(target_dom, list):
                if chunk_dom not in target_dom:
                    return False
            else:
                if chunk_dom != str(target_dom):
                    return False

        # Numerical price range filters
        price = meta.get("price")
        if "min_price" in filters and filters["min_price"] is not None:
            if price is None or float(price) < float(filters["min_price"]):
                return False
        if "max_price" in filters and filters["max_price"] is not None:
            if price is None or float(price) > float(filters["max_price"]):
                return False

        # Date range filters
        date_str = meta.get("date")
        if "date_start" in filters and filters["date_start"]:
            if not date_str or str(date_str) < str(filters["date_start"]):
                return False
        if "date_end" in filters and filters["date_end"]:
            if not date_str or str(date_str) > str(filters["date_end"]):
                return False

        # Tags filter
        if "tags" in filters and filters["tags"]:
            target_tags = set(filters["tags"]) if isinstance(filters["tags"], list) else {filters["tags"]}
            chunk_tags = set(meta.get("tags", []))
            if not target_tags.intersection(chunk_tags):
                return False

        return True

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        alpha: float = 0.6,
        k1: float = 1.5,
        b: float = 0.75
    ) -> List[SearchResult]:
        """
        Executes hybrid similarity search (BM25 + TF-IDF Cosine) with metadata pre-filtering.
        - alpha: Weight factor for BM25 vs Cosine (1.0 = pure BM25, 0.0 = pure Cosine)
        """
        with self._lock:
            if not self.chunks or not query.strip():
                return []

            query_tokens = tokenize(query)
            if not query_tokens:
                return []

            # Filter candidate chunks
            candidate_ids = [cid for cid, chunk in self.chunks.items() if self._matches_filters(chunk, filters or {})]
            if not candidate_ids:
                return []

            num_chunks = len(self.chunks)
            
            # Calculate BM25 scores for candidates
            bm25_scores: Dict[str, float] = {}
            for cid in candidate_ids:
                score = 0.0
                doc_len = self.doc_lengths[cid]
                tf_map = self.chunk_tf[cid]
                
                for token in query_tokens:
                    if token in tf_map:
                        freq = tf_map[token]
                        df = self.doc_freqs.get(token, 0)
                        idf = math.log(((num_chunks - df + 0.5) / (df + 0.5)) + 1.0)
                        if idf < 0:
                            idf = 0.0
                            
                        denom = freq + k1 * (1.0 - b + b * (doc_len / (self.avg_doc_length or 1.0)))
                        score += idf * ((freq * (k1 + 1.0)) / denom)
                bm25_scores[cid] = score

            # Calculate TF-IDF Cosine scores for candidates
            query_tf: Dict[str, int] = {}
            for t in query_tokens:
                query_tf[t] = query_tf.get(t, 0) + 1

            # Query vector weights and norm
            query_weights: Dict[str, float] = {}
            q_norm_sq = 0.0
            for token, q_freq in query_tf.items():
                df = self.doc_freqs.get(token, 0)
                if df > 0:
                    idf = math.log(1.0 + (num_chunks / df))
                    tf = 1.0 + math.log(q_freq)
                    w = tf * idf
                    query_weights[token] = w
                    q_norm_sq += w * w

            q_norm = math.sqrt(q_norm_sq)

            cosine_scores: Dict[str, float] = {}
            for cid in candidate_ids:
                if q_norm == 0.0:
                    cosine_scores[cid] = 0.0
                    continue

                tf_map = self.chunk_tf[cid]
                dot_product = 0.0
                doc_norm_sq = 0.0

                for token, d_freq in tf_map.items():
                    df = self.doc_freqs.get(token, 0)
                    idf = math.log(1.0 + (num_chunks / (df if df > 0 else 1)))
                    d_tf = 1.0 + math.log(d_freq)
                    d_weight = d_tf * idf
                    doc_norm_sq += d_weight * d_weight
                    
                    if token in query_weights:
                        dot_product += query_weights[token] * d_weight

                doc_norm = math.sqrt(doc_norm_sq)
                if q_norm * doc_norm > 0:
                    cosine_scores[cid] = dot_product / (q_norm * doc_norm)
                else:
                    cosine_scores[cid] = 0.0

            # Normalize BM25 scores to [0.0, 1.0]
            max_bm25 = max(bm25_scores.values()) if bm25_scores and max(bm25_scores.values()) > 0 else 1.0

            results: List[SearchResult] = []
            for cid in candidate_ids:
                b_score = bm25_scores[cid]
                c_score = cosine_scores[cid]
                norm_b_score = b_score / max_bm25 if max_bm25 > 0 else 0.0
                
                hybrid_score = (alpha * norm_b_score) + ((1.0 - alpha) * c_score)
                if hybrid_score <= 0.0:
                    continue
                
                chunk = self.chunks[cid]
                results.append(
                    SearchResult(
                        chunk_id=cid,
                        doc_id=chunk.doc_id,
                        text=chunk.text,
                        score=round(hybrid_score, 6),
                        bm25_score=round(b_score, 6),
                        cosine_score=round(c_score, 6),
                        metadata=chunk.metadata
                    )
                )

            # Sort descending by hybrid_score
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]

    def save_to_json(self, filepath: Optional[str] = None) -> str:
        """Saves current index state to JSON file using atomic replacement."""
        with self._lock:
            target_path = filepath or self.storage_path or ".agents/rag_store.json"
            
            # Ensure parent directory exists
            parent_dir = os.path.dirname(os.path.abspath(target_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "documents": {doc_id: doc.model_dump() for doc_id, doc in self.documents.items()},
                "chunks": {cid: chunk.model_dump() for cid, chunk in self.chunks.items()}
            }

            tmp_fd, tmp_path = tempfile.mkstemp(dir=parent_dir, prefix=".rag_store_", suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, target_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

            return target_path

    def load_from_json(self, filepath: Optional[str] = None) -> None:
        """Loads index state from JSON file and rebuilds indexes."""
        with self._lock:
            target_path = filepath or self.storage_path or ".agents/rag_store.json"
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Storage path {target_path} does not exist.")

            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.documents.clear()
            self.chunks.clear()
            self.chunk_tokens.clear()
            self.chunk_tf.clear()
            self.doc_freqs.clear()
            self.doc_lengths.clear()

            raw_docs = data.get("documents", {})
            for doc_id, doc_dict in raw_docs.items():
                self.documents[doc_id] = Document(**doc_dict)

            raw_chunks = data.get("chunks", {})
            for cid, chunk_dict in raw_chunks.items():
                chunk = DocumentChunk(**chunk_dict)
                self.add_chunk(chunk)
