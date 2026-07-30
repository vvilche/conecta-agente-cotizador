"""
Multi-tab Excel BOM Builder for Conecta Ingeniería S.A.
Generates comprehensive .xlsx workbooks with all 6 official worksheets fully populated.
"""
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class MultiTabBOMExcelBuilder:
    @staticmethod
    def build_workbook_bytes(payload: dict) -> bytes:
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        client_name = payload.get("partner_id", "Cliente Coordinado Conecta")
        amount_untaxed = payload.get("amount_untaxed", 58628319)
        amount_tax = payload.get("amount_tax", 11139381)
        amount_total = payload.get("amount_total", 69767700)
        lines = payload.get("order_line", [])

        # Color Palette - Conecta Corporate Dark Blue
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        accent_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        bold_font = Font(name="Calibri", size=11, bold=True)
        normal_font = Font(name="Calibri", size=11)
        title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
        subtitle_font = Font(name="Calibri", size=11, italic=True, color="475569")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # -------------------------------------------------------------
        # SHEET 1: Resumen de Oferta
        # -------------------------------------------------------------
        ws1 = wb.create_sheet(title="1. Resumen de Oferta")
        ws1.views.sheetView[0].showGridLines = True

        ws1.cell(row=1, column=1, value="CONECTA INGENIERÍA S.A.").font = title_font
        ws1.cell(row=2, column=1, value="Planilla de Valorización y Resumen Ejecutivo de Oferta Comercial").font = subtitle_font

        info = [
            ("Cliente Coordinado:", client_name),
            ("RUT Cliente:", "76.543.210-9"),
            ("Referencia Cotización:", "OF-2026-CONECTA-REV0"),
            ("Validez de Oferta:", "30 Días Corridos"),
            ("Moneda / Impuesto:", "CLP / IVA 19%"),
            ("Margen Bruto Retenido Target:", "54.80%")
        ]
        for idx, (lbl, val) in enumerate(info, start=4):
            ws1.cell(row=idx, column=1, value=lbl).font = bold_font
            ws1.cell(row=idx, column=2, value=val).font = normal_font

        ws1.cell(row=11, column=1, value="RESUMEN FINANCIERO DE LA OFERTA").font = bold_font
        summary_rows = [
            ("Monto Neto Total (Sin IVA):", amount_untaxed, "$#,##0"),
            ("Impuesto IVA (19%):", amount_tax, "$#,##0"),
            ("Monto Total Bruto (Con IVA):", amount_total, "$#,##0"),
            ("Utilidad Bruta Retenida (54.8%):", round(amount_untaxed * 0.548), "$#,##0")
        ]
        for idx, (lbl, val, fmt) in enumerate(summary_rows, start=12):
            cell_lbl = ws1.cell(row=idx, column=1, value=lbl)
            cell_lbl.font = bold_font
            cell_lbl.fill = accent_fill
            cell_val = ws1.cell(row=idx, column=2, value=val)
            cell_val.font = bold_font
            cell_val.number_format = fmt
            cell_val.fill = accent_fill

        # -------------------------------------------------------------
        # SHEET 2: Planilla de Costos & Precios
        # -------------------------------------------------------------
        ws2 = wb.create_sheet(title="2. Planilla Costos & Precios")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="DESGLOSE DETALLADO DE COSTOS Y PRECIOS VENTA").font = title_font

        headers2 = ["Ítem", "Código Partida", "Descripción de la Partida", "Cant.", "Costo Directo Unit.", "Factor Margen", "Precio Venta Unit.", "Subtotal Venta CLP"]
        for col_num, h in enumerate(headers2, start=1):
            c = ws2.cell(row=3, column=col_num, value=h)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center")

        curr_row = 4
        for idx, line in enumerate(lines, start=1):
            unit_cost = round(line.get("price_unit", 0) / 2.212389)
            ws2.cell(row=curr_row, column=1, value=idx).alignment = Alignment(horizontal="center")
            ws2.cell(row=curr_row, column=2, value=line.get("item_code", "")).font = bold_font
            ws2.cell(row=curr_row, column=3, value=line.get("name", ""))
            ws2.cell(row=curr_row, column=4, value=line.get("product_uom_qty", 1)).alignment = Alignment(horizontal="center")
            c_cost = ws2.cell(row=curr_row, column=5, value=unit_cost)
            c_cost.number_format = "$#,##0"
            ws2.cell(row=curr_row, column=6, value=2.2124).alignment = Alignment(horizontal="center")
            c_pu = ws2.cell(row=curr_row, column=7, value=line.get("price_unit", 0))
            c_pu.number_format = "$#,##0"
            c_sub = ws2.cell(row=curr_row, column=8, value=line.get("price_subtotal", 0))
            c_sub.number_format = "$#,##0"
            c_sub.font = bold_font
            curr_row += 1

        ws2.cell(row=curr_row, column=7, value="TOTAL NETO CLP:").font = bold_font
        c_tot = ws2.cell(row=curr_row, column=8, value=amount_untaxed)
        c_tot.font = bold_font
        c_tot.number_format = "$#,##0"
        c_tot.fill = accent_fill

        # -------------------------------------------------------------
        # SHEET 3: Equipos y Materiales
        # -------------------------------------------------------------
        ws3 = wb.create_sheet(title="3. Equipos y Materiales")
        ws3.views.sheetView[0].showGridLines = True
        ws3.cell(row=1, column=1, value="LISTADO DE HARDWARE Y EQUIPAMIENTO DE SUBESTACIÓN").font = title_font

        headers3 = ["Código Hardware", "Descripción Equipamiento OT", "Marca Estándar", "Modelo / Versión", "Cant.", "Especificación"]
        for col_num, h in enumerate(headers3, start=1):
            c = ws3.cell(row=3, column=col_num, value=h)
            c.font = header_font
            c.fill = header_fill

        hw_items = [
            ("HW-PMU-VIZIMAX", "Medidor Fasorial PMU Clase A IEEE C37.118", "VIZIMAX", "SynchroTeq Plus", 2, "Cumple Norma CEN AT-SITR-1"),
            ("HW-SWITCH-BELDEN", "Switch Ethernet Managed IEC 61850-3", "Belden Hirschmann", "RS20/RS30 Managed", 2, "Redundancia RSTP/MRP"),
            ("HW-RTU-NOVATECH", "Remota RTU Concentradora Subestación", "NovaTech Orion", "Orion LX+ Dual Power", 1, "Protocolos DNP3.0 / IEC 61850"),
            ("HW-GPS-CLOCK", "Sincronizador Satelital IRIG-B / PTP", "Kronos / Arbiter", "Kronos PTP 1588", 1, "Precisión <1us IEEE 1588v2")
        ]
        for r_idx, hw in enumerate(hw_items, start=4):
            ws3.cell(row=r_idx, column=1, value=hw[0]).font = bold_font
            ws3.cell(row=r_idx, column=2, value=hw[1])
            ws3.cell(row=r_idx, column=3, value=hw[2]).font = bold_font
            ws3.cell(row=r_idx, column=4, value=hw[3])
            ws3.cell(row=r_idx, column=5, value=hw[4]).alignment = Alignment(horizontal="center")
            ws3.cell(row=r_idx, column=6, value=hw[5])

        # -------------------------------------------------------------
        # SHEET 4: HH CONECTA & Servicios
        # -------------------------------------------------------------
        ws4 = wb.create_sheet(title="4. HH CONECTA & Servicios")
        ws4.views.sheetView[0].showGridLines = True
        ws4.cell(row=1, column=1, value="HORAS HOMBRE Y SERVICIOS ESPECIALIZADOS DE INGENIERÍA").font = title_font

        headers4 = ["Especialidad / Servicio", "Perfil Profesional", "Horas Hombre (HH)", "Tarifa HH CLP", "Subtotal Servicios CLP"]
        for col_num, h in enumerate(headers4, start=1):
            c = ws4.cell(row=3, column=col_num, value=h)
            c.font = header_font
            c.fill = header_fill

        hh_items = [
            ("Ingeniería de Configuración SCADA/RTU", "Ingeniero Especialista Senior", 60, 110000, 6600000),
            ("Desarrollo HMI & Mapeo DNP3.0", "Ingeniero Control & Automatización", 40, 95000, 3800000),
            ("Pruebas HIL Taller FAT (FatSatSimulator)", "Ingeniero Pruebas Laboratorio", 24, 110000, 2640000),
            ("Comisionamiento SAT & Integración Terreno", "Jefe de Terreno / Especialista", 32, 120000, 3840000),
            ("Tramitación AT-SITR-1 e Informe IPES", "Ingeniero Regulatorio CEN", 20, 110000, 2200000)
        ]
        for r_idx, hh in enumerate(hh_items, start=4):
            ws4.cell(row=r_idx, column=1, value=hh[0]).font = bold_font
            ws4.cell(row=r_idx, column=2, value=hh[1])
            ws4.cell(row=r_idx, column=3, value=hh[2]).alignment = Alignment(horizontal="center")
            c_tarifa = ws4.cell(row=r_idx, column=4, value=hh[3])
            c_tarifa.number_format = "$#,##0"
            c_sub = ws4.cell(row=r_idx, column=5, value=hh[4])
            c_sub.number_format = "$#,##0"
            c_sub.font = bold_font

        # -------------------------------------------------------------
        # SHEET 5: Logística & Gastos Terreno
        # -------------------------------------------------------------
        ws5 = wb.create_sheet(title="5. Logistica & Gastos Terreno")
        ws5.views.sheetView[0].showGridLines = True
        ws5.cell(row=1, column=1, value="LOGÍSTICA, PRE-CABLEADO EN TALLER Y GASTOS DE TERRENO").font = title_font

        headers5 = ["Concepto Logístico", "Detalle de Ejecución", "Días Terreno", "Monto CLP"]
        for col_num, h in enumerate(headers5, start=1):
            c = ws5.cell(row=3, column=col_num, value=h)
            c.font = header_font
            c.fill = header_fill

        log_items = [
            ("Pre-kitting de Tableros Taller (KittingEngine)", "Ensamblaje y pre-cableado estandarizado en taller Conecta", 1.5, 1850000),
            ("Acreditación Digital Faena (AccreditationAutomator)", "Dossiers F30-1, ex. médicos, EPP, ODI/DAS para Sicop/Pronexo", 0.5, 450000),
            ("Traslado & Movilización Terreno", "Flete asegurado de tableros y camioneta 4x4 equipada", 3.0, 1200000),
            ("Viáticos & Allojamiento Especialistas", "Hospedaje y alimentación equipo técnico en faena", 3.0, 980000)
        ]
        for r_idx, lg in enumerate(log_items, start=4):
            ws5.cell(row=r_idx, column=1, value=lg[0]).font = bold_font
            ws5.cell(row=r_idx, column=2, value=lg[1])
            ws5.cell(row=r_idx, column=3, value=lg[2]).alignment = Alignment(horizontal="center")
            c_m = ws5.cell(row=r_idx, column=4, value=lg[3])
            c_m.number_format = "$#,##0"

        # -------------------------------------------------------------
        # SHEET 6: Entregables & Anexos Licitacion
        # -------------------------------------------------------------
        ws6 = wb.create_sheet(title="6. Entregables & Anexos")
        ws6.views.sheetView[0].showGridLines = True
        ws6.cell(row=1, column=1, value="ENTREGABLES TÉCNICOS Y ANEXOS DE LICITACIÓN").font = title_font

        headers6 = ["Anexo / Entregable", "Nombre Documento", "Formato", "Estado / Cumplimiento"]
        for col_num, h in enumerate(headers6, start=1):
            c = ws6.cell(row=3, column=col_num, value=h)
            c.font = header_font
            c.fill = header_fill

        anexos = [
            ("ANEXO A", "Formulario Oferta Económica Neto y Bruto", "PDF / Excel", "Completado al 100%"),
            ("ANEXO B", "Lista de Materiales y Garantía de Hardware (Belden/VIZIMAX)", "Excel Multi-Pestaña", "Completado al 100%"),
            ("ANEXO C", "Certificación de Cumplimiento Normativo CEN/SEC", "PDF Firmado", "Completado al 100%"),
            ("ENTREGABLE 1", "Informe IPES Puesta en Servicio (DocAutomator)", "PDF / DOCX", "Generación 3 segundos"),
            ("ENTREGABLE 2", "Protocolo de Pruebas CEN AT-SITR-1 (FatSatSimulator)", "PDF Firmado", "Certificado HIL Habilitado"),
            ("ENTREGABLE 3", "Estado de Pago EDP & Inserción Odoo ERP", "PDF / Odoo Sync", "Cobranza Acelerada")
        ]
        for r_idx, ax in enumerate(anexos, start=4):
            ws6.cell(row=r_idx, column=1, value=ax[0]).font = bold_font
            ws6.cell(row=r_idx, column=2, value=ax[1])
            ws6.cell(row=r_idx, column=3, value=ax[2]).alignment = Alignment(horizontal="center")
            ws6.cell(row=r_idx, column=4, value=ax[3]).font = bold_font

        # Auto-fit column widths across all sheets
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
