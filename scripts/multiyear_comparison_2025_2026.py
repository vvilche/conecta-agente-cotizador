#!/usr/bin/env python3
"""
Multi-Year Commercial Comparison (2025 vs 2026).
Analyzes historical evolution of offer volume, business line mix, and client portfolios across 7,533 records.
"""

import sqlite3
import pandas as pd
from pathlib import Path

def run_multiyear_analysis():
    conn = sqlite3.connect("matriz_conocimiento_2026.sqlite")
    
    df = pd.read_sql_query("SELECT offer_id, client_name, domain, total_amount, date FROM knowledge_matrix", conn)
    df["year"] = df["offer_id"].apply(lambda x: "2025" if "2025" in str(x) else "2026")

    print("==========================================================================")
    print("📊 ANÁLISIS COMPARATIVO MULTI-ANUAL INTELIGENCIA COMERCIAL (2025 vs 2026)")
    print("==========================================================================")
    print(f"• Total Registros Analizados: {len(df):,}")

    yearly = df.groupby("year")["total_amount"].agg(["count", "sum", "mean"]).reset_index()
    print("\n=== EVOLUCIÓN ANUAL GLOBAL ===")
    for idx, row in yearly.iterrows():
        yr = row["year"]
        cnt = int(row["count"])
        tot = row["sum"]
        avg = row["mean"]
        print(f"• Año {yr}: {cnt:>4} registros | Total: ${tot:>16,.0f} CLP (~${tot/1e9:>5.2f}B CLP) | Promedio: ${avg:>11,.0f} CLP")

    print("\n=== EVOLUCIÓN POR LÍNEA DE NEGOCIO (2025 vs 2026) ===")
    by_domain_yr = df.groupby(["domain", "year"])["total_amount"].agg(["count", "sum"]).unstack(fill_value=0)
    print(by_domain_yr)

    print("\n=== TOP 10 CLIENTES MULTI-ANUALES (2025 vs 2026) ===")
    top_clients = df.groupby("client_name")["total_amount"].sum().sort_values(ascending=False).head(10)
    for client, total in top_clients.items():
        sub_df = df[df["client_name"] == client]
        v_2025 = sub_df[sub_df["year"] == "2025"]["total_amount"].sum()
        v_2026 = sub_df[sub_df["year"] == "2026"]["total_amount"].sum()
        print(f"• {client:<30} | Total 2025: ${v_2025:>13,.0f} CLP | Total 2026: ${v_2026:>13,.0f} CLP | Total Acumulado: ${total:>14,.0f} CLP")

if __name__ == "__main__":
    run_multiyear_analysis()
