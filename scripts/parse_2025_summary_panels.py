#!/usr/bin/env python3
"""
Inspect Panel de Control and Metas 2025 Summary Tables.
Extracts official 2025 Annual Targets, Total Booking Achieved, and Line Breakdowns.
"""

import pandas as pd
from pathlib import Path

def parse_panels():
    file_path = Path("booking_y_presupuesto_2025.xlsx")
    xl = pd.ExcelFile(file_path)

    print("==========================================================================")
    print("🎯 LECTURA DE PANELES CONSOLIDADOS: BOOKING Y PRESUPUESTO 2025")
    print("==========================================================================")

    # 1. Sheet: PANEL DE CONTROL
    df_panel = pd.read_excel(file_path, sheet_name="PANEL DE CONTROL")
    print("--- 1. HOJA 'PANEL DE CONTROL' ---")
    for r in range(0, min(18, len(df_panel))):
        row_vals = [str(df_panel.iloc[r, c]) for c in range(0, min(15, len(df_panel.columns)))]
        row_txt = " | ".join([v for v in row_vals if v != "nan"])
        if row_txt.strip():
            print(f" Línea {r:2d}: {row_txt}")

    # 2. Sheet: METAS VTAS Y OCS
    df_metas = pd.read_excel(file_path, sheet_name="METAS VTAS Y OCS")
    print("\n--- 2. HOJA 'METAS VTAS Y OCS' (Resumen Metas vs OCs 2025) ---")
    for r in range(0, 35):
        row_vals = [str(df_metas.iloc[r, c]) for c in range(0, min(16, len(df_metas.columns)))]
        row_txt = " | ".join([v for v in row_vals if v != "nan"])
        if row_txt.strip():
            print(f" Línea {r:2d}: {row_txt}")

if __name__ == "__main__":
    parse_panels()
