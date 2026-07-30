"""
Pytest Fixtures for odoo_ecosystem and rag_memory Test Suites.
Provides MockOdooServer instances, multi-protocol OdooClient fixtures, sample seed payloads,
and RAG Memory dataset fixtures (tenders, historical proposals, pricing matrices, temp vector store).
"""

import pytest
import os
import tempfile
from odoo_ecosystem.mock_server import MockOdooServer, OdooVersion, FaultInjectionConfig
from odoo_ecosystem.client import OdooClient, OdooConfig
from odoo_ecosystem.audit import AuditLogger


# ==========================================
# Milestone 1: Odoo Ecosystem Fixtures
# ==========================================

@pytest.fixture
def mock_odoo_server():
    """Provides a fresh MockOdooServer instance pre-seeded with 9 model records."""
    return MockOdooServer(version=OdooVersion.V16)


@pytest.fixture
def audit_logger():
    """Provides an isolated AuditLogger using a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "test_audit.jsonl")
        logger_inst = AuditLogger(log_file_path=log_file)
        yield logger_inst


@pytest.fixture
def odoo_client_xmlrpc(mock_odoo_server, audit_logger):
    """OdooClient configured for XML-RPC using mock server."""
    cfg = OdooConfig(protocol="xmlrpc", max_retries=3, rate_limit_rps=100.0)
    return OdooClient(config=cfg, audit_logger=audit_logger, mock_server=mock_odoo_server)


@pytest.fixture
def odoo_client_jsonrpc(mock_odoo_server, audit_logger):
    """OdooClient configured for JSON-RPC using mock server."""
    cfg = OdooConfig(protocol="jsonrpc", max_retries=3, rate_limit_rps=100.0)
    return OdooClient(config=cfg, audit_logger=audit_logger, mock_server=mock_odoo_server)


@pytest.fixture
def odoo_client_rest(mock_odoo_server, audit_logger):
    """OdooClient configured for REST using mock server."""
    cfg = OdooConfig(protocol="rest", max_retries=3, rate_limit_rps=100.0)
    return OdooClient(config=cfg, audit_logger=audit_logger, mock_server=mock_odoo_server)


@pytest.fixture(params=["xmlrpc", "jsonrpc", "rest"])
def odoo_client_param(request, mock_odoo_server, audit_logger):
    """Parametrized fixture yielding OdooClient for xmlrpc, jsonrpc, and rest."""
    cfg = OdooConfig(protocol=request.param, max_retries=3, rate_limit_rps=100.0)
    return OdooClient(config=cfg, audit_logger=audit_logger, mock_server=mock_odoo_server)


@pytest.fixture
def seed_payloads():
    """Sample valid payloads for all 9 primary Odoo models."""
    return {
        "res.partner": {
            "name": "Generadora Solar del Norte SpA",
            "is_company": True,
            "email": "contacto@solarnorte.cl",
            "vat": "76111222-3",
            "credit_limit": 2500000.0
        },
        "crm.lead": {
            "name": "Estudio Integración PMGD Solar",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "expected_revenue": 45000.0,
            "probability": 75.0,
            "type": "opportunity"
        },
        "sale.order": {
            "name": "SO003",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "amount_untaxed": 45000.0,
            "amount_tax": 8550.0,
            "amount_total": 53550.0,
            "state": "draft"
        },
        "sale.order.line": {
            "product_id": [5, "Servicio Estudio EDAC"],
            "name": "Análisis de coordinación de protecciones",
            "product_uom_qty": 1.0,
            "price_unit": 45000.0
        },
        "project.project": {
            "name": "Proyecto Coordinación EDAC/ERAG",
            "partner_id": [2, "Transelec S.A."],
            "privacy_visibility": "employees"
        },
        "project.task": {
            "name": "Simulación Cortocircuito DIgSILENT",
            "project_id": [200, "Proyecto Digitalización COMASA"],
            "planned_hours": 20.0,
            "kanban_state": "normal"
        },
        "account.analytic.account": {
            "name": "CC-SOLAR-003",
            "code": "CC003",
            "partner_id": [1, "Empresa Electrica COMASA S.A."]
        },
        "crossovered.budget": {
            "name": "Presupuesto Q3 2026",
            "date_from": "2026-07-01",
            "date_to": "2026-09-30",
            "state": "draft"
        },
        "crossovered.budget.lines": {
            "analytic_account_id": [300, "CC-COMASA-001"],
            "date_from": "2026-07-01",
            "date_to": "2026-09-30",
            "planned_amount": 100000.0
        },
        "account.move": {
            "name": "INV/2026/0002",
            "move_type": "out_invoice",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "invoice_date": "2026-07-28",
            "state": "draft",
            "amount_total": 53550.0
        },
        "account.move.line": {
            "name": "Honorarios Estudio Técnico",
            "quantity": 1.0,
            "price_unit": 45000.0
        },
        "account.payment": {
            "name": "PAY/2026/0003",
            "payment_type": "inbound",
            "partner_id": [1, "Empresa Electrica COMASA S.A."],
            "amount": 53550.0,
            "date": "2026-07-28",
            "state": "draft"
        }
    }


# ==========================================
# Milestone 2: RAG & Historical Memory Fixtures
# ==========================================

@pytest.fixture
def sample_tenders_dataset():
    """Provides realistic Chilean electrical domain tender specifications."""
    return [
        {
            "doc_id": "TENDER-2025-001",
            "title": "Licitación Estudio de Coordinación de Protecciones EDAC/ERAG Subestación Ancoa",
            "category": "tender",
            "client": "Transelec S.A.",
            "date": "2025-10-15",
            "domain": "edac_erag",
            "tags": ["edac", "erag", "protecciones", "di gsilent"],
            "raw_content": (
                "Requerimientos Términos de Referencia Licitación TDR-2025-001:\n"
                "Se solicita consultoría especializada para realizar el estudio de coordinación de protecciones "
                "y ajuste de esquemas EDAC (Esquema Desconexión Automática de Carga) y ERAG (Esquema de Alivio "
                "de Generación) en la Subestación Ancoa 220kV. Requisitos obligatorios: Simulación en DIgSILENT "
                "PowerFactory v2023, auditoría ante el Coordinador Eléctrico Nacional (CEN), verificación de "
                "tiempos de despeje de fallas y emisión de informe técnico certificado por SEC."
            )
        },
        {
            "doc_id": "TENDER-2025-002",
            "title": "Licitación Integración y Telemetría SITR PMGD Solar El Monte",
            "category": "tender",
            "client": "Empresa Electrica COMASA S.A.",
            "date": "2025-11-01",
            "domain": "pmgd_sitr",
            "tags": ["pmgd", "sitr", "telemetria", "cen"],
            "raw_content": (
                "Bases de Licitación PMGD Solar El Monte 9MW:\n"
                "Implementación de sistema de medición y telemetría en tiempo real (SITR) según normativa "
                "AT-SITR-1 del CEN. Incluye instalación de reconectador en punto de conexión a media tensión (13.8kV), "
                "remota DNP3.0 sobre enlace GPRS redundante, integración con SCADA central y pruebas "
                "de comunicación de punta a punta con el Coordinador Eléctrico Nacional."
            )
        },
        {
            "doc_id": "TENDER-2026-001",
            "title": "Licitación Digitalización de Tableros y Telemedición Subestación Polpaico",
            "category": "tender",
            "client": "Enel Distribución Chile S.A.",
            "date": "2026-01-20",
            "domain": "digitalizacion_scada",
            "tags": ["scada", "telemedicion", "tableros", "iec61850"],
            "raw_content": (
                "Términos Técnicos Digitalización Polpaico:\n"
                "Suministro, montaje y configuración de tableros de control y protección con protocolo IEC 61850. "
                "Integración a Odoo ERP módulo de proyectos y activos para mantenimiento predictivo. Pruebas de "
                "interoperabilidad de relés de protección Siemens SIPROTEC y SEL-751."
            )
        },
        {
            "doc_id": "TENDER-2026-002",
            "title": "Licitación Mantenimiento Preventivo y Calibración de Relés Subestaciones CGE",
            "category": "tender",
            "client": "CGE Distribución S.A.",
            "date": "2026-02-10",
            "domain": "mantenimiento_reles",
            "tags": ["mantenimiento", "reles", "calibracion", "sec"],
            "raw_content": (
                "Bases Mantenimiento Subestaciones CGE Zona Sur:\n"
                "Servicio de inyección de corriente secundaria, prueba de curvas de tiempo-corriente (50/51, 50N/51N), "
                "verificación de transformadores de medida (TC/TP) y certificación de protocolos de prueba ante la SEC."
            )
        }
    ]


@pytest.fixture
def historical_proposals_dataset():
    """Provides historical won and lost proposals with pricing & winning strategy metadata."""
    return [
        {
            "doc_id": "PROP-2024-WON-01",
            "title": "Propuesta Técnica y Económica Estudio EDAC/ERAG Transelec S.A.",
            "category": "proposal",
            "outcome": "won",
            "price": 45000000.0,
            "client": "Transelec S.A.",
            "date": "2024-05-10",
            "domain": "edac_erag",
            "tags": ["edac", "erag", "digsilent", "propuesta_ganada"],
            "raw_content": (
                "Propuesta Adjudicada PROP-2024-WON-01:\n"
                "Se propone estudio integral de estabilidad transitoria y ajuste de relés EDAC/ERAG "
                "para la Subestación Ancoa. Metodología basada en simulación DIgSILENT PowerFactory con "
                "modelación de cortocircuito trifásico y monofásico a tierra. Factor clave de adjudicación: "
                "Inclusión de soporte directo durante el proceso de auditoría y aprobación ante la DTR del CEN, "
                "junto con entrega de archivos .pfd listos para ejecución."
            )
        },
        {
            "doc_id": "PROP-2024-WON-02",
            "title": "Propuesta Habilitación Telemetría SITR PMGD Solar del Norte",
            "category": "proposal",
            "outcome": "won",
            "price": 18500000.0,
            "client": "Generadora Solar del Norte SpA",
            "date": "2024-08-22",
            "domain": "pmgd_sitr",
            "tags": ["pmgd", "sitr", "dnp3", "propuesta_ganada"],
            "raw_content": (
                "Propuesta Adjudicada PROP-2024-WON-02:\n"
                "Solución llave en mano de telemetría SITR para PMGD 3MW. Incluye medidor de respaldo clase 0.2S, "
                "RTU de campo con soporte DNP3.0 sobre TCP/IP y módem router industrial con VPN IPsec hacia el CEN. "
                "Ventaja competitiva: Tiempo de ejecución garantizado en 15 días hábiles con aprobación previa de "
                "diagramas unilineales por la SEC."
            )
        },
        {
            "doc_id": "PROP-2024-LOST-01",
            "title": "Propuesta Estudio Cortocircuito y Coordinación Parque Eólico Biobío",
            "category": "proposal",
            "outcome": "lost",
            "price": 68000000.0,
            "client": "Colbún S.A.",
            "date": "2024-03-15",
            "domain": "edac_erag",
            "tags": ["cortocircuito", "propuesta_perdida"],
            "raw_content": (
                "Propuesta Rechazada PROP-2024-LOST-01:\n"
                "Estudio de flujo de potencia y cortocircuito en Parque Eólico 50MW. Motivo de rechazo: "
                "Precio un 25% por encima del presupuesto referencial del cliente ($50.000.000 CLP) y plazo "
                "de entrega excesivo (60 días vs 30 días solicitados)."
            )
        },
        {
            "doc_id": "PROP-2025-WON-03",
            "title": "Propuesta Digitalización Tableros IEC 61850 Subestación San Bernardo",
            "category": "proposal",
            "outcome": "won",
            "price": 32000000.0,
            "client": "Enel Distribución Chile S.A.",
            "date": "2025-02-14",
            "domain": "digitalizacion_scada",
            "tags": ["iec61850", "scada", "propuesta_ganada"],
            "raw_content": (
                "Propuesta Adjudicada PROP-2025-WON-03:\n"
                "Digitalización de 8 paños de distribución en IEC 61850 GOOSE/MMS. Factor decisivo: "
                "Integración nativa de conectores con Odoo ERP para trazabilidad de repuestos y módulos de "
                "mantenimiento de activos."
            )
        },
        {
            "doc_id": "PROP-2025-LOST-02",
            "title": "Propuesta Telemedición y SCADA Subestación Quillota",
            "category": "proposal",
            "outcome": "lost",
            "price": 28000000.0,
            "client": "Empresa Electrica COMASA S.A.",
            "date": "2025-06-01",
            "domain": "pmgd_sitr",
            "tags": ["scada", "propuesta_perdida"],
            "raw_content": (
                "Propuesta Rechazada PROP-2025-LOST-02:\n"
                "Suministro de Gateway SCADA. Motivo de rechazo: Falta de acreditación en norma ISO 27001 "
                "para ciberseguridad en redes OT exigida en las bases administrativas."
            )
        },
        {
            "doc_id": "PROP-2026-PEND-01",
            "title": "Propuesta Auditoría Cumplimiento Normativo CEN 2026",
            "category": "proposal",
            "outcome": "pending",
            "price": 22000000.0,
            "client": "Transelec S.A.",
            "date": "2026-01-10",
            "domain": "auditoria_cen",
            "tags": ["auditoria", "cen", "propuesta_pendiente"],
            "raw_content": (
                "Propuesta en Evaluación PROP-2026-PEND-01:\n"
                "Servicio de auditoría preventiva de cumplimiento normativo técnico para instalaciones de transmisión."
            )
        }
    ]


@pytest.fixture
def pricing_matrices_dataset():
    """Provides CSV string payloads representing historical cost benchmarks & pricing matrices."""
    return """item,descripcion,categoria,precio_unitario,unidad,dominio
