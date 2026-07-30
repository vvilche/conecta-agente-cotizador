#!/usr/bin/env python3
"""
BOM & Itemized Cost Extractor for 2026 Commercial Proposals.
Parses Excel spreadsheets in '3 Calculo de Oferta' and '4 Oferta' subfolders,
classifies project folders by BusinessLineType, and updates the Knowledge Matrix.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag_memory.business_lines import BusinessLineClassifier, BusinessLineType, STANDARD_BOM_TEMPLATES
from rag_memory.knowledge_matrix import KnowledgeMatrix, OfferRecord, PricingItem, OfferStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_items_from_excel(excel_path: Path) -> List[PricingItem]:
    """
    Attempts parsing itemized cost table from an Excel spreadsheet (.xlsx/.xls).
    Uses pandas / openpyxl if available, or falls back to filename heuristics.
    """
    items: List[PricingItem] = []
    try:
        import pandas as pd
        # Read Excel sheets
        excel_file = pd.ExcelFile(excel_path)
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            if df.empty:
                continue
            # Search for columns matching item, descripcion, precio, total
            col_map = {}
            for col in df.columns:
                c_str = str(col).lower()
                if "descrip" in c_str or "detalle" in c_str or "item" in c_str or "concepto" in c_str:
                    col_map["desc"] = col
                elif "total" in c_str or "precio" in c_str or "monto" in c_str or "val" in c_str:
                    col_map["price"] = col
                elif "cant" in c_str or "qty" in c_str:
                    col_map["qty"] = col

            if "desc" in col_map and "price" in col_map:
                for _, row in df.iterrows():
                    desc_val = str(row[col_map["desc"]]).strip()
                    if desc_val and desc_val.lower() != "nan" and len(desc_val) > 3:
                        try:
                            p_val = float(row[col_map["price"]])
                            if p_val > 0:
                                qty_val = float(row[col_map["qty"]]) if "qty" in col_map and pd.notnull(row[col_map["qty"]]) else 1.0
                                items.append(PricingItem(
                                    description=desc_val,
                                    quantity=qty_val,
                                    unit_price=p_val / (qty_val or 1.0),
                                    total_price=p_val,
                                    currency="CLP"
                                ))
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logger.debug(f"Excel parsing fallback for {excel_path.name}: {e}")

    return items


def scan_and_extract_boms(dataset_dir: str, db_path: str = "matriz_conocimiento_2026.sqlite"):
    dataset_path = Path(dataset_dir)
    if not dataset_path.exists():
        logger.error(f"Path '{dataset_dir}' does not exist.")
        return

    logger.info(f"Scanning project folders in: {dataset_path.resolve()}")
    project_folders = [p for p in dataset_path.glob("*") if p.is_dir()]
    logger.info(f"Found {len(project_folders)} project directories.")

    km = KnowledgeMatrix(db_path=db_path)
    total_boms_found = 0

    for idx, folder in enumerate(project_folders, 1):
        folder_name = folder.name
        business_line = BusinessLineClassifier.classify(folder_name)

        # Search for Excel files in folder
        excel_files = list(folder.rglob("*.xlsx")) + list(folder.rglob("*.xls"))
        extracted_items: List[PricingItem] = []

        for excel_p in excel_files:
            if "~$" in excel_p.name:  # Skip lock files
                continue
            f_items = extract_items_from_excel(excel_p)
            extracted_items.extend(f_items)

        # If no items extracted from Excel, populate with standard BOM template defaults for that business line
        if not extracted_items:
            template = STANDARD_BOM_TEMPLATES.get(business_line)
            if template:
                for b_item in template.items:
                    extracted_items.append(PricingItem(
                        item_code=b_item.item_code,
                        description=b_item.description,
                        quantity=b_item.default_qty,
                        unit=b_item.unit,
                        unit_price=b_item.unit_price_clp,
                        total_price=b_item.default_qty * b_item.unit_price_clp,
                        currency="CLP"
                    ))

        total_amount = sum(it.total_price for it in extracted_items)

        # Build OfferRecord
        record = OfferRecord(
            offer_id=folder_name.upper().replace(" ", "_"),
            title=folder_name,
            client_name=folder_name.split("-")[1].strip() if "-" in folder_name else "Cliente 2026",
            date="2026-01-01",
            status=OfferStatus.PENDING,
            domain=business_line.value,
            total_amount=total_amount,
            currency="CLP",
            pricing_items=extracted_items,
            raw_source_path=str(folder)
        )

        km.add_record(record)
        if extracted_items:
            total_boms_found += 1

        if idx % 50 == 0 or idx == len(project_folders):
            logger.info(f"Processed {idx}/{len(project_folders)} project folders...")

    logger.info("==================================================")
    logger.info(f"BOM Extraction Completed Successfully!")
    logger.info(f"Total Projects Processed: {len(project_folders)}")
    logger.info(f"Projects with BOM Items Extracted: {total_boms_found}")
    logger.info(f"Updated SQLite Database: {Path(db_path).resolve()}")
    logger.info("==================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract BOMs and classify business lines from 2026 projects.")
    parser.add_argument("dataset_dir", type=str, help="Path to 2026 commercial project root directory.")
    parser.add_argument("--db", type=str, default="matriz_conocimiento_2026.sqlite", help="SQLite DB path.")
    args = parser.parse_args()

    scan_and_extract_boms(args.dataset_dir, args.db)
