## 2026-07-30T03:06:47Z

Diseñar y construir un paquete integral y accionable de automatizaciones de software para el Área de Operaciones de Conecta Ingeniería S.A., maximizando la retención interna de margen bruto (54.8%), acelerando la cobranza de cuentas por cobrar y reduciendo la carga administrativa burocrática del equipo técnico.

Working directory: /Users/victorvilche/VictorEstrategia/CampañasCumplimientoNormativo/ENEL PMUS/Digitalizacion Transelec/COMASA/Inteligencia Comercial
Integrity mode: development

## Requirements

### R1. Paquete de Automatizaciones Operacionales Punta a Punta
El sistema debe estructurar 5 módulos de automatización de software listos para integración operativa:
1. DocAutomator: Generador automático en 3 segundos de Fichas de Traspaso, Protocolos de Pruebas CEN AT-SITR-1 e Informes IPES en formato PDF/DOCX.
2. FatSatSimulator: Banco de pruebas de laboratorio con simulación HIL para validar telemetrías DNP3/C37.118 antes del despacho a terreno.
3. KittingEngine: Motor de armado estandarizado de tableros (Kit PMU y Kit RTU SCADA) pre-cableados en taller.
4. AccreditationAutomator: Auto-compilador de dossiers digitales de acreditación (F30-1, contratos, ex. médicos, EPP, ODI/DAS) para ingreso express a faenas (Sicop/Pronexo/RyS).
5. PaymentStatementAutomator: Emisor instantáneo de Estados de Pago con certificado FAT/SAT firmado adjunto para disparo de facturación en Odoo.

### R2. Matriz de Rentabilidad e Impacto Financiero
El sistema debe calcular el impacto financiero de cada automatización en términos de horas hombre liberadas, días de terreno reducidos y margen bruto retenido internamente.

### R3. Panel Integrado de Supervisión
El paquete debe estar integrado en la interfaz de supervisión de operaciones (src/supervisor_ui/app.py) con capacidad de auditoría y ejecución de pruebas.

## Acceptance Criteria

### Cobertura y Funcionalidad Operativa
- [ ] Los 5 módulos de automatización operan integradamente en el repositorio src/operations/.
- [ ] La batería de pruebas automatizadas en tests/ cubre el 100% de las funciones operacionales con 0 errores.
- [ ] La interfaz de usuario en src/supervisor_ui/app.py permite activar y auditar la ejecución de cada automatización.

### Verificación Objetiva
- [ ] Ejecución limpia de pytest con 200+ pruebas pasando al 100%.
- [ ] Generación exitosa de informes ejecutivos en formato Markdown para el equipo de operaciones.

## 2026-07-30T16:34:00Z

# Teamwork Project Prompt — Audit & Document Format Standardization

> Goal: Audit and standardize file structures, Word/Excel document generators, and folder mappings across Commercial & Operations modules.

Audit and standardize all generated project documents (Word .docx proposals, Excel .xlsx 9-sheet workbooks, PDF technical reports) to ensure 100% fidelity to historical Conecta S.A. project standards (`ot_7000` / `ot_8000_smart_extracted`).

Working directory: /Users/victorvilche/VictorEstrategia/CampañasCumplimientoNormativo/ENEL PMUS/Digitalizacion Transelec/COMASA/Inteligencia Comercial
Integrity mode: development

## Requirements

### R1. Word Quote Builder Standardization (`official_word_quote_builder.py`)
Ensure Word documents generated for quotations follow the exact corporate template of Conecta S.A.:
- Professional cover & metadata block: Reference number (`260730 Rev 0`), Date (`Santiago, 30 de Julio de 2026`), Client name, Subject.
- Official Headings:
  1. `DETALLE DE LOS SUMINISTROS Y SERVICIOS`
  2. `DETALLE DE PRECIO OFERTA BASE`
  3. `EXCLUSIONES DE LA OFERTA`
  4. `VALIDEZ DE LA OFERTA`
  5. `CONDICIONES DE PAGO`
  6. `TÉRMINOS Y CONDICIONES (T&C)`
- Properly formatted summary table with item codes, descriptions, quantities, unit prices in CLP/USD, and net totals.

### R2. Excel 9-Sheet BOM Builder Standardization (`bom_excel_builder.py`)
Ensure Excel workbooks generated for projects populate all 9 official Conecta worksheets:
1. `Ficha`: Transpaso OT Metadata.
2. `Resumen`: Net sales, 19% IVA, Total gross, Target Gross Margin %.
3. `Control HH y Costos`: Man-hours matrix by activity (Planificación, Ingeniería, Pruebas HIL FAT, SAT Terreno).
4. `Equi. Mat. Arr. Sub.`: Hardware, Materials, Equipment Rentals, Subcontracts.
5. `Cash Flow`: Milestone billing (EDP 1 Pre-kitting 50%, EDP 2 SAT HIL 50%).
6. `Cliente`: Client corporate metadata.
7. `Expenses y Logistica`: Travel, 4x4 trucks, Sicop/Pronexo accreditation.
8. `Terminos de Pago`: Payment terms, performance bonds, warranty.
9. `Check y Sensibilidad`: Financial margin sensitivity (30% - 68.5%) and risk matrix.

### R3. Automated Test Suite & Audit Integrity
Verify that all 302+ automated unit & integration tests in `pytest` pass with 100% coverage and zero broken contracts.

## Acceptance Criteria

### Verification & Quality Guardrails
- [ ] Word quotation builder generates valid `.docx` files conforming to Conecta's 6 official sections.
- [ ] Multi-tab Excel builder generates valid `.xlsx` files with all 9 sheets populated and non-zero formulas.
- [ ] Quantity parser correctly filters voltage ratings (`220kV`, `110kV`) and parses Spanish number words (`una PMU` -> 1).
- [ ] Target Gross Margin % is dynamically configurable from UI (10.0% to 85.0%).
- [ ] Pytest suite executes cleanly with 300+ passing tests and 0 failures.
