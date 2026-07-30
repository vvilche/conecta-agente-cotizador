"""
Official Word (.docx) Commercial Proposal Builder for Conecta Ingeniería S.A.
Generates formatted Microsoft Word proposal documents.
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
        lines = payload.get("order_line", [])

        # Color Palette
        navy_color = RGBColor(0x1E, 0x29, 0x3B)
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
        p_meta.add_run("Nuestra Ref: ").bold = True
        p_meta.add_run("OF-2026-CONECTA-REV0\n")
        p_meta.add_run("Fecha: ").bold = True
        p_meta.add_run("30 de Julio de 2026 (Santiago, Chile)\n")
        p_meta.add_run("Señores: ").bold = True
        p_meta.add_run(f"{client_name}\n")
        p_meta.add_run("Atención: ").bold = True
        p_meta.add_run("Departamento de Ingeniería & Proyectos / Gerencia de Operaciones\n")
        p_meta.add_run("Ref.: ").bold = True
        p_meta.add_run("Suministro, Ingeniería, Pruebas HIL y Puesta en Servicio de Equipamiento OT")

        # Letter Greeting
        p_body = doc.add_paragraph()
        p_body.paragraph_format.space_before = Pt(12)
        p_body.paragraph_format.space_after = Pt(12)
        p_body.add_run(
            "Estimados Señores:\n\n"
            "Basados en vuestros requerimientos técnicos y normativos del Sistema Eléctrico Nacional (SEN), "
            "tenemos el agrado de presentar nuestra propuesta técnico-económica para el suministro, pre-kitting en taller, "
            "configuración de comunicaciones e integración de hardware industrial en subestación."
        )

        # Section 1: Scope
        h1 = doc.add_heading("1. ALCANCE TÉCNICO DE LA OFERTA Y ARQUITECTURA", level=1)
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

        # Section 2: Economics Table
        h2 = doc.add_heading("2. OFERTA ECONÓMICA Y DESGLOSE DE PARTIDAS", level=1)
        h2.runs[0].font.color.rgb = blue_color

        # Create Styled Table
        table = doc.add_table(rows=1, cols=5)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        hdr_titles = ["Item", "Código Partida", "Descripción de la Partida", "Cant.", "Subtotal Venta CLP"]

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

            # Alternate row background
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
        p_fin.add_run("• Margen Bruto Retenido Target: 54.80%\n")

        # Section 3: Schedule & Terms
        h3 = doc.add_heading("3. CRONOGRAMA Y CONDICIONES COMERCIALES (T&C)", level=1)
        h3.runs[0].font.color.rgb = blue_color

        p_terms = doc.add_paragraph()
        p_terms.add_run("• Plazo de Entrega: ").bold = True
        p_terms.add_run("4 a 6 semanas tras recepción de la Orden de Compra.\n")
        p_terms.add_run("• Estructura de Hitos EDP: ").bold = True
        p_terms.add_run("EDP 1 (50%) al kitting de tableros en taller; EDP 2 (50%) a la entrega del Certificado FAT/SAT HIL e Informe IPES.\n")
        p_terms.add_run("• Validez de la Oferta: ").bold = True
        p_terms.add_run("30 días corridos.\n")
        p_terms.add_run("• Garantía Técnica: ").bold = True
        p_terms.add_run("12 meses contados desde la puesta en servicio comercial.")

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
