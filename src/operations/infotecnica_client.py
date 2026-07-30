"""
InfoTécnica CEN Client Module for Conecta Ingeniería S.A.
Queries the public Coordinador Eléctrico Nacional (CEN) REST API for substation, generator plant,
nemotécnico metadata, and official technical documents (unilineal diagrams, IPES reports).
"""

import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api-infotecnica.coordinador.cl/v1"


class InfoTecnicaClient:
    """
    Client for querying Coordinador Eléctrico Nacional (CEN) InfoTécnica public API.
    """

    @classmethod
    def search_substations_and_plants(cls, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches InfoTécnica CEN for substations or generator plants matching query.
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip()
        try:
            url = f"{API_BASE_URL}/centrales/"
            params = {"format": "json", "search": clean_query}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning("InfoTécnica API returned status %s for search '%s'", resp.status_code, clean_query)
                return []

            data = resp.json()
            results = data if isinstance(data, list) else data.get("results", [])
            
            clean_results = []
            for item in results[:limit]:
                clean_results.append({
                    "id": item.get("id"),
                    "name": item.get("nombre", ""),
                    "nemotecnico": item.get("nemotecnico", ""),
                    "owner": item.get("propietario_nombre") or item.get("grupo_nombre") or "No especificado",
                    "comuna": item.get("comuna_nombre", ""),
                    "potencia_mw": float(item.get("potencia_maxima") or 0.0),
                    "description": item.get("descripcion", ""),
                    "cen_url": f"https://infotecnica.coordinador.cl/instalaciones/centrales/{item.get('id')}" if item.get("id") else ""
                })

            return clean_results

        except Exception as e:
            logger.error("Error querying InfoTécnica CEN API for query '%s': %s", clean_query, e)
            return []

    @classmethod
    def get_plant_documents(cls, central_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves official technical documents (SLD unifilar, datasheets, CEN oficios) for a given central ID.
        """
        if not central_id:
            return []

        try:
            url = f"{API_BASE_URL}/centrales/{central_id}/documentos/"
            resp = requests.get(url, params={"format": "json"}, timeout=10)
            if resp.status_code != 200:
                return []

            data = resp.json()
            docs = data if isinstance(data, list) else data.get("results", [])
            
            formatted_docs = []
            for doc in docs:
                doc_id = doc.get("id")
                formatted_docs.append({
                    "id": doc_id,
                    "name": doc.get("nombre") or doc.get("filename") or f"Documento_{doc_id}",
                    "filename": doc.get("filename", ""),
                    "filesize_kb": doc.get("filesize", 0),
                    "download_url": f"{API_BASE_URL}/centrales/{central_id}/documentos/{doc_id}/" if doc_id else ""
                })

            return formatted_docs

        except Exception as e:
            logger.error("Error fetching documents for central_id %s: %s", central_id, e)
            return []

    @classmethod
    def enrich_quotation_context(cls, prompt_or_substation: str) -> Dict[str, Any]:
        """
        Extracts substation / plant keywords from prompt, queries InfoTécnica CEN API,
        and returns enriched technical context.
        """
        results = cls.search_substations_and_plants(prompt_or_substation, limit=3)
        if not results:
            # Fallback search with generic tokens
            tokens = [t for t in prompt_or_substation.split() if len(t) > 3 and t.lower() not in ("cotizar", "reemplazo", "necesito", "sistema", "para", "subestacion", "subestación")]
            for tok in tokens:
                res = cls.search_substations_and_plants(tok, limit=2)
                if res:
                    results = res
                    break

        if not results:
            return {
                "found": False,
                "query": prompt_or_substation,
                "matches": [],
                "technical_note": "No se encontraron registros de la subestación en la API InfoTécnica CEN."
            }

        top_match = results[0]
        docs = cls.get_plant_documents(top_match["id"]) if top_match.get("id") else []

        return {
            "found": True,
            "query": prompt_or_substation,
            "top_match": top_match,
            "all_matches": results,
            "documents": docs,
            "technical_note": f"Información verificada en API InfoTécnica CEN: Central {top_match['name']} ({top_match['nemotecnico']}), Propietario: {top_match['owner']}, Potencia: {top_match['potencia_mw']} MW."
        }
