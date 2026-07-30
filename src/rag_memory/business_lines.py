"""
Business Line Taxonomy, BOM Catalog, and Guided Workflow Engine for rag_memory & swarm_engine.
Classifies commercial proposals and tenders into specialized lines of business and builds BOM templates.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BusinessLineType(str, Enum):
    PMU_PDC = "pmu_pdc"
    SITR_PMGD = "sitr_pmgd"
    SCADA_RETROFIT = "scada_retrofit"
    EDAC_ERAG_STUDIES = "edac_erag_studies"
    MAINTENANCE_LICENSES = "maintenance_licenses"
    GENERAL = "general"


class CommercialModality(str, Enum):
    COMPRA_DIRECTA = "compra_directa"
    LICITACION = "licitacion"


class TenderAntecedents(BaseModel):
    tender_code: str = "LIC-2026-CEN"
    title: str
    client_name: str
    modality: CommercialModality = CommercialModality.LICITACION
    technical_bases_summary: str = "Bases Técnicas CEN: Cumplimiento estándar NTSyCS y AT-SITR-1."
    experience_required_years: int = 3
    performance_bond_pct: float = 10.0  # 10% Boleta de Fiel Cumplimiento
    warranty_months: int = 12
    penalty_per_day_uf: float = 5.0
    required_forms: List[str] = Field(default_factory=lambda: [
        "Anexo A - Formulario de Oferta Económica",
        "Anexo B - Cuadro de Precios Unitarios y BOM",
        "Anexo C - Declaración Jurada de Cumplimiento Normativo CEN/SEC",
        "Certificado F30-1 de Cumplimiento Obligaciones Laborales"
    ])


class SavingsOpportunity(BaseModel):
    category: str  # hardware_substitution, volume_discount, engineering_efficiency
    title: str
    description: str
    estimated_savings_clp: float  # Internal cost reduction
    additional_profit_clp: float  # 100% retained by company
    margin_boost_pct: float  # Margin boost retained internally
    risk_level: str = "LOW"


class MarginOptimizationReport(BaseModel):
    total_cost_clp: float  # Initial internal cost
    optimized_cost_clp: float  # Reduced internal cost
    total_sale_price_clp: float  # Fixed price charged to client
    base_margin_clp: float  # Initial internal profit
    base_margin_pct: float
    retained_savings_clp: float  # 100% internal company profit boost
    boosted_margin_clp: float  # Total internal profit for company
    boosted_margin_pct: float  # Boosted margin percentage
    opportunities: List[SavingsOpportunity] = Field(default_factory=list)



class BOMItemCategory(str, Enum):
    HARDWARE = "hardware"
    SOFTWARE_LICENSE = "software_license"
    ENGINEERING_HOURS = "engineering_hours"
    FIELD_SERVICES = "field_services"
    REGULATORY_CERTIFICATION = "regulatory_certification"


class BOMItem(BaseModel):
    item_code: str
    description: str
    category: BOMItemCategory
    default_qty: float = 1.0
    unit: str = "unidad"
    unit_price_clp: float = 0.0
    optional: bool = False
    notes: Optional[str] = None


class BOMTemplate(BaseModel):
    business_line: BusinessLineType
    name: str
    description: str
    guided_questions: List[str] = Field(default_factory=list)
    items: List[BOMItem] = Field(default_factory=list)


# Standard BOM Templates for each Business Line
STANDARD_BOM_TEMPLATES: Dict[BusinessLineType, BOMTemplate] = {
    BusinessLineType.PMU_PDC: BOMTemplate(
        business_line=BusinessLineType.PMU_PDC,
        name="Suministro e Integración Completa PMU y Concentrador PDC",
        description="Solución llave en mano para medición fasorial PMU y concentración PDC acorde a exigencias CEN.",
        guided_questions=[
            "¿Cuántas unidades de medición fasorial PMU se requieren instalar?",
            "¿Requiere servidor con Licencia de Concentrador PDC (Local o Corporativo)?",
            "¿Se requiere suministro de un nuevo Reloj Satelital GPS (Kronos Series 2/3), o se utilizará el reloj de sincronización existente del cliente en subestación (IRIG-B / PTP)?",
            "¿Se requiere auditoría y acompañamiento directo en las pruebas de conexión ante el Coordinador Eléctrico Nacional (CEN)?"
        ],
        items=[
            BOMItem(
                item_code="HW-VIZIMAX-PMU",
                description="Unidad de Medición Fasorial Vizimax SynchroTeq Plus PMU (Clase A IEEE C37.118)",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=9500000.0,
            ),
            BOMItem(
                item_code="HW-GPS-CLOCK",
                description="Reloj de Sincronización de Tiempo GPS/GNSS Kronos Series 2/3 con salidas IRIG-B e IEEE 1588 PTP (Opcional si cliente no dispone de reloj)",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=3200000.0,
            ),
            BOMItem(
                item_code="SW-PDC-LIC",
                description="Licencia de Software Concentrador de Datos Fasoriales PDC (Local / Corporativo)",
                category=BOMItemCategory.SOFTWARE_LICENSE,
                default_qty=1.0,
                unit="licencia",
                unit_price_clp=12500000.0,
            ),
            BOMItem(
                item_code="HW-SWITCH-IND",
                description="Switch Ethernet Industrial Redundante Belden Hirschmann (o Moxa) con soporte PTP IEEE 1588",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=2300000.0,
            ),
            BOMItem(
                item_code="ENG-HH-PMU-INT",
                description="Ingeniería de Integración, Configuración C37.118 y Mapeo de Canales PMU/PDC",
                category=BOMItemCategory.ENGINEERING_HOURS,
                default_qty=60.0,
                unit="horas",
                unit_price_clp=110000.0,
            ),
            BOMItem(
                item_code="FLD-FAT-SAT",
                description="Pruebas de Aceptación en Fábrica (FAT) y Pruebas en Terreno (SAT)",
                category=BOMItemCategory.FIELD_SERVICES,
                default_qty=1.0,
                unit="servicio",
                unit_price_clp=4500000.0,
            ),
            BOMItem(
                item_code="REG-CEN-AUDIT",
                description="Gestión de Auditoría y Aprobación de Conexión ante la DTR del CEN",
                category=BOMItemCategory.REGULATORY_CERTIFICATION,
                default_qty=1.0,
                unit="tramite",
                unit_price_clp=3500000.0,
            ),
        ]
    ),
    BusinessLineType.SITR_PMGD: BOMTemplate(
        business_line=BusinessLineType.SITR_PMGD,
        name="Sistema de Información en Tiempo Real (SITR) para PMGD",
        description="Solución de telemedición y telecontrol AT-SITR-1 del CEN para centrales PMGD Solares/Eólicas.",
        guided_questions=[
            "¿Cuál es la potencia instalada de la central PMGD (MW)?",
            "¿Se requiere medidor de respaldo de clase 0.2S?",
            "¿Requiere módem router industrial 4G/GPRS con túnel VPN IPsec redundante hacia el CEN?",
            "¿Incluye integración con el reconectador / celda de media tensión en el punto de conexión?"
        ],
        items=[
            BOMItem(
                item_code="HW-METER-02S",
                description="Medidor de Energía Grado Multifunción Clase 0.2S (Respaldado)",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=3800000.0,
            ),
            BOMItem(
                item_code="HW-RTU-DNP3",
                description="Gateway / RTU de Campo DNP3.0 sobre TCP/IP con Entradas/Salidas Digitales y Análogas",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=4200000.0,
            ),
            BOMItem(
                item_code="HW-MODEM-4G",
                description="Router Módem Industrial Dual-SIM 4G/LTE con Cliente VPN IPsec Certificado",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=1400000.0,
            ),
            BOMItem(
                item_code="ENG-HH-SITR",
                description="Configuración de Protocolos DNP3, Pruebas de Telemetría y SCADA Local",
                category=BOMItemCategory.ENGINEERING_HOURS,
                default_qty=40.0,
                unit="horas",
                unit_price_clp=95000.0,
            ),
            BOMItem(
                item_code="FLD-COMM-TEST",
                description="Pruebas de Comunicación de Punta a Punta con el Coordinador Eléctrico Nacional",
                category=BOMItemCategory.FIELD_SERVICES,
                default_qty=1.0,
                unit="servicio",
                unit_price_clp=2800000.0,
            ),
        ]
    ),
    BusinessLineType.SCADA_RETROFIT: BOMTemplate(
        business_line=BusinessLineType.SCADA_RETROFIT,
        name="Digitalización SCADA y Suministro de Remotas (RTU / Telecontrol)",
        description="Arquitectura de control y telemetría de subestación con Remotas (RTU), Módulos de Entradas/Salidas I/O, Switches Ethernet y Router 4G DNP3.",
        guided_questions=[
            "¿Cuántas Unidades Terminales Remotas (RTU / Remotas) se requieren instalar o reemplazar?",
            "¿Cuántas tarjetas de Entradas/Salidas Digitales y Análogas (DI/DO/AI) requiere la Remota?",
            "¿Requiere Switch Ethernet Industrial y Router 4G/Dual SIM para enlace DNP3 TCP/IP con el Coordinador (CEN)?",
            "¿Qué protocolo de telecontrol se utilizará con el CDC (DNP3.0 TCP/IP / IEC 60870-5-104 / IEC 61850)?"
        ],
        items=[
            BOMItem(
                item_code="HW-RTU-NOVATECH",
                description="Unidad Terminal Remota RTU de Subestación (Novatech Orion MX / ABB RTU560 / Moxa)",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=9800000.0,
            ),
            BOMItem(
                item_code="HW-IO-CARDS",
                description="Módulo de Expansión Entradas/Salidas Digitales y Análogas (DI/DO/AI) para Remota RTU",
                category=BOMItemCategory.HARDWARE,
                default_qty=2.0,
                unit="tarjeta",
                unit_price_clp=1850000.0,
            ),
            BOMItem(
                item_code="HW-SWITCH-IND",
                description="Switch Ethernet Industrial Redundante Belden Hirschmann de Subestación IEC 61850 / DNP3",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=2300000.0,
            ),
            BOMItem(
                item_code="HW-ROUTER-4G",
                description="Router Módem Industrial Dual-SIM 4G/LTE con Cliente VPN DNP3 TCP/IP hacia CEN",
                category=BOMItemCategory.HARDWARE,
                default_qty=1.0,
                unit="unidad",
                unit_price_clp=1400000.0,
            ),
            BOMItem(
                item_code="ENG-HH-SCADA",
                description="Ingeniería de Configuración de Base de Datos SCADA, Tabla de Señales DNP3 y Pruebas",
                category=BOMItemCategory.ENGINEERING_HOURS,
                default_qty=50.0,
                unit="horas",
                unit_price_clp=110000.0,
            ),
            BOMItem(
                item_code="FLD-FAT-SAT-RTU",
                description="Pruebas FAT en Taller y Comisionamiento SAT en Terreno para Remota RTU",
                category=BOMItemCategory.FIELD_SERVICES,
                default_qty=1.0,
                unit="servicio",
                unit_price_clp=3800000.0,
            ),
        ]
    ),
    BusinessLineType.EDAC_ERAG_STUDIES: BOMTemplate(
        business_line=BusinessLineType.EDAC_ERAG_STUDIES,
        name="Estudio de Coordinación de Protecciones y Ajuste EDAC/ERAG",
        description="Consultoría especializada en modelación DIgSILENT PowerFactory y ajuste de relés.",
        guided_questions=[
            "¿Cuántas subestaciones o alimentadores abarca el estudio?",
            "¿Requiere simulación de flujo de potencia y cortocircuito en DIgSILENT PowerFactory?",
            "¿Incluye tramitación de informe técnico certificado ante la SEC y presentación al CEN?"
        ],
        items=[
            BOMItem(
                item_code="ENG-DIGSILENT-MODEL",
                description="Modelación de Red de Transmisión/Distribución en DIgSILENT PowerFactory",
                category=BOMItemCategory.ENGINEERING_HOURS,
                default_qty=1.0,
                unit="estudio",
                unit_price_clp=15000000.0,
            ),
            BOMItem(
                item_code="ENG-EDAC-CALC",
                description="Cálculo de Curvas de Tiempo-Corriente y Ajustes EDAC/ERAG",
                category=BOMItemCategory.ENGINEERING_HOURS,
                default_qty=1.0,
                unit="estudio",
                unit_price_clp=12000000.0,
            ),
            BOMItem(
                item_code="REG-SEC-CERT",
                description="Elaboración e Inscripción de Informe Técnico Certificado por la SEC",
                category=BOMItemCategory.REGULATORY_CERTIFICATION,
                default_qty=1.0,
                unit="informe",
                unit_price_clp=3500000.0,
            ),
        ]
    ),
    BusinessLineType.MAINTENANCE_LICENSES: BOMTemplate(
        business_line=BusinessLineType.MAINTENANCE_LICENSES,
        name="Mantenimiento Preventivo de Relés y Actualización de Licencias",
        description="Inyección de corriente secundaria, calibración de relés y actualización de licencias software.",
        guided_questions=[
            "¿Cuántos relés de protección requieren inyección secundaria y prueba de disparo?",
            "¿Qué licencias software de supervisión o PDC requieren renovación anual?"
        ],
        items=[
            BOMItem(
                item_code="FLD-RELAY-TEST",
                description="Prueba de Inyección Secundaria y Calibración por Relé de Protección",
                category=BOMItemCategory.FIELD_SERVICES,
                default_qty=5.0,
                unit="rele",
                unit_price_clp=750000.0,
            ),
            BOMItem(
                item_code="SW-RENEWAL-LIC",
                description="Renovación Anual de Licencia de Mantenimiento y Soporte Software PDC",
                category=BOMItemCategory.SOFTWARE_LICENSE,
                default_qty=1.0,
                unit="anual",
                unit_price_clp=4500000.0,
            ),
        ]
    )
}


class BusinessLineClassifier:
    """Classifies queries, project titles, and folder contents into BusinessLineTypes."""

    @classmethod
    def classify(cls, text: str) -> BusinessLineType:
        if not text:
            return BusinessLineType.GENERAL
        
        t = text.lower()
        
        # 1. Maintenance & Relays Calibration (Higher priority if explicitly Maintenance / Support / Licenses)
        if any(k in t for k in ["mantenimiento", "inyeccion", "calibracion", "contrato marco", "soporte", "licencia", "licencias"]):
            return BusinessLineType.MAINTENANCE_LICENSES

        # 2. PMU / PDC (Specific to Synchrophasors / WAPMS)
        if any(k in t for k in ["pmu", "pmus", "pdc", "fasorial", "c37.118", "wapms", "centella", "huasco"]):
            return BusinessLineType.PMU_PDC

        # 3. SCADA / RTU / Remotas (Specific to Remote Terminal Units & Substation Automation)
        if any(k in t for k in ["rtu", "rtus", "remota", "remotas", "scada", "telecontrol", "orion", "sicam", "560", "61850", "plantscape"]):
            return BusinessLineType.SCADA_RETROFIT

        # 4. SITR / PMGD (Specific to PMGD Telemetry & AT-SITR-1)
        if any(k in t for k in ["sitr", "pmgd", "telemetria", "telemedicion", "dnp3", "at-sitr-1", "reconectador"]):
            return BusinessLineType.SITR_PMGD

        # 5. EDAC / ERAG / Protecciones / Estudios
        if any(k in t for k in ["edac", "erag", "digsilent", "cortocircuito", "protecciones", "estudio", "estudios", "ajuste", "ajustes", "selectividad"]):
            return BusinessLineType.EDAC_ERAG_STUDIES
            
        return BusinessLineType.GENERAL


class GuidedArchitectureEngine:
    """
    Engine to build decoupled guided quotes based on Basic & Detailed Engineering Architectures.
    Differentiates PMUs (PMU SEL-735 + Reloj GPS IRIG-B/PTP + PDC) from RTUs (Remotas Orion MX + Tarjetas I/O + Switch + Router 4G DNP3).
    """

    ARCHITECTURES: Dict[str, Dict[str, Any]] = {
        "pmu_pdc": {
            "title": "Arquitectura Medición Fasorial PMU & PDC",
            "required_components": ["Medidor PMU (SEL-735)", "Reloj GPS IRIG-B / PTP IEEE 1588", "Switch Industrial IEC 61850", "Concentrador PDC (Orion MX)"],
            "protocol": "IEEE C37.118 / NTSyCS Cap. 4",
            "excluded_questions": ["Entradas/Salidas Análogas RTU", "Módem 4G GPRS PMGD"],
            "guidance_summary": "Arquitectura de sincronía fasorial. Exige Reloj GPS IRIG-B (<1µs) y streaming C37.118."
        },
        "scada_retrofit": {
            "title": "Arquitectura Remota RTU & SCADA de Subestación",
            "required_components": ["Remota / RTU (Novatech Orion MX / ABB RTU560)", "Tarjetas Entradas/Salidas DI/DO/AI", "Switch Ethernet Industrial", "Router Industrial 4G DNP3"],
            "protocol": "DNP3.0 TCP/IP / IEC 60870-5-104 / AT-SITR-1",
            "excluded_questions": ["Medidor Fasorial PMU", "Tramas IEEE C37.118", "Servidor PDC"],
            "guidance_summary": "Arquitectura de Remota RTU / Telecontrol. NO requiere PMUs ni Concentrador PDC."
        },
        "sitr_pmgd": {
            "title": "Arquitectura SITR Telemedición PMGD",
            "required_components": ["Medidor Principal Clase 0.2S", "Gateway RTU SITR", "Router 4G Dual SIM VPN"],
            "protocol": "DNP3.0 TCP/IP / AT-SITR-1 CEN",
            "excluded_questions": ["Medidor Fasorial PMU", "Servidor PDC"],
            "guidance_summary": "Arquitectura SITR PMGD para inyección a red de distribución."
        }
    }

    @classmethod
    def get_architecture_guidance(cls, business_line: str) -> Dict[str, Any]:
        key = (business_line or "pmu_pdc").lower().strip()
        arch = cls.ARCHITECTURES.get(key, cls.ARCHITECTURES["scada_retrofit"])
        template = STANDARD_BOM_TEMPLATES.get(BusinessLineType(key) if key in BusinessLineType.__members__.values() else BusinessLineType.SCADA_RETROFIT)
        return {
            "business_line": key,
            "architecture": arch,
            "guided_questions": template.guided_questions if template else [],
            "bom_items": [item.model_dump() for item in (template.items if template else [])]
        }