ITEM-001,Estudio de Coordinación de Protecciones EDAC/ERAG,cost_structure,45000000,CLP,edac_erag
ITEM-002,Simulación Cortocircuito DIgSILENT por Subestación,cost_structure,10000000,CLP,edac_erag
ITEM-003,Habilitación Enlace SITR Telemetría CEN PMGD,price_list,18500000,CLP,pmgd_sitr
ITEM-004,Ingeniero Senior Electricista UF/Hora,cost_structure,2.5,UF,general
ITEM-005,Ingeniero Especialista SCADA UF/Hora,cost_structure,2.8,UF,digitalizacion_scada
ITEM-006,Prueba de Inyección Secundaria Relé de Protección,price_list,750000,CLP,mantenimiento_reles
ITEM-007,Certificación de Informe Técnico ante SEC,price_list,1500000,CLP,general
"""


@pytest.fixture
def temp_rag_store(tmp_path):
    """Provides an isolated JSON storage path in pytest temp directory."""
    store_file = tmp_path / "rag_store_test.json"
    return str(store_file)


@pytest.fixture
def historical_memory_instance(temp_rag_store, sample_tenders_dataset, historical_proposals_dataset, pricing_matrices_dataset):
    """Provides a HistoricalMemory instance populated with sample dataset fixtures."""
    from rag_memory.few_shot import HistoricalMemory
    
    memory = HistoricalMemory(storage_path=temp_rag_store)
    
    # Ingest tenders
    for t in sample_tenders_dataset:
        memory.ingest_document(doc_type=t["category"], content=t)
        
    # Ingest proposals
    for p in historical_proposals_dataset:
        memory.ingest_document(doc_type=p["category"], content=p)
        
    # Ingest CSV pricing matrix
    csv_docs = memory.ingester.ingest_csv(pricing_matrices_dataset, category="cost_structure")
    for doc in csv_docs:
        memory.vector_store.add_document(doc)
    
    return memory
