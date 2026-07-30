# Handoff Report — Audit Excel 9-Sheet BOM Builder & Dynamic Margin UI Configuration

**Agent Role**: teamwork_preview_explorer  
**Working Directory**: `.agents/explorer_m1_2`  
**Target Module / Task**: Audit Excel 9-Sheet BOM Builder & Dynamic Margin UI Configuration (Requirement R2 & UI Margin Config)  
**Date**: 2026-07-30  

---

## 1. Observation

Direct code examination of the codebase (`src/operations/bom_excel_builder.py`, `src/operations/financial_engine.py`, `src/supervisor_ui/app.py`, `src/swarm_engine/agents/cotizacion_inventario.py`, and `src/supervisor_ui/templates/comercial.html`) yielded the following exact findings:

1. **`src/operations/bom_excel_builder.py` Worksheet Count & Names**:
   - Line 5-7 & 59-312: `MultiTabBOMExcelBuilder` generates **14 sheets**: `Currency`, `Ficha`, `Control HH y Costos`, `Cash Flow`, `Cliente`, `Resumen`, `Costos HH`, `Equi. Mat. Arr. Sub.`, `Calculo HH`, `Expenses`, `Check`, `Sensibilidad`, `Terminos de Pago`, `Base de Datos`.
   - Conecta's official Requirement R2 mandates **9 worksheets**: `Ficha`, `Resumen`, `Control HH y Costos`, `Equi. Mat. Arr. Sub.`, `Cash Flow`, `Cliente`, `Expenses y Logistica`, `Terminos de Pago`, `Check y Sensibilidad`.
   - Key structural mismatches:
     - `Check` and `Sensibilidad` are split into 2 separate sheets instead of being unified as `Check y Sensibilidad`.
     - `Control HH y Costos`, `Costos HH`, and `Calculo HH` are split into 3 separate sheets instead of being integrated into 1 sheet.
     - `Expenses` is missing `y Logistica` in its sheet name.

2. **`src/operations/bom_excel_builder.py` Excel Formula Audit**:
   - **0 Excel formulas are populated across all 319 lines of `bom_excel_builder.py`**.
   - Line 119: `total_hh = sum(h[5] for h in hh_items); ws.cell(r + 1, 6, total_hh)` -> Python static int written as cell value instead of `=SUM(F5:F11)`.
   - Line 128: `("EDP 1", "...", 0.50, round(amount_untaxed * 0.5), ...)` -> Python static int instead of `=Ficha!B11*0.5` or `=Resumen!B4*C4`.
   - Lines 158-163 (`Resumen` sheet):
     - `amount_tax` -> Static value instead of `=B4*0.19`.
     - `amount_total` -> Static value instead of `=B4+B5`.
     - `Costo Directo Estimado` -> Static value `round(amount_untaxed * (1 - margin_pct / 100))` instead of `=B4*(1-B9)`.
     - `Utilidad Bruta Retenida` -> Static value `round(amount_untaxed * (margin_pct / 100))` instead of `=B4-B7` or `=B4*B9`.
   - Lines 199 (`Equi. Mat. Arr. Sub.` sheet): `price_subtotal` is written as static value instead of `=E4*F4`.
   - If a user modifies quantities or prices in Excel, no formulas recalculate.

3. **`src/operations/financial_engine.py` Margin Flexibility**:
   - Line 12: `RETAINED_GROSS_MARGIN_PCT: float = 54.8` (hardcoded class attribute constant).
   - Line 14-16: `def retained_gross_margin_pct(self) -> float: return self.RETAINED_GROSS_MARGIN_PCT` takes no parameter.
   - Line 69-95: `calculate_financial_summary()` has no `target_margin_pct` argument and calls `retained_margin_pct = self.retained_gross_margin_pct()`.
   - Result: `financial_engine.py` ALWAYS evaluates financial ROI at 54.8% and ignores any dynamic margin configured from 10.0% to 85.0%.

4. **`src/supervisor_ui/templates/comercial.html` Frontend JS Bug**:
   - Lines 362-366 in `generateQuote()` function:
     `num_pmus: numUnits, num_rtus: numUnits, include_gps: hasGps, include_gps_clock: hasGps, has_existing_gps: !hasGps`
   - Neither `numUnits` nor `hasGps` are defined in `generateQuote()`, causing a JavaScript runtime `ReferenceError: numUnits is not defined` when clicking "Generar Cotización".

5. **Margin Sensitivity Range & Propagation**:
   - In `bom_excel_builder.py` lines 262-267 (`Sensibilidad` sheet), scenario margins are hardcoded as 30.0%, 45.0%, `margin_pct` (e.g. 54.8%), and 68.5%.
   - The scenarios do not dynamically pivot around the user-selected `target_margin_pct` nor cover the full 10.0% to 85.0% range.

---

## 2. Logic Chain

1. **Requirement R2 Alignment**:
   - Conecta S.A. standard pricing and OT transfer documentation requires a uniform 9-worksheet structure (`Ficha`, `Resumen`, `Control HH y Costos`, `Equi. Mat. Arr. Sub.`, `Cash Flow`, `Cliente`, `Expenses y Logistica`, `Terminos de Pago`, `Check y Sensibilidad`).
   - The current generator builds 14 sheets, which creates clutter and breaks downstream parsing scripts expecting the official 9-sheet format.

