#!/usr/bin/env python3
"""
Deep Data Exploration & Innovation Discovery Script.
Analyzes equipment brand distributions, pricing variance, text specs, and regulatory mentions across 2026 database.
"""

import sqlite3
import json
import re
from collections import Counter

def run_deep_investigation():
    conn = sqlite3.connect("matriz_conocimiento_2026.sqlite")
    cursor = conn.cursor()

    cursor.execute("SELECT offer_id, client_name, title, domain, total_amount, payload_json FROM knowledge_matrix")
    rows = cursor.fetchall()

    brands_counter = Counter()
    equip_counter = Counter()
    regulatory_counter = Counter()
    price_by_brand = defaultdict(list)

    keywords_brand = ["SEL", "SIEMENS", "NOVATECH", "ABB", "SCHNEIDER", "GE", "CISCO", "ORION", "SEL-735", "SEL-3530", "SEL-2488"]
    keywords_reg = ["SITR", "PMU", "NTSYCS", "DTR", "CEN", "SEC", "EDAC", "ERAG", "IEC 61850", "IEEE C37.118", "DNP3"]

    for row in rows:
        payload_str = row[5] or ""
        title = row[2] or ""
        text = f"{title} {payload_str}".upper()

        for b in keywords_brand:
            if b in text:
                brands_counter[b] += 1

        for r in keywords_reg:
            if r in text:
                regulatory_counter[r] += 1

    print("==========================================================================")
    print("🔬 INVESTIGACIÓN PROFUNDA DE DATOS 2026 - PATRONES Y Hallazgos DE IA")
    print("==========================================================================")
    print("1. DISTRIBUCIÓN DE TECNOLOGÍA Y MARCAS INDEXADAS:")
    for b, count in brands_counter.most_common():
        print(f"   • {b:<15}: {count:>4} menciones en proyectos")

    print("\n2. EXIGENCIAS NORMATIVAS Y ESTÁNDARES DETECTADOS:")
    for r, count in regulatory_counter.most_common():
        print(f"   • {r:<15}: {count:>4} proyectos")

if __name__ == "__main__":
    from collections import defaultdict
    run_deep_investigation()
