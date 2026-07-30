# HANDOFF REPORT — Explorer M1_1: Audit of Word Quote Builder & Quantity Parser

## 1. Observation

### 1.1 Word Proposal Builder Audit (`src/operations/official_word_quote_builder.py` & `src/operations/official_quote_builder.py`)

Direct inspection of `src/operations/official_word_quote_builder.py` (lines 1 to 202) reveals the following direct observations:

1. **Cover & Metadata Block**:
   - **Line 68**: `p_meta.add_run("OF-2026-CONECTA-REV0\n")` is hardcoded as a static string. It does not follow Conecta's corporate reference convention `YYMMDD Rev X` (e.g. `260730 Rev 0`).
   - **Line 70**: `p_meta.add_run("Santiago, 30 de Julio de 2026\n")` is static text.
   - **Line 76**: `p_meta.add_run(f"PROPUESTA COMERCIAL INTEGRAL DE AUTOMATIZACIÓN OT — {client_name}")` uses a static subject template and does not extract custom titles or subjects from `payload.get("subject")` or `payload.get("title")`.

2. **Official Headings**:
   - **Heading 1**: `1. DETALLE DE LOS SUMINISTROS Y SERVICIOS` (line 90)
   - **Heading 2**: `2. DETALLE DE PRECIO OFERTA BASE` (line 107)
   - **Heading 3**: `3. EXCLUSIONES DE LA OFERTA` (line 149)
   - **Heading 4**: `4. VALIDEZ DE LA OFERTA` (line 160)
   - **Heading 5**: `5. CONDICIONES DE PAGO` (line 168)
   - **Heading 6**: `6. TÉRMINOS Y CONDICIONES (T&C)` (line 178)
   *Observation*: All 6 required section heading names are present, but sections 3-6 lack dynamic payload customization (e.g., customizable payment milestones or custom exclusion bullet points).

3. **Summary Table & Financial Formatting**:
   - **Line 114**: `hdr_titles = ["Ítem", "Código Partida", "Descripción de la Partida", "Cant.", "Subtotal Venta CLP"]`
   - *Defect*: The table is **missing** the `Precio Unit. Neto` (Unit Price) column. It only has 5 columns (Ítem, Código, Descripción, Cant., Subtotal). Contrast with `src/operations/official_quote_builder.py` (Markdown builder) line 51 which includes `Precio Unit. Neto CLP`.
   - **Line 131**: `row_cells[4].text = f"${line.get('price_subtotal', 0):,.0f} CLP"` — Currency is hardcoded as `CLP`. There is no currency attribute checking (`USD`, `UF`, `CLP`).
   - **Line 143-146**: Financial summary lines hardcode `${amount_untaxed:,.0f} CLP`, `${amount_tax:,.0f} CLP`, `${amount_total:,.0f} CLP`.
   - **Table formatting**: Cell widths (`cell.width`) are not explicitly set on docx table cells, causing Word autowrap columns unevenly.

### 1.2 Quantity Parser Audit (`src/swarm_engine/agents/cotizacion_inventario.py` & `src/supervisor_ui/app.py`)

Inspection of `src/swarm_engine/agents/cotizacion_inventario.py` (line 75) and all `src/` files shows:

1. **Absence of Text Quantity Parser**:
   - `CotizacionInventarioAgent.guide_quotation` (line 75) extracts quantities solely from explicit dictionary keys:
     ```python
     num_devices = float(user_params.get("num_rtus") or user_params.get("num_remotas") or user_params.get("num_pmus") or user_params.get("qty") or 1.0)
     ```
   - No regular expression or natural language parser exists in Python to extract item quantities from user prompt strings like `"Cotizar dos RTUs Novatech Orion LX+ y tres switches Belden en SE Ancud 220kV"`.

2. **Voltage & Power Rating False Positives**:
   - Without filtering, any standard regex searching for integers (`\d+`) in prompts containing `"SE Ancud 220kV"`, `"Subestación Quillota 110kV"`, `"Línea 500kV"`, `"Media Tensión 13.8kV"`, `"Transformador 66kV"`, or `"Planta Solar 9MW"` extracts `220`, `110`, `500`, `66`, `13.8`, or `9` as the item quantity count (over-quoting by 100x-200x).

3. **Spanish Number Word Parsing**:
   - User prompts in Spanish frequently specify counts using word forms (`"una PMU"`, `"dos RTUs"`, `"tres tableros"`, `"cuatro switches"`, `"cinco medidores"`).
   - Python string conversion `float()` or `int()` fails on non-numeric strings, falling back to default `1.0`.

---

## 2. Logic Chain

