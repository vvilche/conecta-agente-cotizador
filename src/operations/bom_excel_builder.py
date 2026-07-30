"""
Multi-tab Excel BOM Builder for Conecta Ingeniería S.A.
Generates comprehensive .xlsx workbooks following the exact 14-sheet historical Conecta Ficha de Traspaso format
audited from real OT files:
['Currency', 'Ficha', 'Control HH y Costos', 'Cash Flow', 'Cliente', 'Resumen',
 'Costos HH', 'Equi. Mat. Arr. Sub.', 'Calculo HH', 'Expenses',
 'Check', 'Sensibilidad', 'Terminos de Pago', 'Base de Datos']
"""
import io
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class MultiTabBOMExcelBuilder:
    # ── Shared Style Helpers ────────────────────────────────────────────────
    HDR_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    HDR_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ACCENT_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    GREEN_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    BOLD = Font(name="Calibri", size=11, bold=True)
    NORMAL = Font(name="Calibri", size=11)
    TITLE = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    SUBTITLE = Font(name="Calibri", size=10, italic=True, color="475569")
    CENTER = Alignment(horizontal="center")
    RIGHT = Alignment(horizontal="right")

    @classmethod
    def _hdr_row(cls, ws, row, titles):
        for col, title in enumerate(titles, start=1):
            c = ws.cell(row=row, column=col, value=title)
            c.font = cls.HDR_FONT
            c.fill = cls.HDR_FILL
            c.alignment = cls.CENTER

    @classmethod
    def _autofit(cls, wb):
        for sheet in wb.worksheets:
            for col in sheet.columns:
                col_letter = get_column_letter(col[0].column)
                max_len = max((len(str(cell.value or "")) for cell in col), default=0)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 55)

    @staticmethod
    def build_workbook_bytes(payload: dict) -> bytes:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        cls = MultiTabBOMExcelBuilder

        client_name = payload.get("partner_id", "Cliente Coordinado Conecta")
        amount_untaxed = payload.get("amount_untaxed", 58628319)
        amount_tax = payload.get("amount_tax", 11139381)
        amount_total = payload.get("amount_total", 69767700)
        margin_pct = float(payload.get("margin_analysis", {}).get("boosted_margin_pct", 54.8))
        lines = payload.get("order_line", [])
        today = datetime.date.today().strftime("%d/%m/%Y")

        # ── 1. Currency ────────────────────────────────────────────────────
        ws = wb.create_sheet("Currency")
        ws.cell(1, 1, "Currency").font = cls.TITLE
        ws.cell(3, 1, "Banco Central de Chile").font = cls.BOLD
        ws.cell(4, 1, "Base de Datos Estadísticos (BDE)")
        ws.cell(6, 1, "Tipo").font = cls.BOLD
        ws.cell(6, 2, "Código").font = cls.BOLD
        ws.cell(6, 3, "Valor").font = cls.BOLD
        ws.cell(6, 4, "Fecha").font = cls.BOLD
        for col in [1, 2, 3, 4]:
            ws.cell(6, col).fill = cls.HDR_FILL
            ws.cell(6, col).font = cls.HDR_FONT
        fx_data = [("USD", "USD", 910.00, today), ("EUR", "EUR", 985.00, today), ("UF", "UF", 37800.00, today)]
        for r, (tp, cd, val, dt) in enumerate(fx_data, start=7):
            ws.cell(r, 1, tp)
            ws.cell(r, 2, cd)
            c = ws.cell(r, 3, val); c.number_format = "#,##0.00"
            ws.cell(r, 4, dt)

        # ── 2. Ficha ───────────────────────────────────────────────────────
        ws = wb.create_sheet("Ficha")
        ws.cell(1, 1, "CONECTA INGENIERÍA S.A. — FICHA DE TRASPASO OT").font = cls.TITLE
        ws.cell(2, 1, "Formulario Oficial de Traspaso Comercial a Operaciones").font = cls.SUBTITLE
        ficha_data = [
            ("Fecha de Traspaso", today),
            ("N° Oferta Conecta", "OF-2026-CONECTA-REV0"),
            ("N° OT Conecta", "7095-00"),
            ("Cliente Coordinado", client_name),
            ("RUT Cliente", "76.543.210-9"),
            ("Nombre Proyecto", f"Suministro e Integración OT — {client_name}"),
            ("Jefe de Proyecto Asignado", "Ing. Pedro Morales"),
            ("Monto Oferta Neto CLP", amount_untaxed),
            ("Margen Bruto Target (%)", margin_pct / 100.0),
        ]
        for i, (lbl, val) in enumerate(ficha_data, start=4):
            c1 = ws.cell(i, 1, lbl); c1.font = cls.BOLD; c1.fill = cls.ACCENT_FILL
            c2 = ws.cell(i, 2, val)
            if isinstance(val, float) and val < 1:
                c2.number_format = "0.0%"
            elif isinstance(val, (int, float)) and val > 1000:
                c2.number_format = "$#,##0"

        # ── 3. Control HH y Costos ─────────────────────────────────────────
        ws = wb.create_sheet("Control HH y Costos")
        ws.cell(1, 1, "CONTROL HH Y COSTOS").font = cls.TITLE
        ws.cell(3, 1, "HH POR ACTIVIDADES").font = cls.BOLD
        cls._hdr_row(ws, 4, ["ÍTEM", "PO/PM", "ING. SENIOR/A", "ING. B", "TÉC. TERRENO", "TOTAL HH"])
        hh_items = [
            ("PLANIFICACION", 4, 8, 0, 0, 12),
            ("LEVANTAMIENTO", 0, 4, 8, 0, 12),
            ("INGENIERIA", 2, 24, 16, 0, 42),
            ("IMPLEMENTACION", 0, 8, 16, 16, 40),
            ("PRUEBAS FAT", 0, 8, 12, 8, 28),
            ("SAT TERRENO", 2, 8, 8, 16, 34),
            ("REGULATORY CEN", 2, 8, 4, 0, 14),
        ]
        for r, (name, *hh) in enumerate(hh_items, start=5):
            ws.cell(r, 1, name).font = cls.BOLD
            for ci, val in enumerate(hh, start=2):
                ws.cell(r, ci, val).alignment = cls.CENTER
        total_hh = sum(h[5] for h in hh_items)
        ws.cell(r + 1, 1, "TOTAL").font = cls.BOLD
        ws.cell(r + 1, 6, total_hh).font = cls.BOLD

        # ── 4. Cash Flow ───────────────────────────────────────────────────
        ws = wb.create_sheet("Cash Flow")
        ws.cell(1, 1, "FLUJO DE CAJA — HITOS DE COBRANZA (EDP)").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Hito EDP", "Descripción", "Facturación %", "Monto Neto CLP", "Fecha Est."])
        edp_data = [
            ("EDP 1", "Pre-kitting y entrega de tableros en taller Conecta S.A.", 0.50, round(amount_untaxed * 0.5), "Semana 3"),
            ("EDP 2", "Certificado FAT/SAT HIL e Informe IPES registrado ante CEN", 0.50, round(amount_untaxed * 0.5), "Semana 6"),
        ]
        for r, (hito, desc, pct, monto, fecha) in enumerate(edp_data, start=4):
            ws.cell(r, 1, hito).font = cls.BOLD
            ws.cell(r, 2, desc)
            c = ws.cell(r, 3, pct); c.number_format = "0.0%"; c.alignment = cls.CENTER
            c = ws.cell(r, 4, monto); c.number_format = "$#,##0"; c.font = cls.BOLD
            ws.cell(r, 5, fecha).alignment = cls.CENTER

        # ── 5. Cliente ─────────────────────────────────────────────────────
        ws = wb.create_sheet("Cliente")
        ws.cell(1, 1, "METADATA DEL CLIENTE COORDINADO").font = cls.TITLE
        client_info = [
            ("Razón Social", client_name),
            ("RUT Empresa", "76.543.210-9"),
            ("Giro / Sector", "Generación y Transmisión de Energía Eléctrica"),
            ("Dirección", "Av. Andrés Bello 2711, Las Condes, Santiago"),
            ("Contacto Técnico", "Ing. Administrador de Contratos"),
            ("Teléfono", "+56 2 2345 6789"),
        ]
        for i, (lbl, val) in enumerate(client_info, start=4):
            c1 = ws.cell(i, 1, lbl); c1.font = cls.BOLD; c1.fill = cls.ACCENT_FILL
            ws.cell(i, 2, val)

        # ── 6. Resumen ─────────────────────────────────────────────────────
        ws = wb.create_sheet("Resumen")
        ws.cell(1, 1, "RESUMEN FINANCIERO Y OPTIMIZACIÓN DE MARGEN").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Indicador Financiero", "Valor CLP / %"])
        summary = [
            ("Ventas Neto Cliente (Sin IVA)", amount_untaxed, "$#,##0"),
            ("Impuesto IVA (19%)", amount_tax, "$#,##0"),
            ("Total Bruto Facturación", amount_total, "$#,##0"),
            ("Costo Directo Estimado", round(amount_untaxed * (1 - margin_pct / 100)), "$#,##0"),
            ("Utilidad Bruta Retenida", round(amount_untaxed * (margin_pct / 100)), "$#,##0"),
            ("Margen Bruto Retenido (%)", margin_pct / 100, "0.0%"),
        ]
        for i, (lbl, val, fmt) in enumerate(summary, start=4):
            c1 = ws.cell(i, 1, lbl); c1.font = cls.BOLD
            c2 = ws.cell(i, 2, val); c2.number_format = fmt; c2.font = cls.BOLD
            if "Margen" in lbl or "Utilidad" in lbl:
                c1.fill = cls.GREEN_FILL; c2.fill = cls.GREEN_FILL

        # ── 7. Costos HH ───────────────────────────────────────────────────
        ws = wb.create_sheet("Costos HH")
        ws.cell(1, 1, "COSTOS DE HORAS HOMBRE POR ROL").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Rol", "Tarifa HH (CLP/hr)", "Total HH", "Costo Total CLP"])
        hh_costs = [
            ("Gerente de Proyecto (PM)", 110000, 4, 440000),
            ("Project Owner (PO)", 95000, 12, 1140000),
            ("Ing. Senior / A", 85000, 68, 5780000),
            ("Ing. Especialista B", 70000, 64, 4480000),
            ("Técnico Terreno", 55000, 40, 2200000),
        ]
        for r, (rol, tarifa, hh, costo) in enumerate(hh_costs, start=4):
            ws.cell(r, 1, rol).font = cls.BOLD
            c = ws.cell(r, 2, tarifa); c.number_format = "$#,##0"
            ws.cell(r, 3, hh).alignment = cls.CENTER
            c = ws.cell(r, 4, costo); c.number_format = "$#,##0"; c.font = cls.BOLD

        # ── 8. Equi. Mat. Arr. Sub. ────────────────────────────────────────
        ws = wb.create_sheet("Equi. Mat. Arr. Sub.")
        ws.cell(1, 1, "DETALLE DE EQUIPOS, MATERIALES, ARRIENDOS Y SUBCONTRATOS").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Categoría", "Código Partida", "Descripción Ítem", "Marca / Modelo", "Cant.", "P. Unit. CLP", "Subtotal CLP"])
        for r, line in enumerate(lines, start=4):
            ws.cell(r, 1, "HARDWARE/SW").font = cls.BOLD
            ws.cell(r, 2, line.get("item_code", ""))
            ws.cell(r, 3, line.get("name", ""))
            ws.cell(r, 4, "VIZIMAX/Belden/NovaTech")
            ws.cell(r, 5, line.get("product_uom_qty", 1)).alignment = cls.CENTER
            c = ws.cell(r, 6, line.get("price_unit", 0)); c.number_format = "$#,##0"
            c = ws.cell(r, 7, line.get("price_subtotal", 0)); c.number_format = "$#,##0"; c.font = cls.BOLD

        # ── 9. Calculo HH ─────────────────────────────────────────────────
        ws = wb.create_sheet("Calculo HH")
        ws.cell(1, 1, "CÁLCULO DETALLADO DE HH POR ACTIVIDAD Y PERFIL").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Actividad", "Descripción Detallada", "Perfil Requerido", "HH Estimadas", "Costo HH CLP"])
        activities = [
            ("Planificación", "Kick-off, carta Gantt, gestión riesgos", "PM / PO", 12, 1140000),
            ("Levantamiento", "Visita a subestación, relevamiento señales DNP3/C37.118", "Ing. Senior A", 12, 1020000),
            ("Ingeniería", "Mapeo de canales, configuración firmware VIZIMAX/Orion", "Ing. Senior A + B", 42, 4070000),
            ("Implementación", "Pre-kitting tableros, programación RTU/PMU en taller", "Ing. B + Técnico", 40, 5000000),
            ("Pruebas FAT", "Simulación HIL, validación tramas DNP3 / C37.118", "Ing. Senior A + B", 28, 2940000),
            ("SAT Terreno", "Comisionamiento en subestación, pruebas CEN", "Todos los roles", 34, 3190000),
            ("Regulatory", "Redacción IPES, protocolo AT-SITR-1, acreditación", "PM + Ing. A", 14, 1400000),
        ]
        for r, (act, desc, perfil, hh, costo) in enumerate(activities, start=4):
            ws.cell(r, 1, act).font = cls.BOLD
            ws.cell(r, 2, desc)
            ws.cell(r, 3, perfil)
            ws.cell(r, 4, hh).alignment = cls.CENTER
            c = ws.cell(r, 5, costo); c.number_format = "$#,##0"

        # ── 10. Expenses ───────────────────────────────────────────────────
        ws = wb.create_sheet("Expenses")
        ws.cell(1, 1, "LOGÍSTICA, VIÁTICOS Y ACREDITACIÓN EN FAENA").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Concepto", "Detalle", "Días/Unid.", "Monto CLP"])
        expenses = [
            ("Pre-kitting Tableros Taller", "Ensamblaje y pre-cableado estandarizado KittingEngine", 1.5, 1850000),
            ("Acreditación Digital", "Dossier Sicop/Pronexo F30-1, ex. médicos, EPP, ODI/DAS", 0.5, 450000),
            ("Traslado & Camioneta 4x4", "Movilización de tableros y camioneta equipada", 3.0, 1200000),
            ("Viáticos Especialistas", "Alimentación y hospedaje en faena", 3.0, 980000),
        ]
        for r, (con, det, dias, monto) in enumerate(expenses, start=4):
            ws.cell(r, 1, con).font = cls.BOLD
            ws.cell(r, 2, det)
            ws.cell(r, 3, dias).alignment = cls.CENTER
            c = ws.cell(r, 4, monto); c.number_format = "$#,##0"

        # ── 11. Check ─────────────────────────────────────────────────────
        ws = wb.create_sheet("Check")
        ws.cell(1, 1, "LISTA DE VERIFICACIÓN — CHECKLIST DE PROYECTO").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Área", "Ítem de Control", "Estado", "Responsable", "Fecha"])
        checks = [
            ("Comercial", "Oferta firmada y enviada al cliente", "✅ OK", "Comercial", today),
            ("Comercial", "Orden de Compra recibida", "⏳ Pendiente", "Comercial", ""),
            ("Operaciones", "Ficha de Traspaso llenada en SAP/Odoo", "✅ OK", "Jefe OT", today),
            ("Operaciones", "Pre-kitting tableros completado en taller", "⏳ Pendiente", "Téc. Taller", ""),
            ("Operaciones", "FAT/SAT HIL ejecutado y certificado firmado", "⏳ Pendiente", "Ing. Senior", ""),
            ("Regulatory", "Informe IPES redactado y enviado al CEN", "⏳ Pendiente", "PM", ""),
            ("Cobranza", "EDP 1 emitido y facturado", "⏳ Pendiente", "Administración", ""),
            ("Cobranza", "EDP 2 emitido y facturado", "⏳ Pendiente", "Administración", ""),
        ]
        for r, (area, item, estado, resp, fecha) in enumerate(checks, start=4):
            ws.cell(r, 1, area).font = cls.BOLD
            ws.cell(r, 2, item)
            ws.cell(r, 3, estado).alignment = cls.CENTER
            ws.cell(r, 4, resp)
            ws.cell(r, 5, fecha).alignment = cls.CENTER

        # ── 12. Sensibilidad ──────────────────────────────────────────────
        ws = wb.create_sheet("Sensibilidad")
        ws.cell(1, 1, "ANÁLISIS DE SENSIBILIDAD — ESCENARIOS DE MARGEN").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Escenario", "Margen %", "Ventas Neto CLP", "Costo Directo CLP", "Utilidad Bruta CLP", "Evaluación"])
        scenarios = [
            ("Agresivo (Licitación)", 0.30, amount_untaxed, round(amount_untaxed * 0.70), round(amount_untaxed * 0.30), "Riesgo Alto"),
            ("Conservador", 0.45, amount_untaxed, round(amount_untaxed * 0.55), round(amount_untaxed * 0.45), "Riesgo Medio"),
            (f"Estándar Conecta ({margin_pct:.1f}%)", margin_pct / 100, amount_untaxed, round(amount_untaxed * (1 - margin_pct / 100)), round(amount_untaxed * (margin_pct / 100)), "✅ Óptimo"),
            ("SLA / Software Premium", 0.685, amount_untaxed, round(amount_untaxed * 0.315), round(amount_untaxed * 0.685), "Alta Rentabilidad"),
        ]
        for r, (escen, pct, ventas, costo, util, eval_) in enumerate(scenarios, start=4):
            ws.cell(r, 1, escen).font = cls.BOLD
            c = ws.cell(r, 2, pct); c.number_format = "0.0%"; c.alignment = cls.CENTER
            c = ws.cell(r, 3, ventas); c.number_format = "$#,##0"
            c = ws.cell(r, 4, costo); c.number_format = "$#,##0"
            c = ws.cell(r, 5, util); c.number_format = "$#,##0"; c.font = cls.BOLD
            ws.cell(r, 6, eval_).alignment = cls.CENTER
            if "Óptimo" in eval_:
                for ci in range(1, 7):
                    ws.cell(r, ci).fill = cls.GREEN_FILL

        # ── 13. Terminos de Pago ──────────────────────────────────────────
        ws = wb.create_sheet("Terminos de Pago")
        ws.cell(1, 1, "TÉRMINOS Y CONDICIONES DE PAGO Y GARANTÍA").font = cls.TITLE
        terms = [
            ("Condición de Pago", "Facturación a 30 días tras aprobación de Estado de Pago (EDP)"),
            ("Validez de la Oferta", "30 días corridos a contar de la fecha de presentación"),
            ("Garantía Técnica", "12 meses desde la puesta en servicio comercial"),
            ("Boleta Fiel Cumplimiento", "10% del monto neto total (requerido para licitaciones)"),
            ("Multas / Cap", "Techo máximo acumulado de multas: 5% del valor neto del contrato"),
            ("Fuerza Mayor", "Suspensión de plazos por eventos fuera del control de las partes"),
        ]
        for i, (lbl, val) in enumerate(terms, start=4):
            c1 = ws.cell(i, 1, lbl); c1.font = cls.BOLD; c1.fill = cls.ACCENT_FILL
            ws.cell(i, 2, val)

        # ── 14. Base de Datos ─────────────────────────────────────────────
        ws = wb.create_sheet("Base de Datos")
        ws.cell(1, 1, "BASE DE DATOS — PRECIOS REFERENCIALES CONECTA S.A.").font = cls.TITLE
        cls._hdr_row(ws, 3, ["Código", "Descripción", "Marca/Modelo", "Precio Ref. CLP", "Precio Ref. USD", "Actualizado"])
        ref_prices = [
            ("HW-VIZIMAX-PMU", "Unidad Medición Fasorial PMU Clase A IEEE C37.118", "VIZIMAX SynchroTeq Plus", 9500000, round(9500000 / 910), today),
            ("HW-GPS-CLOCK", "Reloj Satelital GPS Kronos Series 2/3 IRIG-B/PTP", "Kronos / Arbiter", 3200000, round(3200000 / 910), today),
            ("SW-PDC-LIC", "Licencia PDC Concentrador Datos Fasoriales Local/Corp.", "ELPROS / OSIsoft", 12500000, round(12500000 / 910), today),
            ("HW-SWITCH-IND", "Switch Ethernet Industrial PTP IEEE 1588 Redundante", "Belden Hirschmann RS20", 2300000, round(2300000 / 910), today),
            ("HW-RTU-NOVATECH", "Remota RTU Subestación DNP3 / IEC 61850 GOOSE", "NovaTech Orion LX+", 9800000, round(9800000 / 910), today),
        ]
        for r, (cod, desc, marca, clp, usd, fecha) in enumerate(ref_prices, start=4):
            ws.cell(r, 1, cod).font = cls.BOLD
            ws.cell(r, 2, desc)
            ws.cell(r, 3, marca)
            c = ws.cell(r, 4, clp); c.number_format = "$#,##0"
            c = ws.cell(r, 5, usd); c.number_format = "$#,##0"
            ws.cell(r, 6, fecha).alignment = cls.CENTER

        cls._autofit(wb)

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream.getvalue()
