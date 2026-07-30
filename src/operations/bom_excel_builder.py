"""
Multi-tab Excel BOM Builder for Conecta Ingeniería S.A.
Generates comprehensive .xlsx workbooks following the exact 9-sheet historical Conecta Ficha de Traspaso format:
['Ficha', 'Resumen', 'Control HH y Costos', 'Equi. Mat. Arr. Sub.', 'Cash Flow', 'Cliente', 'Expenses y Logistica', 'Terminos de Pago', 'Check y Sensibilidad']
"""
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class MultiTabBOMExcelBuilder:
    @staticmethod
    def build_workbook_bytes(payload: dict) -> bytes:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet

        client_name = payload.get("partner_id", "Cliente Coordinado Conecta")
        amount_untaxed = payload.get("amount_untaxed", 58628319)
        amount_tax = payload.get("amount_tax", 11139381)
        amount_total = payload.get("amount_total", 69767700)
        margin_pct = payload.get("margin_analysis", {}).get("boosted_margin_pct", 54.8)
        lines = payload.get("order_line", [])

        # Color Palette - Conecta Corporate Dark Blue
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        accent_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        bold_font = Font(name="Calibri", size=11, bold=True)
        normal_font = Font(name="Calibri", size=11)
        title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
        subtitle_font = Font(name="Calibri", size=11, italic=True, color="475569")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # -------------------------------------------------------------
        # SHEET 1: Ficha (Ficha de Traspaso Comercial a Operaciones)
        # -------------------------------------------------------------
        ws1 = wb.create_sheet(title="Ficha")
        ws1.views.sheetView[0].showGridLines = True
        ws1.cell(row=1, column=1, value="CONECTA INGENIERÍA S.A. — FICHA DE TRASPASO OT").font = title_font
        ws1.cell(row=2, column=1, value="Formulario Oficial de Traspaso Comercial a Operaciones").font = subtitle_font

        ficha_data = [
            ("Fecha de Traspaso", "30/07/2026"),
            ("N° Oferta Conecta", "OF-2026-CONECTA-REV0"),
            ("N° OT Conecta", "OT 7095-00"),
            ("Cliente Coordinado", client_name),
            ("RUT Cliente", "76.543.210-9"),
            ("Nombre Proyecto", f"Suministro e Integración OT - {client_name}"),
            ("Jefe de Proyecto Asignado", "Ing. Pedro Morales / Jefe de Terreno"),
            ("Monto Oferta Neto CLP", f"${amount_untaxed:,.0f} CLP"),
            ("Margen Bruto Target", f"{margin_pct:.1f}%")
        ]
        for idx, (lbl, val) in enumerate(ficha_data, start=4):
            c1 = ws1.cell(row=idx, column=1, value=lbl)
            c1.font = bold_font
            c1.fill = accent_fill
            c2 = ws1.cell(row=idx, column=2, value=val)
            c2.font = normal_font

        # -------------------------------------------------------------
        # SHEET 2: Resumen (Planilla Resumen de Oferta y Rentabilidad)
        # -------------------------------------------------------------
        ws2 = wb.create_sheet(title="Resumen")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="RESUMEN FINANCIERO Y OPTIMIZACIÓN DE MARGEN").font = title_font

        summary_data = [
            ("Ventas Neto Cliente (Sin IVA)", amount_untaxed, "$#,##0"),
            ("Impuesto IVA (19%)", amount_tax, "$#,##0"),
            ("Total Bruto Facturación", amount_total, "$#,##0"),
            ("Costo Directo Estimado", round(amount_untaxed * (1.0 - margin_pct/100.0)), "$#,##0"),
            ("Utilidad Bruta Retenida", round(amount_untaxed * (margin_pct/100.0)), "$#,##0"),
            ("Margen Bruto Retenido (%)", margin_pct / 100.0, "0.0%")
        ]
        ws2.cell(row=3, column=1, value="Indicador Financiero").font = header_font
        ws2.cell(row=3, column=1).fill = header_fill
        ws2.cell(row=3, column=2, value="Valor CLP / %").font = header_font
        ws2.cell(row=3, column=2).fill = header_fill

        for idx, (lbl, val, fmt) in enumerate(summary_data, start=4):
            c_l = ws2.cell(row=idx, column=1, value=lbl)
            c_l.font = bold_font
            c_v = ws2.cell(row=idx, column=2, value=val)
            c_v.font = bold_font
            c_v.number_format = fmt
            if "Margen" in lbl or "Utilidad" in lbl:
                c_l.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                c_v.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")

        # -------------------------------------------------------------
        # SHEET 3: Control HH y Costos
        # -------------------------------------------------------------
        ws3 = wb.create_sheet(title="Control HH y Costos")
        ws3.views.sheetView[0].showGridLines = True
        ws3.cell(row=1, column=1, value="CONTROL DE HORAS HOMBRE (HH) POR ACTIVIDAD Y ESPECIALIDAD").font = title_font

        headers3 = ["Actividad / Etapa", "PM / PO", "Ing. Senior A", "Ing. Especialista B", "Técnico Terreno", "Total HH", "Costo HH CLP"]
        for c_idx, h in enumerate(headers3, start=1):
            c = ws3.cell(row=3, column=c_idx, value=h)
            c.font = header_font
            c.fill = header_fill

        hh_matrix = [
            ("PLANIFICACIÓN & GESTIÓN", 4, 8, 12, 0, 24, 2640000),
            ("INGENIERÍA & MAPEO DNP3/C37.118", 2, 24, 34, 0, 60, 6600000),
            ("PRUEBAS HIL FAT TALLER", 0, 12, 16, 8, 36, 3960000),
            ("MONTAJE & PRE-KITTING TABLEROS", 0, 0, 8, 16, 24, 2400000),
            ("COMISIONAMIENTO SAT TERRENO", 4, 16, 16, 16, 52, 6240000),
            ("REGULATORY & IPES CEN/SEC", 2, 10, 8, 0, 20, 2200000)
        ]
        for r_idx, r_data in enumerate(hh_matrix, start=4):
            ws3.cell(row=r_idx, column=1, value=r_data[0]).font = bold_font
            for c_i in range(1, 6):
                ws3.cell(row=r_idx, column=c_i+1, value=r_data[c_i]).alignment = Alignment(horizontal="center")
            c_cost = ws3.cell(row=r_idx, column=7, value=r_data[6])
            c_cost.number_format = "$#,##0"
            c_cost.font = bold_font

        # -------------------------------------------------------------
        # SHEET 4: Equi. Mat. Arr. Sub. (Equipos, Materiales y Subcontratos)
        # -------------------------------------------------------------
        ws4 = wb.create_sheet(title="Equi. Mat. Arr. Sub.")
        ws4.views.sheetView[0].showGridLines = True
        ws4.cell(row=1, column=1, value="DETALLE DE EQUIPOS, MATERIALES, ARRIENDOS Y SUBCONTRATOS").font = title_font

        headers4 = ["Categoría", "Código Partida", "Descripción Ítem", "Marca / Modelo", "Cant.", "Precio Unit. CLP", "Subtotal Venta CLP"]
        for c_idx, h in enumerate(headers4, start=1):
            c = ws4.cell(row=3, column=c_idx, value=h)
            c.font = header_font
            c.fill = header_fill

        curr_r = 4
        for line in lines:
            ws4.cell(row=curr_r, column=1, value="HARDWARE/SW").font = bold_font
            ws4.cell(row=curr_r, column=2, value=line.get("item_code", ""))
            ws4.cell(row=curr_r, column=3, value=line.get("name", ""))
            ws4.cell(row=curr_r, column=4, value="Belden/VIZIMAX/NovaTech")
            ws4.cell(row=curr_r, column=5, value=line.get("product_uom_qty", 1)).alignment = Alignment(horizontal="center")
            c_p = ws4.cell(row=curr_r, column=6, value=line.get("price_unit", 0))
            c_p.number_format = "$#,##0"
            c_sub = ws4.cell(row=curr_r, column=7, value=line.get("price_subtotal", 0))
            c_sub.number_format = "$#,##0"
            c_sub.font = bold_font
            curr_r += 1

        # -------------------------------------------------------------
        # SHEET 5: Cash Flow (Flujo de Caja EDPs)
        # -------------------------------------------------------------
        ws5 = wb.create_sheet(title="Cash Flow")
        ws5.views.sheetView[0].showGridLines = True
        ws5.cell(row=1, column=1, value="FLUJO DE CAJA DE PROYECTO Y HITOS DE COBRANZA (EDP)").font = title_font

        headers5 = ["Hito de Cobranza", "Descripción Hito", "Facturación %", "Monto Neto CLP", "Fecha Estimada"]
        for c_idx, h in enumerate(headers5, start=1):
            c = ws5.cell(row=3, column=c_idx, value=h)
            c.font = header_font
            c.fill = header_fill

        cf_data = [
            ("EDP 1", "Pre-kitting y entrega de tableros pre-cableados en taller Conecta", 0.50, round(amount_untaxed * 0.5), "Semana 3"),
            ("EDP 2", "Certificado de Pruebas FAT/SAT HIL firmadas e Registro Informe IPES ante CEN", 0.50, round(amount_untaxed * 0.5), "Semana 6")
        ]
        for r_idx, cf in enumerate(cf_data, start=4):
            ws5.cell(row=r_idx, column=1, value=cf[0]).font = bold_font
            ws5.cell(row=r_idx, column=2, value=cf[1])
            c_pct = ws5.cell(row=r_idx, column=3, value=cf[2])
            c_pct.number_format = "0.0%"
            c_pct.alignment = Alignment(horizontal="center")
            c_m = ws5.cell(row=r_idx, column=4, value=cf[3])
            c_m.number_format = "$#,##0"
            c_m.font = bold_font
            ws5.cell(row=r_idx, column=5, value=cf[4]).alignment = Alignment(horizontal="center")

        # -------------------------------------------------------------
        # SHEET 6: Cliente (Metadata Cliente Coordinado)
        # -------------------------------------------------------------
        ws6 = wb.create_sheet(title="Cliente")
        ws6.views.sheetView[0].showGridLines = True
        ws6.cell(row=1, column=1, value="METADATA DEL CLIENTE COORDINADO").font = title_font

        client_info = [
            ("Razón Social", client_name),
            ("RUT Empresa", "76.543.210-9"),
            ("Giro / Sector", "Generación y Transmisión de Energía Eléctrica"),
            ("Dirección", "Av. Andrés Bello 2711, Las Condes, Santiago"),
            ("Contacto Técnico", "Ing. Administrador de Contratos"),
            ("Email Contacto", f"contacto@{client_name.lower().replace(' ', '')}.cl")
        ]
        for idx, (lbl, val) in enumerate(client_info, start=4):
            c1 = ws6.cell(row=idx, column=1, value=lbl)
            c1.font = bold_font
            c1.fill = accent_fill
            c2 = ws6.cell(row=idx, column=2, value=val)
            c2.font = normal_font

        # -------------------------------------------------------------
        # SHEET 7: Expenses y Logistica
        # -------------------------------------------------------------
        ws7 = wb.create_sheet(title="Expenses y Logistica")
        ws7.views.sheetView[0].showGridLines = True
        ws7.cell(row=1, column=1, value="LOGÍSTICA, VIÁTICOS Y ACREDITACIÓN EN FAENA").font = title_font

        headers7 = ["Concepto Logístico", "Detalle de Gastos", "Días", "Monto CLP"]
        for c_idx, h in enumerate(headers7, start=1):
            c = ws7.cell(row=3, column=c_idx, value=h)
            c.font = header_font
            c.fill = header_fill

        expenses = [
            ("Pre-kitting Tableros Taller", "Ensamblaje y pre-cableado estandarizado (KittingEngine)", 1.5, 1850000),
            ("Acreditación Digital Faena", "Dossier Sicop/Pronexo F30-1, ex. médicos, EPP, ODI/DAS", 0.5, 450000),
            ("Traslado & Camioneta 4x4", "Movilización de tableros y camioneta equipada a subestación", 3.0, 1200000),
            ("Viáticos Especialistas", "Alimentación y hospedaje técnicos en faena", 3.0, 980000)
        ]
        for r_idx, ex in enumerate(expenses, start=4):
            ws7.cell(row=r_idx, column=1, value=ex[0]).font = bold_font
            ws7.cell(row=r_idx, column=2, value=ex[1])
            ws7.cell(row=r_idx, column=3, value=ex[2]).alignment = Alignment(horizontal="center")
            c_m = ws7.cell(row=r_idx, column=4, value=ex[3])
            c_m.number_format = "$#,##0"

        # -------------------------------------------------------------
        # SHEET 8: Terminos de Pago
        # -------------------------------------------------------------
        ws8 = wb.create_sheet(title="Terminos de Pago")
        ws8.views.sheetView[0].showGridLines = True
        ws8.cell(row=1, column=1, value="TÉRMINOS Y CONDICIONES DE PAGO Y GARANTÍA").font = title_font

        terms = [
            ("Condición de Pago", "Facturación 30 días tras aprobación de Estado de Pago (EDP)"),
            ("Validez de la Oferta", "30 días corridos a contar de la fecha de presentación"),
            ("Garantía Técnica", "12 meses contados desde la puesta en servicio comercial"),
            ("Boleta Fiel Cumplimiento", "10% del monto neto total (requerido para licitaciones públicas)"),
            ("Multas / Cap", "Límite máximo acumulado de multas 5% del valor del contrato")
        ]
        for idx, (lbl, val) in enumerate(terms, start=4):
            c1 = ws8.cell(row=idx, column=1, value=lbl)
            c1.font = bold_font
            c1.fill = accent_fill
            c2 = ws8.cell(row=idx, column=2, value=val)
            c2.font = normal_font

        # -------------------------------------------------------------
        # SHEET 9: Check y Sensibilidad
        # -------------------------------------------------------------
        ws9 = wb.create_sheet(title="Check y Sensibilidad")
        ws9.views.sheetView[0].showGridLines = True
        ws9.cell(row=1, column=1, value="ANÁLISIS DE SENSIBILIDAD Y MATRIZ DE RIESGOS DE COSTO").font = title_font

        headers9 = ["Escenario de Margen", "Margen %", "Ventas Neto CLP", "Costo Directo CLP", "Utilidad Bruta CLP", "Evaluación Riesgo"]
        for c_idx, h in enumerate(headers9, start=1):
            c = ws9.cell(row=3, column=c_idx, value=h)
            c.font = header_font
            c.fill = header_fill

        scenarios = [
            ("Agresivo (Licitación)", 0.30, amount_untaxed, round(amount_untaxed*0.70), round(amount_untaxed*0.30), "Riesgo Alto"),
            ("Estándar Conecta S.A.", margin_pct/100.0, amount_untaxed, round(amount_untaxed*(1.0-margin_pct/100.0)), round(amount_untaxed*(margin_pct/100.0)), "Óptimo Conecta"),
            ("SLA / Software Premium", 0.685, amount_untaxed, round(amount_untaxed*0.315), round(amount_untaxed*0.685), "Alta Rentabilidad")
        ]
        for r_idx, sc in enumerate(scenarios, start=4):
            ws9.cell(row=r_idx, column=1, value=sc[0]).font = bold_font
            c_pct = ws9.cell(row=r_idx, column=2, value=sc[1])
            c_pct.number_format = "0.0%"
            c_pct.alignment = Alignment(horizontal="center")
            c_v = ws9.cell(row=r_idx, column=3, value=sc[2])
            c_v.number_format = "$#,##0"
            c_c = ws9.cell(row=r_idx, column=4, value=sc[3])
            c_c.number_format = "$#,##0"
            c_u = ws9.cell(row=r_idx, column=5, value=sc[4])
            c_u.number_format = "$#,##0"
            c_u.font = bold_font
            ws9.cell(row=r_idx, column=6, value=sc[5]).alignment = Alignment(horizontal="center")

        # Auto-fit column widths across all 9 sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or '')
                    if cell.number_format and '$' in cell.number_format:
                        val_str += '      '
                    max_len = max(max_len, len(val_str))
                sheet.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 55)

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream.getvalue()
