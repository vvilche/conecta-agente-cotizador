#!/usr/bin/env python3
"""
CLI Batch Ingestion Script for 10 GB Commercial Offers (2026+).
Generates the structured Knowledge Matrix (SQLite + JSON) and indexes chunks into RAG Vector Store.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag_memory.knowledge_matrix import KnowledgeMatrix, OfferRecord, PricingItem, OfferStatus
from rag_memory.ingester import DocumentIngester
from rag_memory.few_shot import HistoricalMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_file_to_offer_record(file_path: Path) -> OfferRecord:
    """
    Deterministically parses a single proposal/tender file into an OfferRecord.
    Supports .json, .csv, .txt, .pdf, .xlsx.
    """
    file_name = file_path.name
    doc_id = file_path.stem.upper().replace(" ", "_")
    client_name = "Cliente General"
    
    # Try extracting client from filename if formatted like CLIENT_OFFER.ext
    parts = file_name.split("_")
    if len(parts) > 1:
        client_name = parts[0].title()

    raw_content = ""
    try:
        if file_path.suffix.lower() == ".json":
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return OfferRecord(
                        offer_id=data.get("doc_id") or data.get("offer_id") or doc_id,
                        title=data.get("title") or file_path.stem,
                        client_name=data.get("client") or data.get("client_name") or client_name,
                        date=data.get("date") or "2026-01-01",
                        status=OfferStatus(data.get("outcome", "pending")),
                        domain=data.get("domain", "general"),
                        total_amount=float(data.get("price") or data.get("total_amount") or 0.0),
                        currency=data.get("currency", "CLP"),
                        raw_source_path=str(file_path)
                    )
        elif file_path.suffix.lower() in [".txt", ".md", ".csv"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_content = f.read(5000)
    except Exception as e:
        logger.warning(f"Could not open file {file_path}: {e}")

    return OfferRecord(
        offer_id=doc_id,
        title=file_path.stem,
        client_name=client_name,
        date="2026-01-01",
        status=OfferStatus.PENDING,
        domain="general",
        total_amount=0.0,
        currency="CLP",
        raw_source_path=str(file_path)
    )


def process_dataset_directory(
    dataset_dir: str,
    matrix_db_path: str = "matriz_conocimiento_2026.sqlite",
    export_json_path: str = "matriz_conocimiento_2026.json"
):
    dataset_path = Path(dataset_dir)
    if not dataset_path.exists():
        logger.error(f"Dataset path '{dataset_dir}' does not exist.")
        return

    logger.info(f"Scanning directory: {dataset_path.resolve()}")
    files = [p for p in dataset_path.rglob("*") if p.is_file() and not p.name.startswith(".")]
    logger.info(f"Found {len(files)} files to process.")

    km = KnowledgeMatrix(db_path=matrix_db_path)
    memory = HistoricalMemory()
    ingester = DocumentIngester()

    success_count = 0
    for idx, f in enumerate(files, 1):
        try:
            record = parse_file_to_offer_record(f)
            km.add_record(record)
            
            # Ingest to RAG memory vector index
            doc = ingester.ingest_dict({
                "doc_id": record.offer_id,
                "title": record.title,
                "category": record.category,
                "outcome": record.status.value,
                "price": record.total_amount,
                "client": record.client_name,
                "date": record.date,
                "domain": record.domain,
                "raw_content": f"Oferta {record.title} Cliente: {record.client_name}. Ruta: {record.raw_source_path}"
            })
            memory.vector_store.add_document(doc)
            success_count += 1

            if idx % 100 == 0 or idx == len(files):
                logger.info(f"Processed {idx}/{len(files)} files...")
        except Exception as e:
            logger.error(f"Error processing {f}: {e}")

    km.export_to_json(export_json_path)
    rag_store_path = "rag_store_2026.json"
    memory.vector_store.save_to_json(rag_store_path)
    logger.info("==================================================")
    logger.info(f"Ingestion Completed Successfully!")
    logger.info(f"Total Offers Ingested: {km.count()}")
    logger.info(f"SQLite Matrix Database: {Path(matrix_db_path).resolve()}")
    logger.info(f"JSON Export: {Path(export_json_path).resolve()}")
    logger.info(f"RAG Vector Store: {Path(rag_store_path).resolve()}")
    logger.info("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Knowledge Matrix from batch folder.")
    parser.add_argument("dataset_dir", type=str, help="Path to 10 GB dataset folder or sync directory.")
    parser.add_argument("--db", type=str, default="matriz_conocimiento_2026.sqlite", help="SQLite DB output path.")
    parser.add_argument("--json", type=str, default="matriz_conocimiento_2026.json", help="JSON output path.")
    args = parser.parse_args()

    process_dataset_directory(args.dataset_dir, args.db, args.json)
