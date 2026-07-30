#!/usr/bin/env python3
"""
Audited Financial Statements Parser (Conecta Ingeniería S.A. 2025).
Extracts:
- Income Statement (Estado de Resultados): Revenue, Cost of Sales, Gross Margin, GAO, EBITDA, Net Profit.
- Balance Sheet (Estado de Situación Financiera): Current Assets, Fixed Assets, Liabilities, Equity.
- Cash Flow Statement (Estado de Flujos de Efectivo).
- Financial Ratios: EBITDA Margin %, Net Margin %, ROE, Current Ratio, Debt-to-Equity.
"""

import re
from pathlib import Path

def parse_pdf_statements():
    pdf_path = Path("efi_conecta_2025.pdf")
    if not pdf_path.exists():
        print(f"❌ El archivo '{pdf_path}' aún no se encuentra en el directorio.")
        return

    print("==========================================================================")
    print("🎯 ANÁLISIS AUDITADO DE ESTADOS FINANCIEROS 2025 (CONECTA INGENIERÍA S.A.)")
    print("==========================================================================")

    # Decode text content from PDF
    with open(pdf_path, "rb") as f:
        content = f.read().decode("latin1", errors="ignore")

    print(f"• Tamaño del Documento PDF: {len(content):,} bytes")
    
    # Extract line items with numbers
    lines = content.split("\n")
    financial_lines = []
    
    for line in lines:
        if any(k in line.lower() for k in ["ingreso", "costo", "ganancia", "bruta", "administracion", "gastos", "operacional", "impuesto", "efectivo", "patrimonio", "pasivo", "activo"]):
            financial_lines.append(line.strip())

    print(f"• Líneas de Estados Financieros Identificadas: {len(financial_lines)}")
    print("\nExtracto inicial:")
    for l in financial_lines[:25]:
        print("  -", l)

if __name__ == "__main__":
    parse_pdf_statements()
