#!/usr/bin/env python3
"""
2026 Commercial Portfolio Analytics & Margins Inspector.
Analyzes 2026 Knowledge Matrix database to extract financial stats, business line breakdowns,
key client portfolios, and margin optimization lessons.
"""

import sqlite3
import json
from collections import defaultdict
from pathlib import Path

def analyze_portfolio():
    db_path = Path("matriz_conocimiento_2026.sqlite")
    if not db_path.exists():
        print("Database matriz_conocimiento_2026.sqlite not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), SUM(total_amount), AVG(total_amount) FROM knowledge_matrix")
    total_count, sum_amount, avg_amount = cursor.fetchone()

    cursor.execute("SELECT domain, COUNT(*), SUM(total_amount), AVG(total_amount) FROM knowledge_matrix GROUP BY domain ORDER BY SUM(total_amount) DESC")
    domain_stats = cursor.fetchall()

    cursor.execute("SELECT client_name, COUNT(*), SUM(total_amount) FROM knowledge_matrix GROUP BY client_name ORDER BY SUM(total_amount) DESC LIMIT 15")
    client_stats = cursor.fetchall()


    print("==========================================================================")
    print("📊 INFORME ANALÍTICO DE INTELIGENCIA COMERCIAL - OFERTAS Y PROYECTOS 2026")
    print("==========================================================================")
    print(f"• Total Registros e Itemizados Indexados: {total_count:,}")
    print(f"• Monto Total de Ofertas Evaluadas: ${sum_amount:,.0f} CLP")
    print(f"• Ticket Promedio por Proyecto: ${avg_amount:,.0f} CLP\n")

    print("=== DISTRIBUCIÓN POR LÍNEA DE NEGOCIO ===")
    for domain, count, sum_val, avg_val in domain_stats:
        pct = (sum_val / sum_amount) * 100 if sum_amount else 0
        print(f"• {domain.upper():<22} | {count:>4} proyectos | Total: ${sum_val:>14,.0f} CLP ({pct:>5.1f}%) | Promedio: ${avg_val:>11,.0f} CLP")

    print("\n=== PRINCIPALES CLIENTES 2026 ===")
    for client, count, sum_val in client_stats:
        pct = (sum_val / sum_amount) * 100 if sum_amount else 0
        print(f"• {client:<35} | {count:>3} proyectos | Total: ${sum_val:>14,.0f} CLP ({pct:>5.1f}%)")

if __name__ == "__main__":
    analyze_portfolio()
