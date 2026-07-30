"""
Commercial One-Pager & Market Expansion Campaign Engine.
Leverages Conecta's installed PDC/PMU base (Transelec, AES Andes, Colbún, Engie, CGE, Pelambres, Arauco)
to generate high-converting 1-page proposals and targeted commercial campaigns.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OnePagerProposal(BaseModel):
    onepager_id: str
    title: str
    target_audience: str
    pain_point: str
    conecta_value_proposition: str
    key_equipment_brand: str
    standard_pricing_uf: float
    standard_pricing_clp: float
    regulatory_normative_hook: str
    roi_business_case: str


class TargetedCampaign(BaseModel):
    campaign_id: str
    campaign_name: str
    target_segment: str
    installed_base_targets: List[str]
    value_proposition: str
    primary_solution_onepager_id: str
    estimated_target_clients_count: int
    potential_market_revenue_clp: float
    recommended_outreach_channel: str

    @property
    def target_client_types(self) -> List[str]:
        return self.installed_base_targets

    @property
    def key_talking_points(self) -> List[str]:
        return [self.value_proposition, self.recommended_outreach_channel]


class CampaignOnePagerEngine:
    """Generates One-Pager proposals and targeted market expansion campaigns."""

    INSTALLED_PDC_CLIENTS = [
        {"client": "Transelec S.A.", "pdc_sites": ["Maitencillo", "Zona Norte"], "pmu_sites": ["Ancud", "Parral", "Cerro Navia"]},
        {"client": "AES Andes S.A.", "pdc_sites": ["PDC Corporativo"], "pmu_sites": ["Bolero", "Campo Lindo", "PE San Matías"]},
        {"client": "Generadora Metropolitana", "pdc_sites": ["CEME 1"], "pmu_sites": ["CEME 1 220kV"]},
        {"client": "Engie Energía Chile", "pdc_sites": ["Libélula"], "pmu_sites": ["SynchroTeq Vizimax"]},
        {"client": "Colbún S.A.", "pdc_sites": ["PDC Central"], "pmu_sites": ["PE Totoral"]},
        {"client": "CGE Transmisión", "pdc_sites": ["PDC Licencias"], "pmu_sites": ["SE Chillán"]},
        {"client": "Minera Pelambres (Gel Tap)", "pdc_sites": ["PDC Pelambres Redundante"], "pmu_sites": ["Mantos Blancos"]},
        {"client": "Arauco S.A.", "pdc_sites": ["PDC Redundante 8 PMUs"], "pmu_sites": ["Planta Arauco"]},
        {"client": "Pacific Hydro", "pdc_sites": ["PDC Centralizado"], "pmu_sites": ["Punta Sierra", "Chacayes"]},
        {"client": "Sonnedix Chile", "pdc_sites": ["PDC Norte"], "pmu_sites": ["Meseta de los Andes"]}
    ]

    ONE_PAGERS: List[Dict[str, Any]] = [
        {
            "onepager_id": "ONEPAGER-PDC-UPGRADE",
            "title": "Upgrade a Concentrador PDC Corporativo Redundante WAPMS",
            "target_audience": "Empresas Generadoras y Transmisoras con PMUs Aisladas",
            "pain_point": "Pérdida de tramas fasoriales por caídas de enlace y falta de concentración redundante con buffer de 30 días exigido por el CEN.",
            "conecta_value_proposition": "Servidor PDC Redundante NovaTech Orion MX / SEL-3530 con filtrado C37.118-2011 y tablero Rittal IP65.",
            "key_equipment_brand": "NovaTech Orion MX PDC / SEL-3530",
            "standard_pricing_uf": 750.0,
            "standard_pricing_clp": 28782000.0,
            "regulatory_normative_hook": "NTSyCS Cap. 4 & Exigencia DTR del Coordinador Eléctrico Nacional.",
            "roi_business_case": "Garantiza streaming fasorial continuo 99.9%, elimina apercibimientos del CEN y centraliza la medición de hasta 32 PMUs."
        },
        {
            "onepager_id": "ONEPAGER-VIZIMAX-POW",
            "title": "Control de Onda (Point-on-Wave) Vizimax SynchroTeq Plus para Transformadores HV",
            "target_audience": "Subestaciones de Alta Tensión (110kV/220kV/500kV) con Transformadores de Potencia",
            "pain_point": "Corrientes de inrush destructivas y sobretensiones transitorias en maniobras de cierre de interruptores HV.",
            "conecta_value_proposition": "Controlador de maniobra síncrona Vizimax SynchroTeq Plus (Canadá) con algoritmo adaptativo de precisión sub-milisegundo.",
            "key_equipment_brand": "VIZIMAX SynchroTeq Plus (Canadá)",
            "standard_pricing_uf": 1250.0,
            "standard_pricing_clp": 47971000.0,
            "regulatory_normative_hook": "NTSyCS Cap. 3 Calidad de Alimentación & Control de Transitorios.",
            "roi_business_case": "Reducción del 90% en la corriente de inrush, multiplicando por 3 la vida útil de los contactos del interruptor y bobinados del transformador."
        },
        {
            "onepager_id": "ONEPAGER-SLA-SITR",
            "title": "SLA Anual de Monitoreo & Auditoría de Disponibilidad Telemetría SITR/PMU (99.9%)",
            "target_audience": "Plantas PMGD y Parques Solares/Eólicos coordinados ante el CEN",
            "pain_point": "Riesgo constante de multas SEC por indisponibilidad de enlace DNP3/C37.118 inferior al 99.9% mensual.",
            "conecta_value_proposition": "Servicio de monitoreo remoto 24/7, informe mensual de disponibilidad y atención prioritaria en terreno en < 4 horas.",
            "key_equipment_brand": "Plataforma de Auditoría Conecta SITR-Guard & Kitting Engine",
            "standard_pricing_uf": 480.0,
            "standard_pricing_clp": 18421000.0,
            "regulatory_normative_hook": "Norma Técnica de Conexión y Operación (SITR AT-SITR-1 / SEC).",
            "roi_business_case": "Protección total ante multas SEC de hasta 1,000 UTA y aseguramiento de pago continuo de inyecciones de energía."
        },
        {
            "onepager_id": "ONEPAGER-OT-CYBER",
            "title": "Auditoría & Bastionado de Ciberseguridad OT de Subestaciones (IEC 62443 / SEC)",
            "target_audience": "Operadores de Infraestructura Crítica Eléctrica y Subestaciones SCADA",
            "pain_point": "Vulnerabilidades en remotas RTU, switches y routers 4G expuestos a ataques de red y no cumplimiento de directrices SEC.",
            "conecta_value_proposition": "Evaluación de vulnerabilidades OT, segmentación de VLANs en switches Belden Hirschmann/Moxa y túneles VPN IPsec hardened.",
            "key_equipment_brand": "Belden Hirschmann RS20/RS30 & Router Teltonika IPsec",
            "standard_pricing_uf": 550.0,
            "standard_pricing_clp": 21107000.0,
            "regulatory_normative_hook": "Resolución de Ciberseguridad OT SEC & Estándar Internacional IEC 62443.",
            "roi_business_case": "Mitigación de riesgos de ciberataques a sistemas de control y aprobación inmediata en auditorías de ciberseguridad SEC."
        }
    ]

    @classmethod
    def get_all_onepagers(cls) -> List[OnePagerProposal]:
        """Returns all 4 high-converting commercial One-Pagers."""
        return [OnePagerProposal(**op) for op in cls.ONE_PAGERS]

    @classmethod
    def get_onepager_by_id(cls, onepager_id: str) -> Optional[OnePagerProposal]:
        """Returns a specific One-Pager by ID."""
        for op in cls.ONE_PAGERS:
            if op["onepager_id"].upper() == onepager_id.strip().upper():
                return OnePagerProposal(**op)
        return None

    @classmethod
    def build_targeted_campaigns(cls) -> List[TargetedCampaign]:
        """Builds targeted marketing & sales campaigns to capture market share."""
        campaigns = [
            TargetedCampaign(
                campaign_id="CAMP-2026-PDC-UPGRADE",
                campaign_name="CAMPAÑA 1: Upgrade PDC Corporativo Redundante WAPMS",
                target_segment="Empresas con Base Instalada de PMUs (Transelec, AES Andes, Colbún, Arauco, Pacific Hydro)",
                installed_base_targets=["Transelec (Maitencillo/Zona Norte)", "AES Andes (Bolero/Campo Lindo)", "Arauco (Redundante)", "Pelambres"],
                value_proposition="Migración e integración a Concentradores PDC Redundantes NovaTech Orion MX / SEL-3530 con buffer de 30 días.",
                primary_solution_onepager_id="ONEPAGER-PDC-UPGRADE",
                estimated_target_clients_count=15,
                potential_market_revenue_clp=431730000.0,
                recommended_outreach_channel="Executive Briefing & Demo HIL Laboratorio a Gerentes de Mantenimiento y Transmisión"
            ),
            TargetedCampaign(
                campaign_id="CAMP-2026-VIZIMAX-POW",
                campaign_name="CAMPAÑA 2: Protege tu Transformador con Vizimax Controlled Switching",
                target_segment="Subestaciones 110kV/220kV/500kV de Empresas Transmisoras y Mineras",
                installed_base_targets=["Transelec", "ISA Interchile", "Chilquinta", "CGE", "Codelco", "Antofagasta Minerals"],
                value_proposition="Reducción del 90% en corrientes de inrush y sobretensiones en cierre de interruptores HV usando Vizimax SynchroTeq Plus.",
                primary_solution_onepager_id="ONEPAGER-VIZIMAX-POW",
                estimated_target_clients_count=20,
                potential_market_revenue_clp=959420000.0,
                recommended_outreach_channel="Seminario Técnico de Ingeniería de Transitorios & Prueba Pilot con Vizimax"
            ),
            TargetedCampaign(
                campaign_id="CAMP-2026-SLA-SITR",
                campaign_name="CAMPAÑA 3: Cero Multas SEC - SLA Telemetría SITR/PMU 99.9%",
                target_segment="Parques Fotovoltaicos, Eólicos y PMGDs en Chile",
                installed_base_targets=["Sonnedix", "Grenergy", "Generadora Metropolitana", "Atlas Renewable", "Natura Energy"],
                value_proposition="Garantía de disponibilidad de telemetría 99.9% ante el CEN con atención en terreno < 4h y reportabilidad automatizada.",
                primary_solution_onepager_id="ONEPAGER-SLA-SITR",
                estimated_target_clients_count=45,
                potential_market_revenue_clp=828945000.0,
                recommended_outreach_channel="Campaña Digital LinkedIn B2B & Mailing Directo a Asset Managers de Parques Renovables"
            ),
            TargetedCampaign(
                campaign_id="CAMP-2026-OT-CYBER",
                campaign_name="CAMPAÑA 4: Shield OT - Ciberseguridad Subestaciones IEC 62443",
                target_segment="Operadores SCADA y Subestaciones Críticas del SEN",
                installed_base_targets=["Chilquinta", "CGE", "ADASA", "Metro de Santiago", "CMP", "ENAP"],
                value_proposition="Bastionado de remotas RTU, switches Belden Hirschmann y routers 4G con certificación de cumplimiento SEC.",
                primary_solution_onepager_id="ONEPAGER-OT-CYBER",
                estimated_target_clients_count=25,
                potential_market_revenue_clp=527675000.0,
                recommended_outreach_channel="Workshop de Ciberseguridad OT & Audit Express Gratuito de Puertos de Subestación"
            )
        ]
        return campaigns

    @classmethod
    def evaluate_solution_efficiency_matrix(cls) -> List[Dict[str, Any]]:
        """
        Evaluates and ranks Conecta's solutions based on Margin % and Execution Ease.
        Ranks solutions to highlight 'Sweet Spot' quick wins for maximum short-term cash flow.
        """
        matrix = [
            {
                "solution_name": "SLA Anual Monitoreo & Auditoría Disponibilidad SITR/PMU (99.9% CEN)",
                "retained_margin_pct": 68.5,
                "execution_days": 1.0,
                "software_automation_level": "95% (100% Remoto)",
                "field_friction": "NULA (0 días terreno, sin acreditación faena)",
                "cash_flow_velocity_days": 5.0,
                "matrix_quadrant": "SWEET SPOT #1 (Máximo Margen + Ejecución Inmediata)",
                "priority_rank": 1,
                "recommendation": "OFRECER DE INMEDIATO. Alta recurrencia mensual (ARR), sin costo de traslados a terreno."
            },
            {
                "solution_name": "Servicio Express Acreditación Personal Faenas (Pronexo / Sicop)",
                "retained_margin_pct": 72.0,
                "execution_days": 0.2,
                "software_automation_level": "90% (AccreditationAutomator)",
                "field_friction": "NULA (100% Digital en Gabinete)",
                "cash_flow_velocity_days": 3.0,
                "matrix_quadrant": "SWEET SPOT #2 (Margen Excepcional + Entrega Digital)",
                "priority_rank": 2,
                "recommendation": "VENDER EN BUNDLE con cualquier servicio de ingeniería o montaje en faena."
            },
            {
                "solution_name": "Auditoría & Bastionado Ciberseguridad OT (IEC 62443 / SEC)",
                "retained_margin_pct": 58.0,
                "execution_days": 2.0,
                "software_automation_level": "80% (Scripts Audit + HIL Lab)",
                "field_friction": "MUY BAJA (Sin requerimiento de ventana de desconexión)",
                "cash_flow_velocity_days": 10.0,
                "matrix_quadrant": "QUICK WIN #3 (Alto Margen + Entrega Rápida)",
                "priority_rank": 3,
                "recommendation": "APROVECHAR FISCALIZACIONES SEC. Vender a base instalada de remotas SCADA."
            },
            {
                "solution_name": "Upgrade Concentrador PDC Corporativo Redundante NovaTech Orion MX",
                "retained_margin_pct": 52.5,
                "execution_days": 3.0,
                "software_automation_level": "75% (KittingEngine + FatSatSimulator)",
                "field_friction": "BAJA (80% Pre-cableado en taller y simulación HIL)",
                "cash_flow_velocity_days": 15.0,
                "matrix_quadrant": "PROYECTO ALTO VALOR #4 (Buen Margen + Trabajo Taller)",
                "priority_rank": 4,
                "recommendation": "VENDER A GENERADORAS. Pre-armar tableros en taller para despachar probados."
            },
            {
                "solution_name": "Control de Onda (Point-on-Wave) Vizimax SynchroTeq Plus",
                "retained_margin_pct": 54.8,
                "execution_days": 4.0,
                "software_automation_level": "65% (Configuración Vizimax HIL)",
                "field_friction": "MEDIA (Requiere ventana de desconexión en alta tensión)",
                "cash_flow_velocity_days": 20.0,
                "matrix_quadrant": "PROYECTO PREMIUM #5 (Alto Ticket + Cierta Complejidad)",
                "priority_rank": 5,
                "recommendation": "APUNTAR A TRANSMISORAS Y MINERAS. Solución de alto ticket por transformador."
            },
            {
                "solution_name": "Retrofit SCADA & Protecciones Físicas de Subestación",
                "retained_margin_pct": 42.0,
                "execution_days": 8.0,
                "software_automation_level": "50% (Montaje Físico en Patio)",
                "field_friction": "ALTA (Requiere corte CEN + estadía prolongada en faena)",
                "cash_flow_velocity_days": 30.0,
                "matrix_quadrant": "PROYECTO TRADICIONAL #6 (Mayor Carga Operativa)",
                "priority_rank": 6,
                "recommendation": "EJECUTAR SOLO CON KITTING COMPLETO. Maximizar uso de tableros pre-cableados."
            }
        ]
        return matrix
