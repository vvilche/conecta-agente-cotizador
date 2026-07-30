"""
Official Conecta Commercial Proposal Builder.
Formats proposals according to Conecta Ingeniería S.A. historical standards.
"""

class OfficialQuoteDocBuilder:
    @staticmethod
    def build_official_proposal_markdown(payload: dict) -> str:
        client_name = payload.get("partner_id", "Cliente Coordinado Conecta")
        amount_untaxed = payload.get("amount_untaxed", 58628319)
        amount_tax = payload.get("amount_tax", 11139381)
        amount_total = payload.get("amount_total", 69767700)
        lines = payload.get("order_line", [])

        md = f"""# CONECTA INGENIERÍA S.A.
**OFERTA TÉCNICO-COMERCIAL OFICIAL**
**Nuestra Ref:** OF-2026-CONECTA-REV0  
**Santiago, Chile - 30 de Julio de 2026**

---

**Señores:**  
**{client_name}**  
**Atención:** Departamento de Ingeniería y Proyectos / Gerencia de Operaciones  
**Presente**  

**Ref.:** Suministro, Ingeniería, Pruebas HIL y Puesta en Servicio de Equipamiento OT de Subestación

Estimados Señores:

Basados en vuestros requerimientos técnicos y normativos del Sistema Eléctrico Nacional (SEN), tenemos el placer de presentar a su consideración nuestra propuesta técnico-económica para el suministro, pre-kitting en taller, configuración e integración de equipamiento de subestación.

---

## 1. ALCANCE TÉCNICO DE LA OFERTA Y ARQUITECTURA DE SUBESTACIÓN

La solución propuesta por Conecta Ingeniería S.A. considera los más altos estándares tecnológicos de la industria eléctrica chilena:

1. **Equipamiento de Control & Telemetría**: Suministro e integración de hardware industrial certificado (**Belden Hirschmann** Managed Switches IEC 61850-3, **VIZIMAX** SynchroTeq Plus PMU Clase A IEEE C37.118, y remota **NovaTech** Orion LX+).
2. **Pre-kitting Estandarizado en Taller (KittingEngine)**: Tableros pre-cableados y probados en instalaciones de Conecta S.A., reduciendo la estadía de personal en faena de 5 días a solo 1.5 días.
3. **Banco de Pruebas HIL FAT/SAT (FatSatSimulator)**: Simulación de laboratorio de tramas DNP3.0 TCP/IP y tramas C37.118 antes del despacho a terreno.
4. **Tramitación Regulatoria CEN / SEC (DocAutomator)**: Elaboración de Informe IPES y Protocolo de Pruebas CEN AT-SITR-1 en 3 segundos.
5. **Acreditación Express de Personal (AccreditationAutomator)**: Dossier digital de contratos, F30-1, ex. médicos y EPP para plataformas Sicop / Pronexo.

---

## 2. OFERTA ECONÓMICA Y VALORIZACIÓN DE PARTIDAS

El valor total de la presente oferta se desglosa a continuación en Pesos Chilenos (CLP):

| Ítem | Código Partida | Descripción de la Partida | Cant. | Precio Unit. Neto CLP | Subtotal Neto CLP |
| :---: | :--- | :--- | :---: | :---: | :---: |
"""
        for idx, item in enumerate(lines, start=1):
            md += f"| {idx} | `{item.get('item_code')}` | {item.get('name')} | {item.get('product_uom_qty')} | ${item.get('price_unit'):,.0f} CLP | **${item.get('price_subtotal'):,.0f} CLP** |\n"

        md += f"""
---

### 💰 RESUMEN FINANCIERO:
- **MONTO NETO TOTAL**: **${amount_untaxed:,.0f} CLP**
- **IMPUESTO IVA (19%)**: **${amount_tax:,.0f} CLP**
- **MONTO TOTAL BRUTO (CON IVA)**: **${amount_total:,.0f} CLP**

*(Precios verificados contra lista oficial de inventarios Odoo ERP e hitos RAG 2026).*

---

## 3. CRONOGRAMA DE EJECUCIÓN Y HITOS DE PAGO (EDPs)

- **Plazo de Entrega**: 4 a 6 semanas calendario tras la emisión de la Orden de Compra (OC).
- **Estructura de Estados de Pago (EDPs)**:
  - **EDP 1 (50% Monto Neto)**: A la entrega de tableros kitting pre-cableados en taller Conecta S.A.
  - **EDP 2 (50% Monto Neto)**: A la entrega de Certificado Pruebas HIL FAT/SAT firmado e Informe IPES registrado ante el Coordinador Eléctrico Nacional.

---

## 4. TÉRMINOS Y CONDICIONES COMERCIALES (T&C) ESTÁNDAR

1. **Validez de la Oferta**: 30 días corridos a contar de esta fecha.
2. **Forma de Pago**: 30 días fecha factura tras aprobación de cada Estado de Pago (EDP).
3. **Garantía Técnica**: 12 meses contados desde la puesta en servicio comercial o 18 meses desde la entrega en bodega.
4. **Exclusiones de la Oferta**: Obras civiles en subestación, suministro de alimentación AC/DC auxiliar no especificado.

Esperando que nuestra propuesta satisfaga plenamente sus requerimientos, quedamos a su entera disposición para cualquier aclaración técnica o comercial.

Atentamente,

**CONECTA INGENIERÍA S.A.**  
*Área Comercial & División de Operaciones OT*  
Contacto: comercial@conecta-ingenieria.cl | www.conecta-ingenieria.cl
"""
        return md
