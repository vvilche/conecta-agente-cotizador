#!/usr/bin/env python3
"""
Detailed 2025 Official Booking & Budget Parser.
Extracts:
- Total Won OCs in 2025 (Booking Real).
- 2025 Annual Sales Targets vs Actual Won (Cumplimiento de Meta 2025).
- Detailed OCs list (Client, Project, CLP Amount, Direct Cost, Gross Margin %).
- 2025 vs 2026 Multi-Year Comparison.
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

def parse_2025_booking_details():
    file_path = Path("booking_y_presupuesto_2025.xlsx")
    df_metas = pd.read_excel(file_path, sheet_name="METAS VTAS Y OCS")

    print("==========================================================================")
    print("📊 INFORME FINANCIERO OFICIAL DE BOOKING Y VENTAS REALES 2025")
    print("==========================================================================")

    # 1. Parse Top Rows (Metas 2025 vs OCs Adjudicadas)
    print("=== 1. METAS ANUALES 2025 vs VENTAS REALES (OCs ADJUDICADAS 2025) ===")
    
    # Search for summary rows in METAS VTAS Y OCS
    summary_data = []
    for r in range(0, 45):
        row_vals = [str(df_metas.iloc[r, c]) for c in range(0, min(15, len(df_metas.columns)))]
        row_txt = " | ".join([v for v in row_vals if v != "nan"])
        if any(k in row_txt.lower() for k in ["normativo", "scada", "pac", "total", "meta", "acumulada", "proyección"]):
            print(f" Línea {r:2d}: {row_txt}")

    # 2. Extract Individual Won OCs (Rows 50 to 190 in METAS VTAS Y OCS)
    oc_rows = df_metas.iloc[45:190].copy()
    
    client_records_2025 = []
    for idx, row in oc_rows.iterrows():
        # Columns in METAS VTAS Y OCS: col 1 = Cliente, col 2 = Proyecto, col 3 = UF, col 5 = Monto Neto CLP, col 6 = Costo, col 7 = Margen, col 9 = Linea, col 10 = Descripcion
        client = row.iloc[1]
        proj_code = row.iloc[2]
        monto_clp = row.iloc[5]
        costo_clp = row.iloc[6]
        margen_clp = row.iloc[7]
        linea = row.iloc[9]
        desc = row.iloc[10]

        if pd.isna(client) or str(client).strip() in ["nan", "Cliente", "Total", "Ordenes de Compra", "OCs"]:
            continue

        try:
            m_clp = float(monto_clp) * 1e6 if (not pd.isna(monto_clp) and float(monto_clp) < 100000) else float(monto_clp or 0)
            c_clp = float(costo_clp) * 1e6 if (not pd.isna(costo_clp) and float(costo_clp) < 100000) else float(costo_clp or 0)
            g_clp = float(margen_clp) * 1e6 if (not pd.isna(margen_clp) and float(margen_clp) < 100000) else float(margen_clp or 0)
        except (ValueError, TypeError):
            continue

        if m_clp > 0:
            client_records_2025.append({
                "client": str(client).strip(),
                "proj_code": str(proj_code).strip(),
                "monto_clp": m_clp,
                "costo_clp": c_clp,
                "margen_clp": g_clp,
                "linea": str(linea).strip(),
                "description": str(desc).strip()
            })

    tot_booking_2025 = sum(r["monto_clp"] for r in client_records_2025)
    tot_cost_2025 = sum(r["costo_clp"] for r in client_records_2025)
    tot_margin_2025 = sum(r["margen_clp"] for r in client_records_2025)
    avg_margin_pct = (tot_margin_2025 / tot_booking_2025 * 100.0) if tot_booking_2025 > 0 else 0.0

    print(f"\n==========================================================================")
    print(f"💰 CIERRE DE VENTAS Y BOOKING REAL 2025 ({len(client_records_2025)} OCs Adjudicadas)")
    print(f"==========================================================================")
    print(f"• Total Monto OCs Adjudicadas 2025 (Booking Real): ${tot_booking_2025:,.0f} CLP (~${tot_booking_2025/1e6:,.1f} Millones CLP)")
    print(f"• Costo Directo Total de Ejecución 2025:           ${tot_cost_2025:,.0f} CLP")
    print(f"• Utilidad Bruta Real Lograda 2025:                 ${tot_margin_2025:,.0f} CLP")
    print(f"• Margen Bruto Real Ejecutado 2025:                 {avg_margin_pct:.2f}%\n")

    # Group by Client
    by_cl = defaultdict(float)
    by_cl_margin = defaultdict(float)
    by_cl_cnt = defaultdict(int)

    for r in client_records_2025:
        cl = r["client"]
        by_cl[cl] += r["monto_clp"]
        by_cl_margin[cl] += r["margen_clp"]
        by_cl_cnt[cl] += 1

    print("--- TOP CLIENTES 2025 POR VENTAS ADJUDICADAS (OCs) ---")
    sorted_cl = sorted(by_cl.items(), key=lambda x: x[1], reverse=True)
    for cl, m_val in sorted_cl:
        g_val = by_cl_margin[cl]
        g_pct = (g_val / m_val * 100.0) if m_val > 0 else 0.0
        cnt = by_cl_cnt[cl]
        print(f"• {cl:<28} | {cnt:>2} OCs | Vendido: ${m_val:>13,.0f} CLP | Margen Bruto: ${g_val:>12,.0f} CLP ({g_pct:>5.1f}%)")

if __name__ == "__main__":
    parse_2025_booking_details()