2. **Formula Integrity**:
   - Modern enterprise Excel workbooks must maintain complete auditability where summary sheets (`Resumen`, `Cash Flow`, `Check y Sensibilidad`) dynamically derive values from detail sheets (`Control HH y Costos`, `Equi. Mat. Arr. Sub.`, `Expenses y Logistica`) using live Excel formulas (`SUM`, `PRODUCT`, sheet references `=Resumen!B4*0.5`).
   - Writing raw pre-computed Python numbers prevents standard Excel recalculation and violates automated workbook verification.

3. **End-to-End Dynamic Margin Pipeline**:
   - The UI permits margin entry between 10.0% and 85.0%.
   - However, `FinancialImpactEngine` enforces a static constant `54.8%`, causing a discrepancy between UI proposal calculations and backend financial engine ROI metrics.
   - Providing an optional `target_margin_pct` parameter (defaulting to 54.8%) restores full consistency across the UI, financial engine, swarm agent, and BOM builder.

---

## 3. Caveats

- Historical reference workbooks in `ot_7000` / `ot_8000_smart_extracted` / `2025/` contain macro-enabled `.xlsm` files with legacy sheet names. Requirement R2 standardizes these into Conecta's official 9 clean `.xlsx` worksheets.
- Openpyxl evaluates formula strings when opened in Microsoft Excel or LibreOffice; when generating `.xlsx` files programmatically, initial calculated values can be supplied or calculated by Excel upon opening.

---

## 4. Conclusion

The current implementation in `bom_excel_builder.py`, `financial_engine.py`, `app.py`, and `comercial.html` has **7 major technical gaps** (2 CRITICAL, 3 HIGH, 2 MEDIUM) preventing full compliance with Requirement R2 and dynamic margin configuration (10.0% to 85.0%).

### Actionable Implementation Plan for Worker M3:

1. **Refactor `src/operations/bom_excel_builder.py`**:
   - Restructure sheet creation to generate exactly Conecta's 9 official worksheets:
     1. `Ficha`
     2. `Resumen`
     3. `Control HH y Costos` (consolidates HH matrix, role rates, and activity totals)
     4. `Equi. Mat. Arr. Sub.` (hardware, materials, equipment rentals, subcontracts)
     5. `Cash Flow` (EDP 1 Pre-kitting 50%, EDP 2 SAT HIL 50%)
     6. `Cliente`
     7. `Expenses y Logistica` (travel, trucks, Sicop accreditation, site logistics)
     8. `Terminos de Pago` (30-day payment, 10% performance bond, warranty)
     9. `Check y Sensibilidad` (combines checklist & sensitivity matrix for 10.0% - 85.0% margins)
   - Replace static Python pre-calculated cell values with live openpyxl Excel formulas (`=SUM(...)`, `=B4*0.19`, `=E4*F4`, `='Equi. Mat. Arr. Sub.'!G100`, etc.).

2. **Refactor `src/operations/financial_engine.py`**:
   - Add `target_margin_pct: Optional[float] = None` parameter to `retained_gross_margin_pct()`, `calculate_financial_summary()`, and `calculate_financial_summary()`. Default to 54.8% when `None`.
   - Update `/api/operations/metrics` in `src/supervisor_ui/app.py` to parse `margin_pct` from query params.

3. **Fix JS Bug in `src/supervisor_ui/templates/comercial.html`**:
   - Declare missing variables in `generateQuote()`:
     ```javascript
     const numUnits = parseInt(document.getElementById('unitsInput').value || 1);
     const hasGps = (document.getElementById('gpsInput').value === 'true');
     ```

4. **Dynamic Margin Sensitivity Table**:
   - Update sheet `Check y Sensibilidad` to generate 5 sensitivity scenarios dynamically centered around `target_margin_pct` spanning from 10.0% to 85.0% (e.g. 10.0%, 30.0%, `target_margin_pct`, 68.5%, 85.0%).

---

## 5. Verification Method

Worker M3 can verify the completed implementation using the following steps:

1. **Python Unit Tests**:
   - Create `tests/test_bom_excel_builder_r2.py` and run `pytest tests/test_bom_excel_builder_r2.py tests/test_financial_engine.py`:
     - Verify generated workbook contains exactly 9 sheets: `['Ficha', 'Resumen', 'Control HH y Costos', 'Equi. Mat. Arr. Sub.', 'Cash Flow', 'Cliente', 'Expenses y Logistica', 'Terminos de Pago', 'Check y Sensibilidad']`.
     - Inspect cell values for formula strings starting with `=` (e.g. `assert ws['B5'].value == '=B4*0.19'`).
     - Test workbook generation with target margins 10.0%, 30.0%, 54.8%, 68.5%, and 85.0%.

2. **REST API Endpoint Verification**:
   - Trigger `POST /api/request-quote` with `margin_pct = 40.0`.
   - Call `GET /api/documents/download?draft_id=<id>&doc_type=bom_xlsx` and verify response header is `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
   - Call `GET /api/operations/metrics?num_ots=5&margin_pct=30.0` and verify `retained_gross_margin_pct` returns `30.0`.
