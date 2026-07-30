"""
Document Ingestion Engine & Multi-Format Parsers for rag_memory.
Supports JSON, CSV, Markdown, and TXT format parsers with section-aware sliding window chunking.
"""

from enum import Enum
import json
import os
import re
import csv
import io
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


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
    """Immutable representation of a document chunk."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Normalized document model."""
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


def _coerce_category(val: Any) -> DocumentCategory:
    if isinstance(val, DocumentCategory):
        return val
    if not val:
        return DocumentCategory.OTHER
    val_str = str(val).lower().strip()
    mapping = {
        "tender": DocumentCategory.TENDER,
        "licitacion": DocumentCategory.TENDER,
        "licitación": DocumentCategory.TENDER,
        "tdr": DocumentCategory.TENDER,
        "proposal": DocumentCategory.PROPOSAL,
        "propuesta": DocumentCategory.PROPOSAL,
        "oferta": DocumentCategory.PROPOSAL,
        "price_list": DocumentCategory.PRICE_LIST,
        "lista_precios": DocumentCategory.PRICE_LIST,
        "precios": DocumentCategory.PRICE_LIST,
        "cost_structure": DocumentCategory.COST_STRUCTURE,
        "estructura_costos": DocumentCategory.COST_STRUCTURE,
        "costos": DocumentCategory.COST_STRUCTURE,
    }
    return mapping.get(val_str, DocumentCategory.OTHER)


def _coerce_outcome(val: Any) -> ProposalOutcome:
    if isinstance(val, ProposalOutcome):
        return val
    if not val:
        return ProposalOutcome.NA
    val_str = str(val).lower().strip()
    mapping = {
        "won": ProposalOutcome.WON,
        "ganada": ProposalOutcome.WON,
        "adjudicada": ProposalOutcome.WON,
        "lost": ProposalOutcome.LOST,
        "perdida": ProposalOutcome.LOST,
        "rechazada": ProposalOutcome.LOST,
        "pending": ProposalOutcome.PENDING,
        "pendiente": ProposalOutcome.PENDING,
        "en_evaluacion": ProposalOutcome.PENDING,
        "n_a": ProposalOutcome.NA,
        "na": ProposalOutcome.NA,
    }
    return mapping.get(val_str, ProposalOutcome.NA)


def create_sliding_window_chunks(
    doc_id: str,
    text: str,
    doc_metadata: Dict[str, Any],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    min_chunk_size: int = 50
) -> List[DocumentChunk]:
    """
    Creates section-aware sliding window text chunks.
    Preserves document metadata in each chunk's metadata dictionary.
    """
    cleaned_text = text.strip() if text else ""
    if not cleaned_text:
        return []

    # First attempt splitting by double newline or headers
    paragraphs = re.split(r'\n\s*\n', cleaned_text)
    sections: List[str] = []

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
        if len(para_clean) <= chunk_size:
            sections.append(para_clean)
        else:
            # Split long paragraph by sentence boundaries or sub-phrases
            sub_lines = re.split(r'(?<=[.!?])\s+|\n+', para_clean)
            cur_sec = ""
            for line in sub_lines:
                line_str = line.strip()
                if not line_str:
                    continue
                if len(line_str) > chunk_size:
                    # If sentence itself is longer than chunk_size, hard chunk by words
                    words = line_str.split(" ")
                    w_sec = ""
                    for w in words:
                        if len(w_sec) + len(w) + 1 <= chunk_size:
                            w_sec = (w_sec + " " + w).strip()
                        else:
                            if w_sec:
                                sections.append(w_sec)
                            w_sec = w
                    if w_sec:
                        sections.append(w_sec)
                elif len(cur_sec) + len(line_str) + 1 <= chunk_size:
                    cur_sec = (cur_sec + " " + line_str).strip()
                else:
                    if cur_sec:
                        sections.append(cur_sec)
                    cur_sec = line_str
            if cur_sec:
                sections.append(cur_sec)

    # Now merge small sections into chunks with overlap
    chunks: List[DocumentChunk] = []
    chunk_idx = 0
    current_chunk = ""

    for sec in sections:
        if not current_chunk:
            current_chunk = sec
        elif len(current_chunk) + len(sec) + 1 <= chunk_size:
            current_chunk += "\n" + sec
        else:
            # Emit current_chunk
            if len(current_chunk) >= min_chunk_size:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{doc_id}_chk_{chunk_idx}",
                        doc_id=doc_id,
                        chunk_index=chunk_idx,
                        text=current_chunk,
                        metadata=dict(doc_metadata)
                    )
                )
                chunk_idx += 1

            # Prepare next chunk with overlap
            overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
            current_chunk = overlap_text + "\n" + sec

    if current_chunk:
        if len(current_chunk) < min_chunk_size and chunks:
            # Append to previous chunk if too small
            prev = chunks[-1]
            merged_text = prev.text + "\n" + current_chunk
            chunks[-1] = DocumentChunk(
                chunk_id=prev.chunk_id,
                doc_id=prev.doc_id,
                chunk_index=prev.chunk_index,
                text=merged_text,
                metadata=prev.metadata
            )
        else:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_id}_chk_{chunk_idx}",
                    doc_id=doc_id,
                    chunk_index=chunk_idx,
                    text=current_chunk,
                    metadata=dict(doc_metadata)
                )
            )

    return chunks


