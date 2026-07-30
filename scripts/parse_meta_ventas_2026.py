#!/usr/bin/env python3
"""
Exhaustive Parser for Meta Ventas y Ocs 2026.xlsx.
Calculates:
- Meta Anual 2026 (MCLP) vs Proyección Actual vs OCs Adjudicadas.
- Conversion Win Rate by Month, Business Line (Normativo, SCADA, PAC), and Client.
"""

import pandas as pd
import openpyxl
from pathlib import Path
from collections import defaultdict

def parse_excel():
    file_path = Path("meta_ventas_2026.xlsx")
    xl = pd.ExcelFile(file_path)

    print("==========================================================================")
    print("🎯 INFORME COMPLETO: METAS DE VENTAS, OCS Y CONVERSIÓN REAL 2026")
    print("==========================================================================")

    # 1. Inspect 'Resumen' Sheet
    df_resumen = pd.read_excel(file_path, sheet_name="Resumen")
    print("\n--- HOJA RESUMEN (Primeras 20 filas) ---")
    print(df_resumen.iloc[:20, :10].to_string())

    # 2. Iterate through Monthly Projection Sheets to sum Quoted vs Won (OCs)
    monthly_sheets = [s for s in xl.sheet_names if "Proyección" in s or "Flujo" in s]

    total_quoted_mclp = 0.0
    total_won_mclp = 0.0
    total_lost_mclp = 0.0
    total_pipeline_mclp = 0.0

    by_line_quoted = defaultdict(float)
    by_line_won = defaultdict(float)
    by_client_quoted = defaultdict(float)
    by_client_won = defaultdict(float)

    all_opportunities = []

    for sheet in monthly_sheets:
        df = pd.read_excel(file_path, sheet_name=sheet)
        
        # Identify outcome column
        res_col = [c for c in df.columns if "Resultado" in str(c)]
        outcome_col = res_col[0] if res_col else None

        for idx, row in df.iterrows():
            linea = str(row.get("Línea") or "").strip()
            op = str(row.get("Oportunidad") or "").strip()
            cliente = str(row.get("Cliente") or "").strip()
            ingreso_exp = row.get("Ingreso esperado")
            prob = row.get("Probabilidad")
            outcome = str(row.get(outcome_col) or "") if outcome_col else ""

            if not linea or pd.isna(ingreso_exp) or str(ingreso_exp).strip().lower() == "nan":
                continue

            try:
                ingreso_val = float(ingreso_exp)
            except ValueError:
                continue

            if ingreso_val <= 0:
                continue

            total_quoted_mclp += ingreso_val
            by_line_quoted[linea] += ingreso_val
            if cliente and cliente != "nan":
                by_client_quoted[cliente] += ingreso_val

            is_won = any(w in outcome.upper() for w in ["OC", "GANADA", "ADJUDICADA", "CERRADA", "SI"])
            is_lost = any(l in outcome.upper() for l in ["PERDIDA", "NO", "RECHAZADA", "PERDIDAS"])

            if is_won:
                total_won_mclp += ingreso_val
                by_line_won[linea] += ingreso_val
                if cliente and cliente != "nan":
                    by_client_won[cliente] += ingreso_val
            elif is_lost:
                total_lost_mclp += ingreso_val
            else:
                total_pipeline_mclp += ingreso_val

            all_opportunities.append({
                "sheet": sheet,
                "linea": linea,
                "oportunidad": op,
                "cliente": cliente,
                "monto_mclp": ingreso_val,
                "outcome": outcome,
                "is_won": is_won
            })

    print("\n==========================================================================")
    print("📊 RESULTADOS CONSOLIDADOS DE OPORTUNIDADES 2026")
    print("==========================================================================")
    print(f"• Total Oportunidades Evaluadas: {len(all_opportunities)}")
    print(f"• Monto Total Cotizado/Proyectado: ${total_quoted_mclp:,.1f} MCLP (${total_quoted_mclp * 1e6:,.0f} CLP)")
    print(f"• Monto Total Vendido (OCs Adjudicadas): ${total_won_mclp:,.1f} MCLP (${total_won_mclp * 1e6:,.0f} CLP)")
    print(f"• Monto en Pipeline / En Negociación: ${total_pipeline_mclp:,.1f} MCLP (${total_pipeline_mclp * 1e6:,.0f} CLP)")

    win_rate = (total_won_mclp / total_quoted_mclp * 100) if total_quoted_mclp > 0 else 0
    print(f"• Tasa de Conversión Real (Win-Rate): {win_rate:.1f}%")

    print("\n=== CONVERSIÓN POR LÍNEA DE NEGOCIO ===")
    for linea, q_val in by_line_quoted.items():
        w_val = by_line_won[linea]
        w_rate = (w_val / q_val * 100) if q_val > 0 else 0
        print(f"• {linea:<15} | Cotizado: ${q_val:>7.1f} MCLP | Vendido (OC): ${w_val:>7.1f} MCLP | Win-Rate: {w_rate:>5.1f}%")

    print("\n=== TOP CLIENTES CONVERSIÓN (VENDIDO) ===")
    sorted_clients = sorted(by_client_won.items(), key=lambda x: x[1], reverse=True)[:10]
    for cliente, w_val in sorted_clients:
        q_val = by_client_quoted[cliente]
        w_rate = (w_val / q_val * 100) if q_val > 0 else 0
        print(f"• {cliente:<30} | Cotizado: ${q_val:>7.1f} MCLP | Vendido (OC): ${w_val:>7.1f} MCLP | Win-Rate: {w_rate:>5.1f}%")

if __name__ == "__main__":
    parse_excel()
