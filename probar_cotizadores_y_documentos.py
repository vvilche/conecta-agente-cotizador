#!/usr/bin/env python3
"""
Script de Prueba Integral en Vivo:
1. Cotizador de Ficha de Traspaso OT - Libro Excel 9 Pestañas (bom_excel_builder.py)
2. Cotizador Comercial Oficial - Word .docx (official_word_quote_builder.py)
3. Generador de Documentos Técnicos y Protocolos CEN - PDF/Markdown (doc_automator.py)
4. Generador de Dossier de Acreditación de Personal - SICOP/Pronexo (accreditation_automator.py)
5. Generador de Estados de Pago - EDP N°1 y N°2 (payment_statement_automator.py)
"""
import os
import sys
import json
from pathlib import Path

# Añadir src al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from operations.bom_excel_builder import MultiTabBOMExcelBuilder
from operations.official_word_quote_builder import OfficialWordQuoteBuilder
from operations.doc_automator import DocAutomator
from operations.accreditation_automator import AccreditationAutomator
from operations.payment_statement_automator import PaymentStatementAutomator

def ejecutar_prueba_integral():
    output_dir = Path("salida_pruebas_cotizador_y_doc")
    output_dir.mkdir(exist_ok=True)
    
    print("=========================================================================")
    print(" INICIANDO PRUEBA INTEGRAL DE COTIZADORES Y GENERADORES DE DOCUMENTOS ")
    print("=========================================================================\n")
    
    # --- 1. PRUEBA DE COTIZADOR EXCEL (9 PESTAÑAS - FICHA DE TRASPASO OT) ---
    print("1) Probando Cotizador Excel de 9 Pestañas (Ficha de Traspaso OT)...")
    payload_excel = {
        "client_name": "COLBÚN S.A. - CENTRAL RUCATAYO",
        "project_name": "OT 8208 - Integración PMU Vizimax & PDC Corporativo",
        "date": "2026-08-01",
        "seller": "Víctor Vilche",
        "margin_target_pct": 54.8,
        "hh_rate_clp": 35000,
        "items": [
            {"code": "EQ-VIZ-001", "description": "PMU Vizimax SynchroTeq Plus en Celda", "qty": 2, "unit_cost": 4500000, "category": "Hardware"},
            {"code": "EQ-KRO-002", "description": "Reloj Satelital GPS Kronos con Antena", "qty": 1, "unit_cost": 2800000, "category": "Hardware"},
            {"code": "LIC-PDC-003", "description": "Licencia PDC Corporativo 500 Stream", "qty": 1, "unit_cost": 8500000, "category": "Software"},
            {"code": "SRV-FAT-004", "description": "Servicios de Ingeniería de Detalle y Pruebas FAT en Taller", "qty": 1, "unit_cost": 3200000, "category": "Servicios"},
            {"code": "SRV-SAT-005", "description": "Puesta en Servicio SAT Remoto y Conexión CEN", "qty": 1, "unit_cost": 2500000, "category": "Servicios"}
        ]
    }
    builder_excel = MultiTabBOMExcelBuilder()
    excel_bytes = builder_excel.build_workbook_bytes(payload_excel)
    excel_path = output_dir / "COTIZACION_OT8208_COLBUN_9_PESTANAS.xlsx"
    with open(excel_path, "wb") as f:
        f.write(excel_bytes)
    print(f"   [OK] Libro Excel de 9 Pestañas generado exitosamente: {excel_path} ({len(excel_bytes)} bytes)")

    # --- 2. PRUEBA DE COTIZADOR COMERCIAL WORD (.DOCX) ---
    print("\n2) Probando Cotizador Comercial Oficial en Word (.docx)...")
    payload_word = {
        "partner_id": "COLBÚN S.A.",
        "client_name": "COLBÚN S.A.",
        "attention": "Gerencia de Proyectos y Transmisión",
        "reference_number": "260801 Rev 0",
        "subject_ref": "OFERTA TÉCNICO-COMERCIAL: SISTEMA PMU & PDC RUCATAYO",
        "amount_untaxed": 58628319,
        "amount_tax": 11139381,
        "amount_total": 69767700,
        "currency": "CLP",
        "margin_analysis": {"boosted_margin_pct": 54.8},
        "order_line": [
            {"item_code": "EQ-001", "name": "PMU Vizimax SynchroTeq Plus - Unidad Celda", "product_uom_qty": 2, "price_unit": 10500000, "price_subtotal": 21000000},
            {"item_code": "EQ-002", "name": "Reloj Satelital GPS Kronos (Sincronización PTP/IRIG-B)", "product_uom_qty": 1, "price_unit": 6800000, "price_subtotal": 6800000},
            {"item_code": "LIC-003", "name": "Licencia Servidor PDC Corporativo Redundante", "product_uom_qty": 1, "price_unit": 18500000, "price_subtotal": 18500000},
            {"item_code": "SRV-004", "name": "Ingeniería, Armado de Tablero (Cosido) y Pruebas FAT en Taller", "product_uom_qty": 1, "price_unit": 7500000, "price_subtotal": 7500000},
            {"item_code": "SRV-005", "name": "Puesta en Servicio SAT en Faena e Informe IPES CEN", "product_uom_qty": 1, "price_unit": 4828319, "price_subtotal": 4828319}
        ]
    }
    word_builder = OfficialWordQuoteBuilder()
    docx_bytes = word_builder.build_quote_docx_bytes(payload_word)
    docx_path = output_dir / "OFERTA_COMERCIAL_OFICIAL_OT8208_COLBUN.docx"
    with open(docx_path, "wb") as f:
        f.write(docx_bytes)
    print(f"   [OK] Propuesta Comercial Oficial en Word (.docx) generada: {docx_path} ({len(docx_bytes)} bytes)")

    # --- 3. PRUEBA DE GENERADOR DE DOCUMENTOS TÉCNICOS Y PROTOCOLOS CEN ---
    print("\n3) Probando Generador de Documentos Técnicos y Protocolos CEN (doc_automator.py)...")
    doc_auto = DocAutomator()
    protocol_res = doc_auto.generate_cen_fat_protocol(
        ot_code="OT-8208",
        substation_name="S/E Rucatayo 220 kV",
        device_model="Vizimax SynchroTeq Plus PMU / Orion MX"
    )
    protocol_path = output_dir / "PROTOCOLO_FAT_SAT_CEN_OT8208.json"
    with open(protocol_path, "w", encoding="utf-8") as f:
        json.dump(protocol_res, f, indent=2, ensure_ascii=False)
    print(f"   [OK] Protocolo Técnico FAT/SAT CEN generado: {protocol_path}")

    ipes_res = doc_auto.generate_ipes_report(
        ot_code="OT-8208",
        client_name="COLBÚN S.A.",
        substation_name="S/E Rucatayo 220 kV",
        equipment_summary="Gabinete Vizimax SynchroTeq Plus PMU + Gateway Orion MX"
    )
    ipes_path = output_dir / "INFORME_IPES_PUESTA_EN_SERVICIO_OT8208.json"
    with open(ipes_path, "w", encoding="utf-8") as f:
        json.dump(ipes_res, f, indent=2, ensure_ascii=False)
    print(f"   [OK] Informe IPES de Puesta en Servicio CEN generado: {ipes_path}")

    # --- 4. PRUEBA DE GENERADOR DE DOSSIER DE ACREDITACIÓN (SICOP / PRONEXO) ---
    print("\n4) Probando Generador de Dossier de Acreditación de Personal (accreditation_automator.py)...")
    accred_auto = AccreditationAutomator()
    accred_res = accred_auto.generate_substation_access_package(
        ot_code="OT-8208",
        client="COLBÚN S.A.",
        workers=[
            {"name": "Víctor Vilche", "rut": "15.823.411-9"},
            {"name": "Ingeniero Especialista SAT", "rut": "18.455.122-K"}
        ]
    )
    accred_path = output_dir / "DOSSIER_ACREDITACION_SICOP_OT8208.json"
    with open(accred_path, "w", encoding="utf-8") as f:
        json.dump(accred_res, f, indent=2, ensure_ascii=False)
    print(f"   [OK] Dossier de Acreditación de Personal (SICOP/Pronexo) generado: {accred_path}")

    # --- 5. PRUEBA DE GENERADOR DE ESTADOS DE PAGO (EDP N°1 y N°2) ---
    print("\n5) Probando Generador de Estados de Pago Automatizados (payment_statement_automator.py)...")
    pay_auto = PaymentStatementAutomator()
    pay_res = pay_auto.generate_payment_statement(
        ot_code="OT-8208",
        client_name="COLBÚN S.A.",
        milestone_name="Hito 2: 40% - Ingeniería de Detalle y Pruebas FAT en Taller",
        milestone_pct=40.0,
        total_contract_uf=1527.7
    )
    pay_path = output_dir / "ESTADO_DE_PAGO_N2_OT8208_40_PORCIENTO.json"
    with open(pay_path, "w", encoding="utf-8") as f:
        json.dump(pay_res, f, indent=2, ensure_ascii=False)
    print(f"   [OK] Estado de Pago EDP N°2 generado: {pay_path}")

    print("\n=========================================================================")
    print(" RESUMEN: PRUEBA INTEGRAL DE COTIZADORES Y DOCUMENTOS 100% EXITOSA ")
    print(f" Archivos generados disponibles en la carpeta: {output_dir.resolve()}")
    print("=========================================================================")

if __name__ == "__main__":
    ejecutar_prueba_integral()
