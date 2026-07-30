#!/usr/bin/env python3
"""
OT 8000 & Accreditation Dataset Indexer.
Scans ot_8000_smart_extracted folder to catalog:
- Work Orders (OT 8000 series: OT 8208 Colbún, OT 8053 Aguas Antofagasta, etc.).
- Worker Accreditation Dossiers (F30-1, ODIs, Contracts, Medical Exams).
- Financial & Engineering Project Documents.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from collections import defaultdict

def index_ot8000_dataset():
    base_dir = Path("ot_8000_smart_extracted")
    if not base_dir.exists():
        print("❌ Carpeta no encontrada.")
        return

    all_files = list(base_dir.rglob("*"))
    files_only = [f for f in all_files if f.is_file()]

    print("==========================================================================")
    print("📊 CATALOGACIÓN Y ANÁLISIS DE LA SERIE OT 8000 Y ACREDITACIONES")
    print("==========================================================================")
    print(f"• Archivos Recobrados del ZIP Reparado: {len(files_only):,} archivos")

    # Categorize by document purpose
    cats = defaultdict(list)
    ot_groups = defaultdict(list)

    for f in files_only:
        fname = f.name.lower()
        rel_str = str(f.relative_to(base_dir))

        # Check for OT references
        if "ot" in fname or "ot" in rel_str.lower():
            # Try finding OT number
            import re
            m = re.search(r'ot\s*(\d{4})', rel_str.lower())
            if m:
                ot_num = f"OT-{m.group(1)}"
                ot_groups[ot_num].append(f)

        if any(k in fname for k in ["f30", "odi", "epp", "contrato", "antecedentes", "cv", "rioh", "examen", "salud"]):
            cats["Acreditación y Ley de Subcontratación"].append(f)
        elif any(k in fname for k in ["estudio", "informe", "memoria", "especificacion", "plano", "diagrama"]):
            cats["Ingeniería y Diseños Técnicos"].append(f)
        elif any(k in fname for k in ["presupuesto", "cotizacion", "oferta", "factura", "edp", "oc"]):
            cats["Comercial y Estados de Pago"].append(f)
        elif fname.endswith(".pdf"):
            cats["Documentos PDF de Proyecto"].append(f)
        elif fname.endswith(".xlsx") or fname.endswith(".xls") or fname.endswith(".xlsm"):
            cats["Planillas Excel de Gestión"].append(f)
        else:
            cats["Otros Documentos de Soporte"].append(f)

    print("\n--- DISTRIBUCIÓN POR CATEGORÍA DOCUMENTAL ---")
    for cat_name, file_list in cats.items():
        print(f"• {cat_name:<42}: {len(file_list):>5,} archivos")

    print("\n--- ÓRDENES DE TRABAJO OT 8000 DETECTADAS ---")
    sorted_ots = sorted(ot_groups.items(), key=lambda x: len(x[1]), reverse=True)
    for ot_code, f_list in sorted_ots[:15]:
        print(f"• {ot_code:<12} | Archivos Asociados: {len(f_list):>4,} archivos")

    # Store in SQLite database
    conn = sqlite3.connect("matriz_conocimiento_2026.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ot8000_dataset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            filename TEXT,
            relative_path TEXT,
            size_bytes INTEGER
        )
    """)
    cursor.execute("DELETE FROM ot8000_dataset")

    for cat_name, file_list in cats.items():
        for f in file_list:
            cursor.execute("""
                INSERT INTO ot8000_dataset (category, filename, relative_path, size_bytes)
                VALUES (?, ?, ?, ?)
            """, (cat_name, f.name, str(f.relative_to(base_dir)), f.stat().st_size))

    conn.commit()
    print("\n✅ Información integrada exitosamente en 'matriz_conocimiento_2026.sqlite'.")

if __name__ == "__main__":
    index_ot8000_dataset()