class JSONIngester:
    """Ingester for JSON objects, files, and standard dict payloads."""

    def ingest(self, content: Union[Dict[str, Any], str], category_override: Optional[str] = None) -> Document:
        if isinstance(content, str):
            if os.path.exists(content):
                with open(content, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = json.loads(content)
        else:
            data = content

        doc_id = str(data.get("doc_id") or data.get("id") or f"doc_{int(datetime.utcnow().timestamp()*1000)}")
        title = str(data.get("title") or data.get("name") or f"Document {doc_id}")
        category = _coerce_category(category_override or data.get("category") or data.get("doc_type"))
        outcome = _coerce_outcome(data.get("outcome") or data.get("result") or data.get("resultado"))
        
        price = data.get("price")
        if price is None:
            price = data.get("monto") or data.get("precio") or data.get("precio_unitario")
        if price is not None:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = None

        client = data.get("client") or data.get("cliente")
        date_str = data.get("date") or data.get("fecha")
        domain = data.get("domain") or data.get("dominio")
        
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # Extract raw text content
        raw_content = data.get("raw_content") or data.get("content") or data.get("text") or ""
        if not raw_content:
            # Flatten non-metadata values into text string
            excluded = {"doc_id", "id", "title", "name", "category", "doc_type", "outcome", "result", "resultado", "price", "monto", "precio", "cliente", "client", "date", "fecha", "domain", "dominio", "tags", "metadata"}
            content_parts = []
            for k, v in data.items():
                if k not in excluded and v is not None:
                    content_parts.append(f"{k}: {v}")
            raw_content = "\n".join(content_parts) if content_parts else title

        custom_meta = dict(data.get("metadata") or {})
        # Enrich metadata
        meta = {
            "doc_id": doc_id,
            "title": title,
            "category": category.value,
            "outcome": outcome.value,
            "price": price,
            "client": client,
            "date": date_str,
            "domain": domain,
            "tags": tags,
            **custom_meta
        }

        chunks = create_sliding_window_chunks(doc_id, raw_content, meta)
        
        return Document(
            doc_id=doc_id,
            title=title,
            category=category,
            outcome=outcome,
            price=price,
            client=client,
            date=str(date_str) if date_str else None,
            domain=str(domain) if domain else None,
            tags=tags,
            raw_content=raw_content,
            metadata=meta,
            chunks=chunks
        )


class CSVIngester:
    """Ingester for tabular CSV strings or files."""

    def ingest(
        self,
        content: str,
        category: Optional[Union[str, DocumentCategory]] = DocumentCategory.COST_STRUCTURE,
        doc_id_prefix: str = "CSV_DOC"
    ) -> List[Document]:
        if os.path.exists(content):
            with open(content, 'r', encoding='utf-8') as f:
                csv_text = f.read()
        else:
            csv_text = content

        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        documents: List[Document] = []

        for idx, row in enumerate(reader):
            # Map column aliases
            row_clean = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
            
            row_doc_id = row_clean.get("doc_id") or row_clean.get("item") or row_clean.get("id") or f"{doc_id_prefix}_{idx+1}"
            title = row_clean.get("title") or row_clean.get("descripcion") or row_clean.get("nombre") or row_clean.get("item") or f"Item {row_doc_id}"
            
            row_cat = _coerce_category(row_clean.get("categoria") or row_clean.get("category") or category)
            outcome = _coerce_outcome(row_clean.get("outcome") or row_clean.get("resultado"))
            
            price_val = row_clean.get("precio") or row_clean.get("precio_unitario") or row_clean.get("costo") or row_clean.get("price")
            price = None
            if price_val:
                try:
                    price = float(price_val.replace("$", "").replace(",", "").strip())
                except ValueError:
                    price = None

            client = row_clean.get("client") or row_clean.get("cliente")
            date_str = row_clean.get("date") or row_clean.get("fecha")
            domain = row_clean.get("domain") or row_clean.get("dominio")
            unidad = row_clean.get("unidad") or row_clean.get("unit")
            
            tags_val = row_clean.get("tags", "")
            tags = [t.strip() for t in tags_val.split(";") if t.strip()] if tags_val else []

            # Content string from row attributes
            content_lines = [f"{k.capitalize()}: {v}" for k, v in row_clean.items()]
            raw_content = "\n".join(content_lines)

            meta = {
                "doc_id": row_doc_id,
                "title": title,
                "category": row_cat.value,
                "outcome": outcome.value,
                "price": price,
                "client": client,
                "date": date_str,
                "domain": domain,
                "unit": unidad,
                "tags": tags
            }

            chunks = create_sliding_window_chunks(row_doc_id, raw_content, meta)

            doc = Document(
                doc_id=row_doc_id,
                title=title,
                category=row_cat,
                outcome=outcome,
                price=price,
                client=client,
                date=date_str,
                domain=domain,
                tags=tags,
                raw_content=raw_content,
                metadata=meta,
                chunks=chunks
            )
            documents.append(doc)

        return documents


class MarkdownIngester:
    """Ingester for Markdown content with optional YAML frontmatter."""

    def ingest(self, content: str, category_override: Optional[str] = None) -> Document:
        if os.path.exists(content):
            with open(content, 'r', encoding='utf-8') as f:
                md_text = f.read()
        else:
            md_text = content

        frontmatter: Dict[str, Any] = {}
        body = md_text.strip()

        # Parse YAML frontmatter enclosed in ---
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', body, re.DOTALL)
        if frontmatter_match:
            fm_str = frontmatter_match.group(1)
            body = body[frontmatter_match.end():].strip()
            for line in fm_str.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    k = key.strip().lower()
                    v = val.strip().strip('"').strip("'")
                    frontmatter[k] = v

        doc_id = frontmatter.get("doc_id") or frontmatter.get("id") or f"md_{int(datetime.utcnow().timestamp()*1000)}"
        title = frontmatter.get("title") or frontmatter.get("name")
        if not title:
            # Match first H1 header in markdown body
            h1_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
            title = h1_match.group(1).strip() if h1_match else f"Markdown Document {doc_id}"

        category = _coerce_category(category_override or frontmatter.get("category") or frontmatter.get("categoria"))
        outcome = _coerce_outcome(frontmatter.get("outcome") or frontmatter.get("resultado"))

        price_val = frontmatter.get("price") or frontmatter.get("monto") or frontmatter.get("precio")
        price = float(price_val) if price_val else None

        client = frontmatter.get("client") or frontmatter.get("cliente")
        date_str = frontmatter.get("date") or frontmatter.get("fecha")
        domain = frontmatter.get("domain") or frontmatter.get("dominio")

        tags_val = frontmatter.get("tags")
        if isinstance(tags_val, str):
            tags = [t.strip() for t in tags_val.split(",") if t.strip()]
        elif isinstance(tags_val, list):
            tags = [str(t).strip() for t in tags_val]
        else:
            tags = []

        meta = {
            "doc_id": doc_id,
            "title": title,
            "category": category.value,
            "outcome": outcome.value,
            "price": price,
            "client": client,
            "date": date_str,
            "domain": domain,
            "tags": tags,
            **frontmatter
        }

        chunks = create_sliding_window_chunks(doc_id, body, meta)

        return Document(
            doc_id=doc_id,
            title=title,
            category=category,
            outcome=outcome,
            price=price,
            client=client,
            date=date_str,
            domain=domain,
            tags=tags,
            raw_content=body,
            metadata=meta,
            chunks=chunks
        )


class TextIngester:
    """Ingester for plain text content with regex key-value auto-detection."""

    def ingest(self, content: str, category_override: Optional[str] = None) -> Document:
        if os.path.exists(content):
            with open(content, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = content

        text_clean = text.strip()

        # Regex header extractors
        client_match = re.search(r'(?:Cliente|Client):\s*(.+)', text_clean, re.IGNORECASE)
        outcome_match = re.search(r'(?:Resultado|Resultado:|Outcome|Resultado de Licitación):\s*(.+)', text_clean, re.IGNORECASE)
        price_match = re.search(r'(?:Monto|Precio|Price):\s*\$?\s*([\d\.,]+)', text_clean, re.IGNORECASE)
        doc_id_match = re.search(r'(?:ID|DocID|Código):\s*(.+)', text_clean, re.IGNORECASE)
        title_match = re.search(r'(?:Título|Title|Asunto):\s*(.+)', text_clean, re.IGNORECASE)

        doc_id = doc_id_match.group(1).strip() if doc_id_match else f"txt_{int(datetime.utcnow().timestamp()*1000)}"
        title = title_match.group(1).strip() if title_match else f"Text Document {doc_id}"
        client = client_match.group(1).strip() if client_match else None
        
        outcome = _coerce_outcome(outcome_match.group(1).strip() if outcome_match else None)
        category = _coerce_category(category_override)

        price = None
        if price_match:
            try:
                price = float(price_match.group(1).replace(".", "").replace(",", "."))
            except ValueError:
                price = None

        meta = {
            "doc_id": doc_id,
            "title": title,
            "category": category.value,
            "outcome": outcome.value,
            "price": price,
            "client": client,
        }

        chunks = create_sliding_window_chunks(doc_id, text_clean, meta)

        return Document(
            doc_id=doc_id,
            title=title,
            category=category,
            outcome=outcome,
            price=price,
            client=client,
            raw_content=text_clean,
            metadata=meta,
            chunks=chunks
        )


class DocumentIngester:
    """Unified Document Ingestion Engine."""

    def __init__(self):
        self.json_ingester = JSONIngester()
        self.csv_ingester = CSVIngester()
        self.markdown_ingester = MarkdownIngester()
        self.text_ingester = TextIngester()

    def ingest_dict(self, content: Dict[str, Any], category: Optional[str] = None) -> Document:
        return self.json_ingester.ingest(content, category_override=category)

    def ingest_json(self, content: Union[Dict[str, Any], str], category: Optional[str] = None) -> Document:
        return self.json_ingester.ingest(content, category_override=category)

    def ingest_csv(self, content: str, category: Optional[Union[str, DocumentCategory]] = DocumentCategory.COST_STRUCTURE) -> List[Document]:
        return self.csv_ingester.ingest(content, category=category)

    def ingest_markdown(self, content: str, category: Optional[str] = None) -> Document:
        return self.markdown_ingester.ingest(content, category_override=category)

    def ingest_text(self, content: str, category: Optional[str] = None) -> Document:
        return self.text_ingester.ingest(content, category_override=category)

    def ingest_file(self, filepath: str, category: Optional[str] = None) -> Union[Document, List[Document]]:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".json":
            return self.ingest_json(filepath, category=category)
        elif ext == ".csv":
            return self.ingest_csv(filepath, category=category)
        elif ext in [".md", ".markdown"]:
            return self.ingest_markdown(filepath, category=category)
        else:
            return self.ingest_text(filepath, category=category)
