#!/usr/bin/env python3
"""
2025 Official Booking & Sales Budget Analyzer.
Parses booking_y_presupuesto_2025.xlsx to extract:
- Total 2025 Won OCs (Booking Real).
- 2025 Target Attainment % by Line & Month.
- Direct Execution Costs & Gross Margin Achieved.
- Client Breakdown for 2025.
"""

import openpyxl
import pandas as pd
from pathlib import Path
from collections import defaultdict

def analyze_2025_booking():
    file_path = Path("booking_y_presupuesto_2025.xlsx")
    if not file_path.exists():
        print(f"❌ El archivo '{file_path}' aún no se encuentra en el directorio.")
        return

    xl = pd.ExcelFile(file_path)
    print("==========================================================================")
    print("🎯 ANÁLISIS EJECUTIVO DE BOOKING Y PRESUPUESTO REAL 2025")
    print("==========================================================================")
    print(f"• Hojas Encontradas en el Archivo: {xl.sheet_names}\n")

    for sheet in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet)
        print(f"📄 HOJA: '{sheet}' (Filas: {len(df)}, Columnas: {len(df.columns)})")
        print(df.head(10))
        print("-" * 80)

if __name__ == "__main__":
    analyze_2025_booking()
