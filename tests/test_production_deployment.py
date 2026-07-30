"""
Production Deployment & Real-Time Webhooks Integration Test Suite.
Verifies production Webhooks (Email RFP, WhatsApp Bot) and Gunicorn WSGI configuration.
"""

import pytest
import json
from supervisor_ui.app import create_app

@pytest.fixture
def test_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_webhook_rfp_email(test_client):
    """Verifies real-time ingestion of RFP emails via Webhook."""
    payload = {
        "sender": "licitaciones@chilquinta.cl",
        "subject": "Licitación Pública PMU Subestación Quilpué",
        "body": "Se solicita cotización para 4 unidades PMU Vizimax SynchroTeq Plus y concentrador PDC local según bases técnicas."
    }
    response = test_client.post("/api/v1/webhook/rfp-email", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["modality"] == "licitacion"
    assert "draft_id" in data

def test_webhook_whatsapp_bot(test_client):
    """Verifies instant quote generation via WhatsApp / Telegram Bot Webhook."""
    payload = {
        "phone": "+56912345678",
        "text": "Necesito cotización rápida para 2 PMUs en subestación Colbún"
    }
    response = test_client.post("/api/v1/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "Bot Comercial Inteligente" in data["reply"]
    assert "draft_id" in data
