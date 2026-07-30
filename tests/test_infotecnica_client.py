"""
Unit tests for InfoTecnicaClient and InfoTécnica CEN endpoints in supervisor UI.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.operations.infotecnica_client import InfoTecnicaClient
from src.supervisor_ui.app import create_app


@pytest.fixture
def app_client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class TestInfoTecnicaClient:
    """Test suite for InfoTecnicaClient and CEN REST API integration."""

    @patch("requests.get")
    def test_search_substations_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {
                    "id": 2335,
                    "nombre": "PMGD PFV TOPACIO",
                    "nemotecnico": "CE02G0881",
                    "propietario_nombre": "PARQUE SOLAR ESMERALDA SPA",
                    "comuna_nombre": "Yungay",
                    "potencia_maxima": 3.0,
                    "descripcion": "NUP1234"
                }
            ]
        }
        mock_get.return_value = mock_resp

        res = InfoTecnicaClient.search_substations_and_plants("TOPACIO")
        assert len(res) == 1
        assert res[0]["id"] == 2335
        assert res[0]["name"] == "PMGD PFV TOPACIO"
        assert res[0]["nemotecnico"] == "CE02G0881"
        assert res[0]["owner"] == "PARQUE SOLAR ESMERALDA SPA"

    @patch("requests.get")
    def test_get_plant_documents(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "id": 1001,
                "nombre": "Diagrama Unifilar SE Topacio.pdf",
                "filename": "topacio_sld.pdf",
                "filesize": 1024.0
            }
        ]
        mock_get.return_value = mock_resp

        docs = InfoTecnicaClient.get_plant_documents(2335)
        assert len(docs) == 1
        assert docs[0]["id"] == 1001
        assert "download_url" in docs[0]

    def test_enrich_quotation_context_empty(self):
        context = InfoTecnicaClient.enrich_quotation_context("")
        assert context["found"] is False

    @patch("requests.get")
    def test_api_infotecnica_endpoints(self, mock_get, app_client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [{"id": 99, "nombre": "SE Mayaca", "nemotecnico": "SEMAY"}]}
        mock_get.return_value = mock_resp

        res = app_client.get("/api/infotecnica/search?q=Mayaca")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["count"] == 1
