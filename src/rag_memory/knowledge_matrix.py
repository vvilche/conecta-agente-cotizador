"""
Knowledge Matrix Data Engine for Commercial Proposals and Tenders (2026+).
Structured representation of offer records, pricing items, technical specs, commercial terms,
and export functionality to SQLite/JSON/Excel.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import sqlite3
from pathlib import Path
from pydantic import BaseModel, Field


class OfferStatus(str, Enum):
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    NA = "n_a"


class PricingItem(BaseModel):
    item_code: Optional[str] = None
    description: str
    quantity: float = 1.0
    unit: Optional[str] = "unidad"
    unit_price: float = 0.0
    total_price: float = 0.0
    currency: str = "CLP"


class TechnicalSpec(BaseModel):
    equipment_type: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    standards: List[str] = Field(default_factory=list)
    complexity_level: str = "medium"  # low, medium, high


class CommercialTerms(BaseModel):
    payment_terms: Optional[str] = None
    delivery_days: Optional[int] = None
    warranty_months: Optional[int] = None
    penalties: Optional[str] = None
    guarantees: List[str] = Field(default_factory=list)


class OfferRecord(BaseModel):
    offer_id: str
    title: str
    client_name: str
    date: str
    status: OfferStatus = OfferStatus.PENDING
    domain: str = "general"
    category: str = "proposal"
    total_amount: float = 0.0
    currency: str = "CLP"
    pricing_items: List[PricingItem] = Field(default_factory=list)
    technical_specs: Optional[TechnicalSpec] = Field(default_factory=TechnicalSpec)
    commercial_terms: Optional[CommercialTerms] = Field(default_factory=CommercialTerms)
    win_reasons: List[str] = Field(default_factory=list)
    loss_reasons: List[str] = Field(default_factory=list)
    raw_source_path: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "title": self.title,
            "client_name": self.client_name,
            "date": self.date,
            "status": self.status.value,
            "domain": self.domain,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "items_count": len(self.pricing_items),
            "raw_source_path": self.raw_source_path,
        }


class KnowledgeMatrix:
    """
    In-memory and persistent SQLite/JSON store for structured OfferRecords.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.records: Dict[str, OfferRecord] = {}
        self.db_path = db_path or ":memory:"
        self._init_sqlite()

    def _init_sqlite(self):
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_matrix (
                    offer_id TEXT PRIMARY KEY,
                    client_name TEXT,
                    title TEXT,
                    date TEXT,
                    status TEXT,
                    domain TEXT,
                    total_amount REAL,
                    currency TEXT,
                    payload_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    def add_record(self, record: OfferRecord) -> None:
        self.records[record.offer_id] = record
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO knowledge_matrix 
                (offer_id, client_name, title, date, status, domain, total_amount, currency, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.offer_id,
                record.client_name,
                record.title,
                record.date,
                record.status.value,
                record.domain,
                record.total_amount,
                record.currency,
                record.model_dump_json(),
                record.created_at
            ))
            conn.commit()

    def get_record(self, offer_id: str) -> Optional[OfferRecord]:
        if offer_id in self.records:
            return self.records[offer_id]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json FROM knowledge_matrix WHERE offer_id = ?", (offer_id,))
            row = cursor.fetchone()
            if row:
                record = OfferRecord.model_validate_json(row[0])
                self.records[offer_id] = record
                return record
        return None

    def search(self, domain: Optional[str] = None, client_name: Optional[str] = None, status: Optional[str] = None) -> List[OfferRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT payload_json FROM knowledge_matrix WHERE 1=1"
            params = []
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            if client_name:
                query += " AND client_name LIKE ?"
                params.append(f"%{client_name}%")
            if status:
                query += " AND status = ?"
                params.append(status)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                if not r[0]:
                    continue
                try:
                    results.append(OfferRecord.model_validate_json(r[0]))
                except Exception:
                    try:
                        raw = json.loads(r[0])
                        rec = OfferRecord(
                            offer_id=str(raw.get("offer_id") or raw.get("id") or "HIST-OFFER"),
                            title=str(raw.get("title") or raw.get("folder") or raw.get("name") or "Propuesta Comercial"),
                            client_name=str(raw.get("client_name") or raw.get("client") or client_name or "Cliente SEN"),
                            date=str(raw.get("date") or raw.get("year") or "2025-01-01"),
                            total_amount=float(raw.get("total_amount") or raw.get("amount") or 0.0)
                        )
                        results.append(rec)
                    except Exception:
                        pass
            return results

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM knowledge_matrix")
            return cursor.fetchone()[0]

    def export_to_json(self, output_path: str) -> str:
        records = self.search()
        data = [r.model_dump() for r in records]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


class TechnicalKnowledgeMatrix:
    """
    Technical Knowledge Base for Regulatory Rules, CEN Protocols, and Standard BOM Lookups.
    """

    NORMATIVE_RULES: List[Dict[str, Any]] = [
        {
            "rule_id": "REG-NTSYCS-01",
            "standard": "NTSyCS Cap. 4",
            "title": "Sincronización Temporal PMU / WAPMS",
            "description": "Exige precisión de tiempo < 1µs con fuente GPS IRIG-B / PTP IEEE 1588 para todas las UMM/PMU conectadas al SEN.",
            "mandatory_component": "Reloj GPS IRIG-B / PTP IEEE 1588",
            "severity": "CRITICAL"
        },
        {
            "rule_id": "REG-AT-SITR-1",
            "standard": "AT-SITR-1 CEN",
            "title": "Protocolo de Telemetría en Tiempo Real SITR",
            "description": "Especifica arquitectura de enlace redundante TCP/IP DNP3 para envío de datos de tiempo real al CDC/CEN.",
            "mandatory_component": "Gateway DNP3 Redundante TCP/IP",
            "severity": "CRITICAL"
        },
        {
            "rule_id": "REG-SEC-05-2021",
            "standard": "SEC Res. Exenta 05/2021",
            "title": "Ciberseguridad en Sistemas de Control OT/SCADA",
            "description": "Establece exigencias de bastionado, control de acceso y segmentación de red OT según norma IEC 62443.",
            "mandatory_component": "Firewall OT IEC 62443 & Segmentación VLAN",
            "severity": "HIGH"
        },
        {
            "rule_id": "REG-DTR-CEN-02",
            "standard": "DTR CEN Cap. 3",
            "title": "Concentración de Datos Fasoriales PDC",
            "description": "Regula la concentración e ingesta de tramas IEEE C37.118 en el concentrador PDC del Coordinador.",
            "mandatory_component": "Servidor Concentrador PDC / Gateway C37.118",
            "severity": "HIGH"
        }
    ]

    CEN_PROTOCOLS: List[Dict[str, Any]] = [
        {
            "protocol_id": "CEN-PROT-FAT-01",
            "category": "FAT_LAB",
            "title": "Protocolo de Pruebas de Aceptación en Fábrica (FAT)",
            "description": "Validación en laboratorio HIL de señales binarias, analógicas y tramas C37.118 / DNP3 pre-despacho.",
            "execution_mode": "VIRTUAL_HIL_LAB",
            "typical_duration_hours": 12.0
        },
        {
            "protocol_id": "CEN-PROT-SAT-02",
            "category": "SAT_FIELD",
            "title": "Protocolo de Pruebas de Aceptación en Sitio (SAT)",
            "description": "Comisión en terreno con inyección secundaria de corriente/voltaje y verificación de punta a punta hacia CEN.",
            "execution_mode": "FIELD_SUBSTATION",
            "typical_duration_days": 1.5
        },
        {
            "protocol_id": "CEN-PROT-IPES-03",
            "category": "IPES_REPORT",
            "title": "Informe de Puesta en Servicio (IPES)",
            "description": "Documento final requerido por el CEN con diagramas unilineales, fichas técnicas y certificados FAT/SAT firmados.",
            "execution_mode": "DOC_AUTOMATION",
            "typical_duration_hours": 2.0
        },
        {
            "protocol_id": "CEN-PROT-EDAC-04",
            "category": "EDAC_SCHEME",
            "title": "Esquema de Desconexión Automática de Carga (EDAC)",
            "description": "Protocolo de pruebas de disparo por subfrecuencia y bajo voltaje según directrices de operación CEN.",
            "execution_mode": "FIELD_LAB_HYBRID",
            "typical_duration_hours": 8.0
        }
    ]

    STANDARD_BOM_CATALOG: Dict[str, List[Dict[str, Any]]] = {
        "pmu_pdc": [
            {"item_code": "HW-VIZIMAX-PMU", "name": "Medidor Vizimax SynchroTeq Plus PMU (IEEE C37.118)", "unit_price_clp": 9500000.0, "category": "hardware"},
            {"item_code": "HW-GPS-KRONOS", "name": "Sincronizador Satelital Reloj GPS Kronos Series 2/3 (IRIG-B / PTP IEEE 1588)", "unit_price_clp": 3200000.0, "category": "hardware"},
            {"item_code": "HW-GPS-CLK", "name": "Reloj de Sincronización GPS IRIG-B IEEE 1588", "unit_price_clp": 3200000.0, "category": "hardware"},
            {"item_code": "HW-ORION-MX-PDC", "name": "Gateway Concentrador PDC NovaTech Orion MX", "unit_price_clp": 4800000.0, "category": "hardware"},
            {"item_code": "HW-ORION-MX", "name": "Gateway de Comunicaciones Orion MX PDC", "unit_price_clp": 4800000.0, "category": "hardware"},
            {"item_code": "SRV-FAT-LAB", "name": "Pruebas de Laboratorio FAT HIL Sincronizadas (Simulador OPAL-RT)", "unit_price_clp": 1800000.0, "category": "service"},
            {"item_code": "SRV-SAT-FIELD", "name": "Comisionamiento en Terreno SAT & Protocolo CEN", "unit_price_clp": 2500000.0, "category": "service"}
        ],
        "sitr_telemetry": [
            {"item_code": "HW-RTU-SITR", "name": "Unidad Terminal Remota RTU NovaTech Orion MX DNP3", "unit_price_clp": 5200000.0, "category": "hardware"},
            {"item_code": "HW-ROUTER-4G", "name": "Router Industrial 4G/Dual SIM DNP3 TCP/IP", "unit_price_clp": 1400000.0, "category": "hardware"},
            {"item_code": "SRV-IPES-DOC", "name": "Elaboración de Informe IPES y Protocolo AT-SITR-1", "unit_price_clp": 1200000.0, "category": "service"}
        ],
        "scada_retrofit": [
            {"item_code": "HW-RTU-NOVATECH", "name": "Unidad Terminal Remota RTU NovaTech Orion MX / LX+", "unit_price_clp": 5400000.0, "category": "hardware"},
            {"item_code": "HW-IO-NOVACARD", "name": "Módulos de Expansión Entradas/Salidas Novacard (DI/DO/AI)", "unit_price_clp": 1800000.0, "category": "hardware"},
            {"item_code": "HW-RTU-ABB560", "name": "Unidad Terminal Remota RTU ABB RTU560 / RTU520", "unit_price_clp": 6200000.0, "category": "hardware"},
            {"item_code": "HW-SCADA-PANEL", "name": "Gabinete Rittal IP65 SCADA Retrofit Pre-cableado", "unit_price_clp": 9600000.0, "category": "hardware"},
            {"item_code": "HW-SW-MOXA", "name": "Switch Ethernet Industrial Redundante Moxa EDS-510A IEC 61850", "unit_price_clp": 2300000.0, "category": "hardware"},
            {"item_code": "HW-SW-INDUSTRIAL", "name": "Switch Ethernet Industrial Redundante IEC 61850", "unit_price_clp": 2300000.0, "category": "hardware"},
            {"item_code": "SRV-INTEG-SCADA", "name": "Servicio de Integración y Configuración SCADA (zenon / Elipse / iFIX)", "unit_price_clp": 3400000.0, "category": "service"}
        ],
        "edac_erag_studies": [
            {"item_code": "HW-RELAY-SEL", "name": "Relé de Protección SEL (SEL-421 / SEL-311C / SEL-751)", "unit_price_clp": 6800000.0, "category": "hardware"},
            {"item_code": "HW-RELAY-SIPROTEC", "name": "Relé de Protección Siemens SIPROTEC 5 / 4 (7SJ / 7SA)", "unit_price_clp": 7200000.0, "category": "hardware"},
            {"item_code": "HW-RELAY-GE", "name": "Relé de Protección GE Multilin (D60 / F60 / G60)", "unit_price_clp": 7000000.0, "category": "hardware"},
            {"item_code": "SRV-STUDY-DIGSILENT", "name": "Estudio de Coordinación de Protecciones & Cortocircuito DIgSILENT PowerFactory", "unit_price_clp": 4500000.0, "category": "service"}
        ]
    }

    @classmethod
    def get_normative_rule(cls, rule_id: str) -> Optional[Dict[str, Any]]:
        """Returns specific normative rule by ID."""
        r_id = rule_id.strip().upper()
        for r in cls.NORMATIVE_RULES:
            if r["rule_id"].upper() == r_id:
                return r
        return None

    @classmethod
    def search_normative_rules(
        cls,
        query: Optional[str] = None,
        standard: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Searches normative rules by keyword query or standard name."""
        results = []
        q = (query or "").lower().strip()
        std = (standard or "").lower().strip()

        for r in cls.NORMATIVE_RULES:
            match_q = not q or (q in r["title"].lower() or q in r["description"].lower() or q in r["rule_id"].lower())
            match_std = not std or (std in r["standard"].lower())
            if match_q and match_std:
                results.append(r)
        return results

    @classmethod
    def get_cen_protocol(cls, protocol_id: str) -> Optional[Dict[str, Any]]:
        """Returns specific CEN protocol by ID."""
        p_id = protocol_id.strip().upper()
        for p in cls.CEN_PROTOCOLS:
            if p["protocol_id"].upper() == p_id:
                return p
        return None

    @classmethod
    def search_cen_protocols(cls, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches CEN protocols by category."""
        if not category:
            return list(cls.CEN_PROTOCOLS)
        cat = category.strip().upper()
        return [p for p in cls.CEN_PROTOCOLS if p["category"].upper() == cat or cat in p["protocol_id"].upper()]

    @classmethod
    def get_standard_bom(cls, business_line: str) -> List[Dict[str, Any]]:
        """Returns standard BOM catalog items for a given business line."""
        b_line = (business_line or "pmu_pdc").strip().lower()
        return cls.STANDARD_BOM_CATALOG.get(b_line, cls.STANDARD_BOM_CATALOG["pmu_pdc"])

    @classmethod
    def lookup_bom_item(cls, item_code: str) -> Optional[Dict[str, Any]]:
        """Looks up a specific BOM item across all catalogs by item_code."""
        code = (item_code or "").strip().upper()
        for items in cls.STANDARD_BOM_CATALOG.values():
            for item in items:
                if item["item_code"].upper() == code:
                    return item
        return None

    @classmethod
    def export_matrix_summary(cls) -> Dict[str, Any]:
        """Returns a high-level summary of the Technical Knowledge Matrix."""
        return {
            "total_normative_rules": len(cls.NORMATIVE_RULES),
            "total_cen_protocols": len(cls.CEN_PROTOCOLS),
            "business_lines_covered": list(cls.STANDARD_BOM_CATALOG.keys()),
            "total_bom_items": sum(len(items) for items in cls.STANDARD_BOM_CATALOG.values())
        }

