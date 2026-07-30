#!/usr/bin/env python3
"""
Buying Patterns & HH Optimization Analytics Engine (2025-2026).
Parses client purchase cycles, ticket distribution, HH cost structures, and margin expansion potential.
"""

import sqlite3
import pandas as pd
from pathlib import Path

def analyze_patterns():
    conn = sqlite3.connect("matriz_conocimiento_2026.sqlite")
    df = pd.read_sql_query("SELECT offer_id, project_code, client_name, year, domain, total_amount, cost_amount, margin_pct FROM knowledge_matrix", conn)

    print("==========================================================================")
    print("📊 ANÁLISIS DE PATRONES DE COMPRA Y OPTIMIZACIÓN DE HH (2025-2026)")
    print("==========================================================================")

    # 1. Ticket Distribution & Frequency per Client
    print("\n--- 1. PATRONES DE COMPRA POR CLIENTE (FRECUENCIA Y TICKET PROMEDIO) ---")
    client_stats = df.groupby("client_name").agg(
        proyectos=("total_amount", "count"),
        total_monto=("total_amount", "sum"),
        ticket_promedio=("total_amount", "mean"),
        margen_promedio=("margin_pct", "mean")
    ).reset_index()
    client_stats = client_stats.sort_values(by="total_monto", ascending=False)

    for _, r in client_stats.iterrows():
        cl = r["client_name"]
        cnt = int(r["proyectos"])
        tot = r["total_monto"]
        avg = r["ticket_promedio"]
        mrg = r["margen_promedio"]
        print(f"• {cl:<25} | {cnt:>3} Proyectos | Total: ${tot:>14,.0f} CLP | Ticket Prom: ${avg:>11,.0f} CLP | Margen: {mrg:>5.1f}%")

    # 2. HH Cost Structure by Domain
    print("\n--- 2. ESTRUCTURA ESTIMADA DE COSTO DE HH POR LÍNEA DE NEGOCIO ---")
    domain_stats = df.groupby("domain").agg(
        proyectos=("total_amount", "count"),
        total_monto=("total_amount", "sum"),
        costo_total=("cost_amount", "sum")
    ).reset_index()

    for _, r in domain_stats.iterrows():
        dom = r["domain"]
        cnt = int(r["proyectos"])
        tot = r["total_monto"]
        cost = r["costo_total"]
        hh_est_cost = cost * 0.65  # 65% of direct cost is HH
        hw_est_cost = cost * 0.35  # 35% is hardware
        print(f"• Línea {dom:<18} | {cnt:>3} Proy | Venta: ${tot:>14,.0f} CLP | Costo HH Est: ${hh_est_cost:>13,.0f} CLP")

    # 3. Internal Margin Capture Potential (HH Optimization of 35%)
    total_hh_cost = df["cost_amount"].sum() * 0.65
    hh_savings_potential = total_hh_cost * 0.35  # 35% reduction in HH hours via automation
    new_total_margin = (df["total_amount"].sum() - (df["cost_amount"].sum() - hh_savings_potential))
    new_margin_pct = (new_total_margin / df["total_amount"].sum()) * 100.0

    print("\n==========================================================================")
    print("💡 POTENCIAL DE CAPTURA INTERNA DE MARGEN (REDUCCIÓN 35% EN HH DE INGENIERÍA)")
    print("==========================================================================")
    print(f"• Costo Acumulado de HH (2025-2026):          ${total_hh_cost:,.0f} CLP")
    print(f"• Ahorro Directo de Costo de HH (Automatización): ${hh_savings_potential:,.0f} CLP (~${hh_savings_potential/1e6:.1f} MCLP)")
    print(f"• Margen Bruto Actual (Sin Optimizar):         {df['margin_pct'].mean():.1f}%")
    print(f"• Nuevo Margen Bruto Retenido Internamente:   {new_margin_pct:.1f}% (+{new_margin_pct - df['margin_pct'].mean():.1f}% de incremento directo)")
    print("==========================================================================")

if __name__ == "__main__":
    analyze_patterns()
