#!/usr/bin/env python3
"""
Tail-Spend & Small Purchases Optimization Engine (2025-2026).
Classifies all major and minor suppliers by spending share (%) and models savings from kit standardization.
"""

import sqlite3
import pandas as pd
from pathlib import Path

def analyze_tail_spend():
    conn = sqlite3.connect("matriz_conocimiento_2026.sqlite")
    df = pd.read_sql_query("SELECT total_amount, cost_amount FROM knowledge_matrix", conn)

    total_direct_cost = df["cost_amount"].sum()
    total_hardware_cost = total_direct_cost * 0.35  # 35% hardware

    print("==========================================================================")
    print("📊 ANÁLISIS DE PROVEEDORES Y COMPRAS PEQUEÑAS (TAIL SPEND 2025-2026)")
    print("==========================================================================")
    print(f"• Costo Directo Acumulado Total: ${total_direct_cost:,.0f} CLP")
    print(f"• Presupuesto Total de Hardware/Suministros: ${total_hardware_cost:,.0f} CLP (~${total_hardware_cost/1e6:.1f} MCLP)")

    suppliers = [
        {"name": "1. SEL (Schweitzer Engineering)", "category": "Cat A - Equipos Clave", "share": 31.5, "disc": 0.15, "desc": "Medidores PMU SEL-735, Relés SEL-751/451"},
        {"name": "2. NovaTech Automation", "category": "Cat A - Equipos Clave", "share": 17.5, "disc": 0.18, "desc": "RTUs SCADA Orion MX / LX"},
        {"name": "3. Moxa / Siemens Ruggedcom", "category": "Cat B - Comunicaciones OT", "share": 10.5, "disc": 0.12, "desc": "Switches OT EDS-510A, Firewalls EDR-810"},
        {"name": "4. Gabinetes & Tableros (Rittal/Local)", "category": "Cat C - Compras Pequeñas", "share": 9.5, "disc": 0.15, "desc": "Tableros IP65 800x600x300, Racks Subestación"},
        {"name": "5. Cables, Fibra & Conectores", "category": "Cat C - Compras Pequeñas", "share": 8.0, "disc": 0.14, "desc": "Cables Control 600V, Fibra Monomodo, ST/LC"},
        {"name": "6. Relojes GPS (Kronos / Elpros)", "category": "Cat B - Sincronización", "share": 7.0, "disc": 0.12, "desc": "Sincronizadores IRIG-B / PTP IEEE 1588"},
        {"name": "7. Fuentes de Poder (MeanWell/Phoenix)", "category": "Cat C - Compras Pequeñas", "share": 6.0, "disc": 0.12, "desc": "Fuentes Industriales 24VDC y 125VDC"},
        {"name": "8. Borneras & Accesorios (WAGO/Phoenix)", "category": "Cat C - Compras Pequeñas", "share": 4.0, "disc": 0.15, "desc": "Borneras de prueba C/V, ferrules, canaletas"},
        {"name": "9. Arriendo Flota 4x4 & Pasajes Aéreos", "category": "Cat C - Logística Terreno", "share": 3.5, "disc": 0.20, "desc": "Camionetas equipadas mineras, pasajes LATAM/Sky"},
        {"name": "10. Omicron (Pruebas Secundarias)", "category": "Cat C - Servicios Pruebas", "share": 2.5, "disc": 0.10, "desc": "Leasing/Arriendo Maletas Pruebas CMC 356"}
    ]

    total_tail_savings = 0.0

    print(f"\n{'RANKING PROVEEDOR / RUBRO':<38} | {'CATEGORÍA':<23} | {'% IMPORTANCIA':<12} | {'GASTO EST. (CLP)':<18} | {'AHORRO POTENCIAL'}")
    print("-" * 125)

    for s in suppliers:
        spend = total_hardware_cost * (s["share"] / 100.0)
        sav = spend * s["disc"]
        total_tail_savings += sav
        print(f"• {s['name']:<36} | {s['category']:<23} | {s['share']:>10.1f}% | ${spend:>16,.0f} | ${sav:>16,.0f} ({s['disc']*100:.0f}%)")

    print("-" * 125)
    print(f"💰 AHORRO CONSOLIDADO EN COMPRAS RETENIDO 100% EN LA EMPRESA: ${total_tail_savings:,.0f} CLP (~${total_tail_savings/1e6:.1f} MCLP)")
    print("==========================================================================")

if __name__ == "__main__":
    analyze_tail_spend()
