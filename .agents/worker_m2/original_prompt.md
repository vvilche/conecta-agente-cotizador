## 2026-07-30T17:03:16Z
Role: teamwork_preview_worker
Working directory: .agents/worker_m2
Task: Standardize Word Quote Builder & Implement Quantity Parser (Requirement R1 & Quantity Parsing).

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Detailed Instructions:
1. Create `src/operations/quantity_parser.py`:
   - Implement `QuantityParser` class.
   - Implement regex pattern `VOLTAGE_POWER_PATTERN` to mask/strip voltage and power ratings before quantity extraction:
     `r'\b\d+(?:\.\d+)?\s*(?:kV|kVAC|kVDC|V|VAC|VDC|MW|kW|MVA|kVA|Hz)\b'` (e.g. `220kV`, `110kV`, `500kV`, `13.8kV`, `9MW`).
   - Implement `SPANISH_NUMBER_WORDS` dict mapping Spanish number words to integers:
     `{"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10}`.
   - Implement methods:
     - `parse_quantities(text: str) -> dict[str, float]`
     - `extract_device_quantity(text: str, default: float = 1.0) -> float`
   - Ensure text like `"Cotizar dos RTUs Novatech Orion LX+ y tres switches Belden en SE Ancud 220kV"` extracts `num_rtus=2.0`, `num_switches=3.0` without misinterpreting `220kV` as quantity 220!
   - Export `QuantityParser`, `parse_quantities`, and `extract_device_quantity` in `src/operations/__init__.py`.

2. Integrate `QuantityParser` in `src/swarm_engine/agents/cotizacion_inventario.py`:
   - Use `QuantityParser.extract_device_quantity` in `guide_quotation` / `process_event` so prompt text with voltage levels (`220kV`, `110kV`) doesn't pollute device counts.

3. Standardize `src/operations/official_word_quote_builder.py`:
   - Dynamic Reference Code: If `reference_number` is not provided in payload, default to corporate standard `YYMMDD Rev X` (e.g., `260730 Rev 0` for date `2026-07-30`).
   - Dynamic Date: Format as `Santiago, 30 de Julio de 2026` or use custom date string from payload.
   - Headings: Maintain all 6 official headings:
     1. `DETALLE DE LOS SUMINISTROS Y SERVICIOS`
     2. `DETALLE DE PRECIO OFERTA BASE`
     3. `EXCLUSIONES DE LA OFERTA`
     4. `VALIDEZ DE LA OFERTA`
     5. `CONDICIONES DE PAGO`
     6. `TÉRMINOS Y CONDICIONES (T&C)`
     Allow payload customization of bullet points / text for sections 3-6.
   - Summary Table: Header must contain 6 columns:
     `["Ítem", "Código Partida", "Descripción de la Partida", "Cant.", f"Precio Unit. Neto {currency}", f"Subtotal Venta {currency}"]`.
     Explicitly populate `Precio Unit. Neto` and `Subtotal Venta` formatted per currency. Explicitly set column cell widths (`cell.width`).
   - Currency: Support `currency` attribute (`CLP`, `USD`, `UF`). Format totals and unit prices accordingly.

4. Add Unit Tests:
   - Create `tests/test_quantity_voltage_parser.py` testing voltage stripping and Spanish word parsing.
   - Create `tests/test_official_word_quote_builder.py` testing docx generation, 6 headings, metadata block, 6-column table, and currency formatting.

5. Verification:
   - Run `pytest tests/test_quantity_voltage_parser.py tests/test_official_word_quote_builder.py tests/test_operations_engine.py` using pytest command.
   - Ensure all tests pass cleanly.

Write handoff report to `.agents/worker_m2/handoff.md` and send completion message to parent.
