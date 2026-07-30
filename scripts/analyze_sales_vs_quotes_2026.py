#!/usr/bin/env python3
"""
Sales vs Quotations 2026 Deep Performance Analytics.
Analyzes meta_ventas_2026.xlsx to compute:
- Total Quoted Amount ($ CLP / USD) vs Total Won/Sold Amount (OCs Adjudicadas).
- Real Conversion / Win Rate % by Client and Business Line.
- Target Sales Attainment % for 2026.
- Monthly / Quarterly sales pipeline progression.
"""

import openpyxl
import pandas as pd
import json
from pathlib import Path

def run_sales_analysis():
    file_path = Path("meta_ventas_2026.xlsx")
    if not file_path.exists():
        print("File meta_ventas_2026.xlsx not found.")
        return

    xl = pd.ExcelFile(file_path)
    print("==========================================================================")
    print("📊 ANÁLISIS DE VENTAS vs COTIZADO Y METAS 2026")
    print("==========================================================================")
    print("Hojas encontradas en el archivo:", xl.sheet_names)

    sheet_summary = {}

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"\n--------------------------------------------------------------------------")
        print(f"📄 HOJA: '{sheet_name}' (Total filas: {len(df)}, Columnas: {len(df.columns)})")
        print(f"--------------------------------------------------------------------------")
        print("Columnas:", df.columns.tolist())
        print("\nMuestra de datos (primeras 5 filas):")
        print(df.head(5))

        # Store basic stats
        sheet_summary[sheet_name] = {
            "rows": len(df),
            "columns": df.columns.tolist()
        }

if __name__ == "__main__":
    run_sales_analysis()
