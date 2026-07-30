"""
Official Word (.docx) Commercial Proposal Builder for Conecta Ingeniería S.A.
Generates formatted Microsoft Word proposal documents following exact historical Conecta S.A. sections:
1. DETALLE DE LOS SUMINISTROS Y SERVICIOS
2. DETALLE DE PRECIO OFERTA BASE
3. EXCLUSIONES DE LA OFERTA
4. VALIDEZ DE LA OFERTA
5. CONDICIONES DE PAGO
6. TÉRMINOS Y CONDICIONES (T&C)
"""
import io
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

class OfficialWordQuoteBuilder:
    @staticmethod
    def build_quote_docx_bytes(payload: dict) -> bytes:
        doc = docx.Document()

        # Page setup - Margins 1 inch
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        client_name = payload.get("partner_id", "Cliente Coordinado Conecta")
        amount_untaxed = payload.get("amount_untaxed", 58628319)
        amount_tax = payload.get("amount_tax", 11139381)
        amount_total = payload.get("amount_total", 69767700)
        margin_pct = payload.get("margin_analysis", {}).get("boosted_margin_pct", 54.8)
        lines = payload.get("order_line", [])

        # Corporate Colors
        blue_color = RGBColor(0x1E, 0x3A, 0x8A)
        muted_color = RGBColor(0x47, 0x55, 0x69)

        # Header Title
        p_title = doc.add_paragraph()
        run_title = p_title.add_run("CONECTA INGENIERÍA S.A.")
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(22)
        run_title.font.bold = True
        run_title.font.color.rgb = blue_color

        p_sub = doc.add_paragraph()
        run_sub = p_sub.add_run("OFERTA TÉCNICO-COMERCIAL OFICIAL — SISTEMAS DE SUBESTACIÓN & OT")
        run_sub.font.name = "Calibri"
        run_sub.font.size = Pt(11)
        run_sub.font.bold = True
        run_sub.font.color.rgb = muted_color

        # Info Box Block
        p_meta = doc.add_paragraph()
        p_meta.add_run("Nuestra Ref.: ").bold = True
        p_meta.add_run("OF-2026-CONECTA-REV0\n")
        p_meta.add_run("Fecha: ").bold = True
        p_meta.add_run("Santiago, 30 de Julio de 2026\n")
        p_meta.add_run("Señores: ").bold = True
        p_meta.add_run(f"{client_name}\n")
        p_meta.add_run("Atención: ").bold = True
        p_meta.add_run("Departamento de Ingeniería & Proyectos / Gerencia de Operaciones\n")
        p_meta.add_run("Ref.: ").bold = True
        p_meta.add_run(f"PROPUESTA COMERCIAL INTEGRAL DE AUTOMATIZACIÓN OT — {client_name}")

        # Letter Greeting
        p_body = doc.add_paragraph()
        p_body.paragraph_format.space_before = Pt(12)
        p_body.paragraph_format.space_after = Pt(12)
        p_body.add_run(
            "Estimados Señores:\n\n"
            "Basados en vuestros requerimientos técnicos y normativos del Sistema Eléctrico Nacional (SEN), "
            "tenemos el placer de presentar nuestra oferta para el suministro, pre-kitting en taller, "
            "configuración de comunicaciones e integración de hardware industrial en subestación."
        )

        # 1. DETALLE DE LOS SUMINISTROS Y SERVICIOS
        h1 = doc.add_heading("1. DETALLE DE LOS SUMINISTROS Y SERVICIOS", level=1)
        h1.runs[0].font.color.rgb = blue_color

        bullet_points = [
            ("Equipamiento de Control & Telemetría: ", "Suministro de hardware certificado Belden Hirschmann, VIZIMAX SynchroTeq Plus PMU y NovaTech Orion LX+."),
            ("Pre-kitting Estandarizado en Taller (KittingEngine): ", "Tableros pre-cableados en taller Conecta S.A., reduciendo la estadía en terreno de 5 días a solo 1.5 días."),
            ("Banco de Pruebas HIL FAT/SAT (FatSatSimulator): ", "Simulación HIL de laboratorio para validar tramas DNP3.0 y C37.118 antes del despacho."),
            ("Tramitación Regulatoria CEN / SEC (DocAutomator): ", "Elaboración en 3 segundos de Informe IPES Puesta en Servicio y Protocolo AT-SITR-1."),
            ("Acreditación Express de Personal (AccreditationAutomator): ", "Dossier digital F30-1, ex. médicos y EPP para plataformas Sicop / Pronexo.")
        ]
        for b_title, b_desc in bullet_points:
            bp = doc.add_paragraph(style='List Bullet')
            r_bt = bp.add_run(b_title)
            r_bt.bold = True
            bp.add_run(b_desc)

        # 2. DETALLE DE PRECIO OFERTA BASE
        h2 = doc.add_heading("2. DETALLE DE PRECIO OFERTA BASE", level=1)
        h2.runs[0].font.color.rgb = blue_color

        # Create Styled Table
        table = doc.add_table(rows=1, cols=5)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        hdr_titles = ["Ítem", "Código Partida", "Descripción de la Partida", "Cant.", "Subtotal Venta CLP"]

        for idx, text in enumerate(hdr_titles):
            hdr_cells[idx].text = text
            set_cell_background(hdr_cells[idx], "1E293B")
            hdr_cells[idx].paragraphs[0].runs[0].font.bold = True
            hdr_cells[idx].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            hdr_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        for idx, line in enumerate(lines, start=1):
            row_cells = table.add_row().cells
            row_cells[0].text = str(idx)
            row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            row_cells[1].text = line.get("item_code", "")
            row_cells[2].text = line.get("name", "")
            row_cells[3].text = str(line.get("product_uom_qty", 1))
            row_cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            row_cells[4].text = f"${line.get('price_subtotal', 0):,.0f} CLP"
            row_cells[4].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

            if idx % 2 == 0:
                for cell in row_cells:
                    set_cell_background(cell, "F8FAFC")

        # Summary Financial Paragraph
        p_fin = doc.add_paragraph()
        p_fin.paragraph_format.space_before = Pt(14)
        p_fin.paragraph_format.space_after = Pt(14)
        p_fin.add_run("RESUMEN FINANCIERO DE LA OFERTA:\n").bold = True
        p_fin.add_run(f"• Monto Neto Total (Sin IVA): ${amount_untaxed:,.0f} CLP\n").bold = True
        p_fin.add_run(f"• Impuesto IVA (19%): ${amount_tax:,.0f} CLP\n")
        p_fin.add_run(f"• Monto Total Bruto (Con IVA): ${amount_total:,.0f} CLP\n").bold = True
        p_fin.add_run(f"• Margen Bruto Retenido Target: {margin_pct:.1f}%\n")

        # 3. EXCLUSIONES DE LA OFERTA
        h3 = doc.add_heading("3. EXCLUSIONES DE LA OFERTA", level=1)
        h3.runs[0].font.color.rgb = blue_color
        p_exc = doc.add_paragraph()
        p_exc.add_run(
            "Se excluye expresamente cualquier suministro o actividad distinta a las mencionadas en esta propuesta, en particular:\n"
            "• Obras civiles mayores, canalizaciones subterráneas de fuerza o tendido de cables de AT/MT.\n"
            "• Suministro de relojes satelitales GPS adicionales si el cliente optó por usar infraestructura existente en subestación.\n"
            "• Modificaciones a la lógica de protecciones de marcas no especificadas en la lista de materiales."
        )

        # 4. VALIDEZ DE LA OFERTA
        h4 = doc.add_heading("4. VALIDEZ DE LA OFERTA", level=1)
        h4.runs[0].font.color.rgb = blue_color
        p_val = doc.add_paragraph()
        p_val.add_run("La presente oferta técnico-económica tiene una validez de ").bold = False
        p_val.add_run("30 días corridos").bold = True
        p_val.add_run(" a contar de la fecha de su presentación.")

        # 5. CONDICIONES DE PAGO
        h5 = doc.add_heading("5. CONDICIONES DE PAGO", level=1)
        h5.runs[0].font.color.rgb = blue_color
        p_pago = doc.add_paragraph()
        p_pago.add_run(
            "El pago del precio ofertado se efectuará mediante Estados de Pago (EDP) contra emisión de factura a 30 días:\n"
            "• EDP N° 1 (50% del Total Neto): Al completar el pre-kitting y armado de tableros en taller Conecta S.A.\n"
            "• EDP N° 2 (50% del Total Neto): A la entrega del Certificado FAT/SAT HIL e Informe IPES registrado ante el CEN."
        )

        # 6. TÉRMINOS Y CONDICIONES (T&C)
        h6 = doc.add_heading("6. TÉRMINOS Y CONDICIONES (T&C)", level=1)
        h6.runs[0].font.color.rgb = blue_color
        p_tc = doc.add_paragraph()
        p_tc.add_run(
            "• Garantía Técnica: 12 meses a contar de la recepción conforme de la puesta en servicio comercial.\n"
            "• Multas y Penalizaciones: Limitadas a un techo máximo acumulado del 5% del valor neto del contrato.\n"
            "• Fuerza Mayor: Suspensión de plazos en caso de eventos climáticos desfavorables en faena o indisponibilidad de la red eléctrica."
        )

        # Signature Block
        p_sig = doc.add_paragraph()
        p_sig.paragraph_format.space_before = Pt(30)
        p_sig.add_run(
            "Atentamente,\n\n\n"
            "_________________________________________\n"
            "CONECTA INGENIERÍA S.A.\n"
            "División de Operaciones & Propuestas Comercial OT\n"
            "comercial@conecta-ingenieria.cl | Santiago, Chile"
        ).bold = True

        stream = io.BytesIO()
        doc.save(stream)
        stream.seek(0)
        return stream.getvalue()
