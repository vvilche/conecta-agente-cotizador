"""
Advanced Data Intelligence & Value Maximization Engine.
Unlocks 6 high-value capabilities from the 2026 Commercial Database:
1. Regulatory Compliance Audit (CEN / SEC / NTSyCS).
2. Automated Single Line Diagram (SLD) JSON builder (IEC 60617 standard).
3. Commercial Win-Rate Estimator by Client Elasticity.
4. SLA Cross-Selling & Recurring Revenue Discovery Engine.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ComplianceWarning(BaseModel):
    rule_id: str
    severity: str  # CRITICAL, WARNING, INFO
    standard: str  # NTSyCS, AT-SITR-1, DTR_CEN, SEC
    message: str
    recommended_addition: str


class RegulatoryAuditReport(BaseModel):
    compliance_score: float  # 0.0 to 1.0
    status: str  # COMPLIANT, WARNINGS_FOUND, CRITICAL_GAPS
    warnings: List[ComplianceWarning] = Field(default_factory=list)


class WinRatePrediction(BaseModel):
    client_name: str
    proposed_margin_pct: float
    estimated_win_rate_pct: float
    recommended_margin_pct: float
    client_sensitivity: str  # HIGH_PRICE_SENSITIVE, BALANCED, QUALITY_FOCUSED
    rationale: str


class CrossSellOpportunity(BaseModel):
    client_name: str
    installed_base_equipment: str
    suggested_service: str
    estimated_annual_revenue_clp: float
    business_case: str


class RegulatoryComplianceAuditor:
    """
    Preventive CEN/SEC Regulatory Compliance Auditor.
    Scans BOM proposals for missing mandatory regulatory components (IRIG-B GPS, DNP3 redundant streams, FAT/SAT DTR protocols).
    """

    @staticmethod
    def audit_proposal(proposed_lines: List[Dict[str, Any]], business_line: str) -> RegulatoryAuditReport:
        warnings = []
        has_pmu = any("pmu" in str(l.get("item_code", "")).lower() or "pmu" in str(l.get("name", "")).lower() for l in proposed_lines)
        has_gps = any("gps" in str(l.get("item_code", "")).lower() or "gps" in str(l.get("name", "")).lower() or "irig" in str(l.get("name", "")).lower() for l in proposed_lines)
        has_pdc = any("pdc" in str(l.get("item_code", "")).lower() or "pdc" in str(l.get("name", "")).lower() for l in proposed_lines)
        has_cen_tests = any("cen" in str(l.get("name", "")).lower() or "ensayo" in str(l.get("name", "")).lower() for l in proposed_lines)

        if has_pmu and not has_gps:
            warnings.append(ComplianceWarning(
                rule_id="REG-NTSYCS-01",
                severity="CRITICAL",
                standard="NTSyCS Cap. 4 (Sincronización Temporal)",
                message="La propuesta contempla PMUs pero no incluye Reloj GPS con salida IRIG-B / PTP 1588.",
                recommended_addition="Agregar Reloj GPS IRIG-B de alta precisión (sincronización < 1µs)."
            ))

        if has_pmu and not has_pdc:
            warnings.append(ComplianceWarning(
                rule_id="REG-DTR-CEN-02",
                severity="WARNING",
                standard="DTR CEN (Concentración Fasorial)",
                message="Se instalan PMUs sin PDC local o concentrador corporativo para streaming IEEE C37.118.",
                recommended_addition="Verificar si la subestación cuenta con PDC existente o incluir concentrador PDC local."
            ))

        if (has_pmu or business_line == "pmu_pdc") and not has_cen_tests:
            warnings.append(ComplianceWarning(
                rule_id="REG-CEN-DTR-03",
                severity="WARNING",
                standard="Guía de Puesta en Servicio CEN",
                message="Falta incluir la partida de Ensayos de Validación y Protocolo de Puesta en Servicio CEN.",
                recommended_addition="Agregar servicio de Pruebas de Campo y Protocolos de Validación CEN."
            ))

        score = 1.0 - (0.3 * len([w for w in warnings if w.severity == "CRITICAL"])) - (0.1 * len([w for w in warnings if w.severity == "WARNING"]))
        score = max(0.0, score)

        status = "COMPLIANT" if not warnings else ("CRITICAL_GAPS" if any(w.severity == "CRITICAL" for w in warnings) else "WARNINGS_FOUND")

        return RegulatoryAuditReport(
            compliance_score=score,
            status=status,
            warnings=warnings
        )


class WinRateEstimator:
    """
    Commercial Win-Rate & Pricing Elasticity Estimator.
    Calibrated with real 2026 sales execution data (Meta Ventas y Ocs 2026.xlsx).
    """

    CLIENT_PROFILES = {
        "colbun": {"sensitivity": "QUALITY_FOCUSED", "optimal_margin": 45.0, "historical_win_rate": 88.0},
        "colbún": {"sensitivity": "QUALITY_FOCUSED", "optimal_margin": 45.0, "historical_win_rate": 88.0},
        "transelec": {"sensitivity": "QUALITY_FOCUSED", "optimal_margin": 42.0, "historical_win_rate": 85.0},
        "chilquinta": {"sensitivity": "BALANCED", "optimal_margin": 35.0, "historical_win_rate": 78.0},
        "aes": {"sensitivity": "BALANCED", "optimal_margin": 32.0, "historical_win_rate": 72.0},
        "eletrans": {"sensitivity": "QUALITY_FOCUSED", "optimal_margin": 40.0, "historical_win_rate": 80.0},
        "tecnored": {"sensitivity": "HIGH_PRICE_SENSITIVE", "optimal_margin": 24.0, "historical_win_rate": 65.0},
        "cge": {"sensitivity": "HIGH_PRICE_SENSITIVE", "optimal_margin": 25.0, "historical_win_rate": 60.0},
    }

    @classmethod
    def predict_win_rate(cls, client_name: str, proposed_margin_pct: float) -> WinRatePrediction:
        norm_client = client_name.lower().strip()
        profile = None
        for k, v in cls.CLIENT_PROFILES.items():
            if k in norm_client:
                profile = v
                break

        if not profile:
            profile = {"sensitivity": "BALANCED", "optimal_margin": 28.0}

        opt_m = profile["optimal_margin"]
        sensitivity = profile["sensitivity"]

        # Calculate estimated win rate
        diff = proposed_margin_pct - opt_m
        if sensitivity == "HIGH_PRICE_SENSITIVE":
            win_rate = max(10.0, 90.0 - (diff * 4.0))
        elif sensitivity == "QUALITY_FOCUSED":
            win_rate = max(20.0, 92.0 - (diff * 1.5))
        else:
            win_rate = max(15.0, 88.0 - (diff * 2.5))

        win_rate = min(98.0, win_rate)

        rationale = (
            f"El cliente '{client_name}' presenta perfil '{sensitivity}'. "
            f"El margen óptimo recomendado para maximizar tasa de adjudicación (>85%) es {opt_m:.1f}%. "
            f"Con el margen propuesto ({proposed_margin_pct:.1f}%), la probabilidad estimada de ganancia es {win_rate:.1f}%."
        )

        return WinRatePrediction(
            client_name=client_name,
            proposed_margin_pct=proposed_margin_pct,
            estimated_win_rate_pct=win_rate,
            recommended_margin_pct=opt_m,
            client_sensitivity=sensitivity,
            rationale=rationale
        )


class CrossSellEngine:
    """
    SLA & Recurring Revenue Cross-Selling Discovery Engine.
    Cross-references historical equipment sales with CEN/SEC normative skills to discover high-margin opportunities.
    """

    @staticmethod
    def find_opportunities(client_name: str, business_line: str, total_amount_clp: float) -> List[CrossSellOpportunity]:
        opps = []
        bl = (business_line or "").lower().strip()

        # 1. Base PMU / WAPMS Opportunities
        if bl in ["pmu_pdc", "general"]:
            opps.append(CrossSellOpportunity(
                client_name=client_name,
                installed_base_equipment="Equipos VIZIMAX SynchroTeq Plus PMU & Relojes GPS Kronos",
                suggested_service="SLA Anual de Mantenimiento Preventivo, Calibración de Canales & Auditoría Disponibilidad SITR (99.9% CEN)",
                estimated_annual_revenue_clp=max(14800000.0, total_amount_clp * 0.12),
                business_case="Los contratos de medición fasorial exigen auditoría mensual de disponibilidad (99.9%) ante el CEN y calibración de canales."
            ))
            opps.append(CrossSellOpportunity(
                client_name=client_name,
                installed_base_equipment="Medidores Fasoriales PMU Standalone",
                suggested_service="Upgrade a Concentrador PDC Corporativo Redundante NovaTech Orion MX / SEL-3530",
                estimated_annual_revenue_clp=28500000.0,
                business_case="La NTSyCS Cap. 4 recomienda concentradores PDC redundantes con filtrado C37.118 y buffer de eventos antes del envío al CEN."
            ))

        # 2. Base SCADA / RTU Retrofit Opportunities
        if bl in ["scada_retrofit", "sitr_telemetry", "general"]:
            opps.append(CrossSellOpportunity(
                client_name=client_name,
                installed_base_equipment="Remotas RTU NovaTech Orion / ABB RTU560 & Switches Belden Hirschmann",
                suggested_service="Auditoría & Bastionado de Ciberseguridad OT de Subestación (Norma SEC / IEC 62443)",
                estimated_annual_revenue_clp=18500000.0,
                business_case="Las nuevas resoluciones SEC exigen evaluación de ciberseguridad, segmentación de VLANs y filtrado VPN en subestaciones críticas."
            ))

        # 3. Controlled Switching & Protection Opportunities
        if bl in ["edac_erag_studies", "pmu_pdc", "general"]:
            opps.append(CrossSellOpportunity(
                client_name=client_name,
                installed_base_equipment="Interruptores de Alta Tensión & Relés SEL / Siemens / GE",
                suggested_service="Retrofit de Control de Onda (Point-on-Wave) Vizimax SynchroTeq Plus",
                estimated_annual_revenue_clp=38000000.0,
                business_case="Mitigación de corrientes de inrush y sobretensiones transitorias en maniobras de transformadores y reactores mediante Vizimax."
            ))
            opps.append(CrossSellOpportunity(
                client_name=client_name,
                installed_base_equipment="Relés de Protección y Esquemas EDAC/ERAG",
                suggested_service="Estudio de Coordinación de Protecciones DIgSILENT & Ensayos HIL en Laboratorio",
                estimated_annual_revenue_clp=16500000.0,
                business_case="Revisión multianual de selectividad y simulación HIL ante cambios topológicos del Sistema Eléctrico Nacional."
            ))

        # 4. Turnkey Worker Accreditation Management
        opps.append(CrossSellOpportunity(
            client_name=client_name,
            installed_base_equipment="Servicios de Ingenieros en Terreno y Cuadrillas de Montaje",
            suggested_service="Servicio de Gestión Express de Acreditación de Personal (Sicop / Pronexo / RyS)",
            estimated_annual_revenue_clp=8500000.0,
            business_case="Gestión y compilación automatizada de dossiers (F30-1, ex. médicos, EPP) reduciendo demoras de acceso a faenas de 7 a 1 día."
        ))

        return opps


class OperationalIntelligenceEngine:
    """
    Operational Intelligence Engine for Work Orders & Projects.
    Provides predictive access delays, bottleneck detection, and operational risk scoring.
    """

    PLATFORM_BASE_DELAYS = {
        "sicop": 5.0,
        "pronexo": 4.0,
        "rys": 3.0,
        "direct": 1.0,
    }

    HIGH_COMPLEXITY_SUBSTATIONS = {
        "ancud", "ceme", "charrúa", "charrua", "crucero", "cardones", "encon", "quillota", "parinacota", "polpaico"
    }

    @classmethod
    def predict_access_delay(
        cls,
        substation_name: str,
        platform: str,
        num_workers: int = 1
    ) -> Dict[str, Any]:
        """
        Predicts site access and accreditation delay days.
        Guards against negative or invalid inputs.
        """
        num_workers = max(1, int(num_workers))
        plat_clean = (platform or "direct").strip().lower()
        sub_clean = (substation_name or "").strip().lower()

        base_delay = cls.PLATFORM_BASE_DELAYS.get(plat_clean, 3.5)

        # Worker scaling penalty: +0.5 days for each worker beyond 2
        worker_penalty = max(0.0, (num_workers - 2) * 0.5)

        # Complexity penalty: +2.0 days if high complexity substation
        is_complex = any(name in sub_clean for name in cls.HIGH_COMPLEXITY_SUBSTATIONS)
        complexity_penalty = 2.0 if is_complex else 0.0

        estimated_delay_days = round(base_delay + worker_penalty + complexity_penalty, 1)
        recommended_lead_time_days = int(round(estimated_delay_days * 1.5))

        bottlenecks = []
        if plat_clean == "sicop":
            bottlenecks.append("Acreditación Sicop requiere validación médica laboral previa (5 días hábiles).")
        if num_workers > 4:
            bottlenecks.append(f"Carga de acreditación elevada ({num_workers} trabajadores). Requiere revisión masiva.")
        if is_complex:
            bottlenecks.append(f"Subestación de alta complejidad ({substation_name}). Requiere inducción de seguridad presencial.")

        if estimated_delay_days >= 7.0:
            platform_risk = "HIGH"
        elif estimated_delay_days >= 4.0:
            platform_risk = "MEDIUM"
        else:
            platform_risk = "LOW"

        return {
            "substation_name": substation_name,
            "platform": plat_clean,
            "num_workers": num_workers,
            "estimated_delay_days": estimated_delay_days,
            "recommended_lead_time_days": recommended_lead_time_days,
            "platform_risk": platform_risk,
            "is_high_complexity": is_complex,
            "bottleneck_factors": bottlenecks
        }

    @classmethod
    def detect_bottlenecks(cls, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scans a list of tasks/milestones for operational bottlenecks.
        """
        if not tasks:
            return {
                "total_tasks_analyzed": 0,
                "bottlenecks_detected": [],
                "critical_count": 0,
                "high_count": 0,
                "has_critical_bottleneck": False
            }

        detected = []
        critical_count = 0
        high_count = 0

        for t in tasks:
            t_id = t.get("task_id") or t.get("id") or t.get("name") or "UNKNOWN_TASK"
            name = str(t.get("name") or t.get("title") or "").lower()
            desc = str(t.get("description") or "").lower()
            combined = f"{name} {desc}"

            # 1. Outage window bottleneck
            if any(k in combined for k in ["desconexión", "desconexion", "corte", "outage", "ventana"]):
                severity = "CRITICAL"
                critical_count += 1
                detected.append({
                    "task_id": t_id,
                    "task_name": t.get("name"),
                    "severity": severity,
                    "bottleneck_type": "SUBSTATION_OUTAGE_WINDOW",
                    "description": "Dependencia crítica de ventana de desconexión autorizada por CEN.",
                    "mitigation": "Confirmar aprobación de Coordinador Eléctrico Nacional 72h antes."
                })
            # 2. Accreditation bottleneck
            elif any(k in combined for k in ["acreditacion", "acreditación", "f30-1", "dossier", "sicop", "pronexo"]):
                if t.get("status") != "completed":
                    severity = "CRITICAL" if "bloqueado" in combined or "urgente" in combined else "HIGH"
                    if severity == "CRITICAL":
                        critical_count += 1
                    else:
                        high_count += 1
                    detected.append({
                        "task_id": t_id,
                        "task_name": t.get("name"),
                        "severity": severity,
                        "bottleneck_type": "ACCREDITATION_DELAY",
                        "description": "Falta completar dossier de acreditación para ingreso a faena.",
                        "mitigation": "Ejecutar AccreditationAutomator para compilación express."
                    })

            # 3. Hardware procurement lead time bottleneck
            elif any(k in combined for k in ["pmu", "sel-735", "rtu", "orion", "switch", "gabinete", "hardware"]):
                lead_time = t.get("lead_time_days", 0)
                if lead_time > 15 or "importacion" in combined or "stock_bajo" in combined:
                    severity = "CRITICAL" if lead_time > 30 else "HIGH"
                    if severity == "CRITICAL":
                        critical_count += 1
                    else:
                        high_count += 1
                    detected.append({
                        "task_id": t_id,
                        "task_name": t.get("name"),
                        "severity": severity,
                        "bottleneck_type": "PROCUREMENT_LEAD_TIME",
                        "description": "Tiempo de entrega prolongado de hardware crítico.",
                        "mitigation": "Revisar stock en KittingEngine o solicitar pre-cableado en taller."
                    })

            # 4. CEN testing protocol bottleneck
            elif any(k in combined for k in ["cen", "fat", "sat", "dtr", "protocolo", "ensayo"]):
                if not t.get("fat_sat_passed", False) and t.get("status") != "completed":
                    severity = "MEDIUM" if "lab" in combined else "HIGH"
                    if severity == "HIGH":
                        high_count += 1
                    detected.append({
                        "task_id": t_id,
                        "task_name": t.get("name"),
                        "severity": severity,
                        "bottleneck_type": "CEN_FAT_SAT_APPROVAL",
                        "description": "Pruebas de laboratorio o terreno del protocolo CEN pendientes.",
                        "mitigation": "Correr FatSatSimulator en modo HIL virtual antes de terreno."
                    })

        return {
            "total_tasks_analyzed": len(tasks),
            "bottlenecks_detected": detected,
            "critical_count": critical_count,
            "high_count": high_count,
            "has_critical_bottleneck": critical_count > 0
        }

    @classmethod
    def calculate_operational_risk_score(cls, ot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates operational risk score (0.0 to 100.0) and risk category.
        Guards against negative or missing values.
        """
        num_workers = max(0, int(ot_data.get("num_workers", 1)))
        num_substations = max(0, int(ot_data.get("num_substations", 1)))
        has_fat_sat_lab = bool(ot_data.get("has_fat_sat_lab", False))
        platform = str(ot_data.get("accreditation_platform") or "direct").lower()
        device_count = max(0, int(ot_data.get("device_count", 1)))
        has_cen_protocols = bool(ot_data.get("has_cen_protocols", False))

        # 1. Access risk (0 to 30 pts)
        plat_delay = cls.PLATFORM_BASE_DELAYS.get(platform, 2.0)
        access_risk = min(30.0, plat_delay * 3.0 + (num_workers * 1.5))

        # 2. Technical complexity risk (0 to 30 pts)
        tech_risk = min(30.0, device_count * 4.0 + (num_substations * 3.0))
        if has_fat_sat_lab:
            tech_risk = max(0.0, tech_risk - 12.0)  # FAT/SAT lab reduces technical risk

        # 3. Regulatory risk (0 to 25 pts)
        reg_risk = 5.0 if has_cen_protocols else 25.0

        # 4. Logistics & timeline risk (0 to 15 pts)
        logistics_risk = min(15.0, num_substations * 4.0 + (num_workers * 1.0))

        total_risk = round(access_risk + tech_risk + reg_risk + logistics_risk, 1)
        total_risk = max(0.0, min(100.0, total_risk))

        if total_risk >= 75.0:
            risk_level = "CRITICAL"
        elif total_risk >= 50.0:
            risk_level = "HIGH"
        elif total_risk >= 25.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        recommendations = []
        if access_risk > 15.0:
            recommendations.append("Compilar dossier de acreditación al menos 7 días antes con AccreditationAutomator.")
        if tech_risk > 15.0:
            recommendations.append("Utilizar KittingEngine para armar y probar tableros pre-cableados en taller.")
        if reg_risk > 15.0:
            recommendations.append("Incluir Protocolo CEN AT-SITR-1 e Informes IPES validados.")
        if not has_fat_sat_lab:
            recommendations.append("Ejecutar FatSatSimulator virtual para reducir días de comisión en terreno de 5 a 1.5 días.")

        return {
            "total_risk_score": total_risk,
            "risk_level": risk_level,
            "breakdown": {
                "access_risk": round(access_risk, 1),
                "technical_risk": round(tech_risk, 1),
                "regulatory_risk": round(reg_risk, 1),
                "logistics_risk": round(logistics_risk, 1)
            },
            "recommendations": recommendations
        }

