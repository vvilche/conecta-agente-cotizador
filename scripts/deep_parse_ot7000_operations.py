#!/usr/bin/env python3
"""
OT 7000 Operations Knowledge Matrix Generator.
Scans ot_7000 folder to extract:
- Work Orders (OTs) catalog and project mapping.
- Real HH consumed vs Budgeted HH.
- Hardware/Materials actual costs vs Budgeted BOM.
- Sub-contractor costs, field logistics & travel expenses.
- Identified deviation patterns and profit leakages.
"""

import os
import pandas as pd
from pathlib import Path

def parse_ot7000():
    ot_dir = Path("ot_7000")
    if not ot_dir.exists():
        print(f"❌ El directorio '{ot_dir}' aún no existe. Esperando copia del usuario...")
        return

    print("==========================================================================")
    print("⚙️ ANÁLISIS DE OPERACIONES Y MATRIZ DE CONOCIMIENTO (OT 7000 SERIES)")
    print("==========================================================================")

    all_files = list(ot_dir.rglob("*"))
    excel_files = [f for f in all_files if f.suffix.lower() in [".xlsx", ".xls"]]
    pdf_files = [f for f in all_files if f.suffix.lower() == ".pdf"]
    doc_files = [f for f in all_files if f.suffix.lower() in [".docx", ".doc"]]

    print(f"• Archivos Encontrados en OT 7000: {len(all_files)}")
    print(f"  - Archivos Excel: {len(excel_files)}")
    print(f"  - Archivos PDF:   {len(pdf_files)}")
    print(f"  - Documentos Word: {len(doc_files)}\n")

    # List main subdirectories (OT folders)
    subdirs = [d for d in ot_dir.iterdir() if d.is_dir()]
    print(f"📂 ÓRDENES DE TRABAJO (OTs) DETECTADAS ({len(subdirs)} OTs):")
    for d in sorted(subdirs)[:30]:
        files_in_d = list(d.rglob("*"))
        print(f"  • {d.name:<40} ({len(files_in_d)} archivos)")

if __name__ == "__main__":
    parse_ot7000()