1. **Word Proposal Builder Logic**:
   - Conecta S.A. proposal documents require corporate reference codes formatted as `YYMMDD Rev X` (e.g. `260730 Rev 0` generated on 2026-07-30). Hardcoding `"OF-2026-CONECTA-REV0"` violates corporate branding and historical reference standards observed across `2025/` proposals.
   - Commercial proposals must state both Unit Prices and Subtotals in tables so clients can audit single-unit vs bulk costs. The Word builder currently omits the `Precio Unit. Neto` column.
   - Conecta S.A. quotes international hardware (e.g., Belden, Vizimax, NovaTech) in USD or CLP. Hardcoding `CLP` on all line subtotals breaks multi-currency proposals.

2. **Quantity Parser Logic**:
   - When a user inputs natural language prompts into the Commercial Portal (`comercial.html`), the system must infer the required device quantities.
   - Text inputs in power systems engineering inevitably include system voltage levels (`220kV`, `110kV`, `500kV`, `13.8kV`) and capacities (`9MW`, `15MW`).
   - If voltage/capacity tokens are not stripped or masked prior to quantity extraction, integer matchers incorrectly bind voltage numbers to device quantities.
   - Similarly, Spanish prompt text uses number words ("dos RTUs", "una PMU"). Mapping `{"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10}` ensures natural language requests translate into accurate BOM line quantities.

---

## 3. Caveats

- **Existing Tests**: Current unit tests (`test_operations_engine.py`, `test_supervisor_ui.py`) check basic PDF/Word generation and EDP endpoints, but do NOT assert the presence of `Precio Unit.` column in docx tables, nor do they test quantity parsing from text prompts containing voltage ratings (`220kV`/`110kV`).
- **No Production Code Written**: As a read-only explorer, no modifications to `src/` have been made. Worker M2 will perform the implementation.

---

## 4. Conclusion & Implementation Recommendations for Worker M2

### 4.1 Recommended Changes for Word Quote Builder (`src/operations/official_word_quote_builder.py`)

1. **Dynamic Reference & Date Formatting**:
   - Compute default reference code as `YYMMDD Rev X` (e.g. `260730 Rev 0`) if not supplied in payload.
   - Accept optional `reference_number` and `date_str` in payload.
2. **Table Header & Column Addition**:
   - Update table headers to 6 columns: `["Ítem", "Código Partida", "Descripción de la Partida", "Cant.", f"Precio Unit. Neto {currency}", f"Subtotal Venta {currency}"]`.
   - Explicitly set column widths: Ítem (0.6 in), Código (1.2 in), Descripción (2.5 in), Cant (0.6 in), Precio Unit (1.1 in), Subtotal (1.2 in).
3. **Currency Flexibility**:
   - Support `currency = payload.get("currency", "CLP")`. Format numbers accordingly (`$X,XXX CLP`, `$X,XXX USD`, or `X.XX UF`).
4. **Section Customization**:
   - Allow optional payload overrides for `exclusions`, `payment_conditions`, `terms_and_conditions`, and `validez_dias`.

### 4.2 Recommended New Quantity Parser Module (`src/operations/quantity_parser.py`)

1. **Implement `QuantityParser` class**:
   - **Voltage/Rating Masking**: Replace/strip patterns using regex:
     ```python
     VOLTAGE_POWER_PATTERN = r'\b\d+(?:\.\d+)?\s*(?:kV|kVAC|kVDC|V|VAC|VDC|MW|kW|MVA|kVA|Hz)\b'
     ```
   - **Spanish Number Word Map**:
     ```python
     SPANISH_NUMBER_WORDS = {
         "un": 1, "una": 1, "uno": 1,
         "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
         "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10
     }
     ```
   - **Quantity Extraction Engine**:
     - Parse strings for phrases like `"dos RTUs"`, `"3 switches"`, `"una PMU"`, `"4 medidores"`.
     - Return a structured dictionary, e.g.:
       ```python
       {
           "num_pmus": 1.0,
           "num_rtus": 2.0,
           "num_switches": 3.0,
           "raw_extracted": [...]
       }
       ```
2. **Integrate into `cotizacion_inventario.py`**:
   - Use `QuantityParser` inside `CotizacionInventarioAgent.process_event` / `guide_quotation` so natural language prompts populate `num_devices` correctly without voltage false-positives.

---

## 5. Verification Method

To verify implementation, Worker M2 should execute:

1. **Unit & Integration Tests**:
   ```bash
   pytest tests/test_operations_engine.py tests/test_supervisor_ui.py -v
   ```
2. **New Test Suite (`tests/test_quantity_parser_and_word_builder.py`)**:
   - Test voltage filtering: `"Cotizar RTU para Subestación Ancud 220kV y 110kV con dos remotas"` -> quantity = 2 (NOT 220 or 110).
   - Test Spanish word parsing: `"Necesito una PMU VIZIMAX y tres switches Belden"` -> PMU qty = 1, Switches qty = 3.
   - Test docx generation: Inspect table column headers to ensure `Precio Unit. Neto` is present and reference number matches `260730 Rev 0`.
