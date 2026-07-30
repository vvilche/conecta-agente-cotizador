# Web Console Interface & REST API Endpoints Specification

## Executive Summary
This document specifies the Web Console Interface & REST API Architecture for Milestone 4 (Supervisor Human-in-the-Loop Web Console). 
The solution provides a lightweight, dependency-free Python HTTP / WSGI Web Application (`src/supervisor_ui/app.py`) and a responsive single-page dashboard (`src/supervisor_ui/templates/index.html`) enforcing **0% auto-execution compliance** for all AI-generated operations.

---

## 1. System Architecture & Component Interactions

```
+-----------------------------------------------------------------------------------+
|                            Supervisor Web Dashboard                               |
|                  (Single-Page HTML5 / Vanilla JS / CSS Grid)                      |
+-----------------------------------------------------------------------------------+
       |                    |                                |
       | GET /api/drafts    | POST /api/drafts/<id>/approve  | GET /api/audit-logs
       v                    v                                v
+-----------------------------------------------------------------------------------+
|                        REST API App (`src/supervisor_ui/app.py`)                  |
|                 (Standard Library http.server / WSGI Router Engine)               |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
|                    Supervisor Engine (`src/supervisor_ui/console.py`)             |
+-----------------------------------------------------------------------------------+
       |                                    |                              |
       v                                    v                              v
+-----------------------+   +-------------------------------+   +-------------------+
| DraftStager / Store   |   | OdooClient.commit_draft(...)  |   | Supervisor        |
| (Staged DraftActions) |   | (Odoo ERP Database Mutation)  |   | AuditLogger       |
+-----------------------+   +-------------------------------+   +-------------------+
```

---

## 2. REST API Specification (`src/supervisor_ui/app.py`)

### 2.1 Route Overview
All endpoints return standard `application/json` responses with consistent status codes (`200 OK`, `400 Bad Request`, `404 Not Found`, `409 Conflict`, `500 Internal Server Error`).

| HTTP Method | Route Endpoint | Purpose | Query / Body Parameters | Success Status |
|-------------|----------------|---------|-------------------------|----------------|
| `GET` | `/api/drafts` | List staged draft actions with multi-field filtering | Query: `agent`, `min_confidence`, `start_date`, `end_date`, `status` | `200 OK` |
| `GET` | `/api/drafts/<draft_id>` | Detail view of draft, proposed payload, RAG rationale, risk score, and current Odoo state | URL param: `draft_id` | `200 OK` / `404 Not Found` |
| `POST` | `/api/drafts/<draft_id>/approve` | Execute supervisor VoBo approval signature | Body: `{"supervisor_id": str, "justification": str}` | `200 OK` / `400 Bad Request` / `404 Not Found` / `409 Conflict` |
| `POST` | `/api/drafts/<draft_id>/reject` | Execute supervisor rejection signature | Body: `{"supervisor_id": str, "reason": str}` | `200 OK` / `400 Bad Request` / `404 Not Found` |
| `GET` | `/api/audit-logs` | Fetch historical supervisor VoBo decisions and created Odoo records | Query: `supervisor_id`, `action`, `limit` | `200 OK` |
| `GET` | `/` | Serve single-page supervisor web console interface | None | `200 OK` |

---

### 2.2 Route Detailed Contracts

#### Endpoint 1: `GET /api/drafts`
- **Description**: Retrieves pending and historical draft actions, filtered by query criteria.
- **Query Parameters**:
  - `agent` (optional str): Filter by agent identifier (e.g. `rfq_prospeccion`, `cotizacion_inventario`).
  - `min_confidence` (optional float): Filter drafts with `confidence_score >= min_confidence`.
  - `start_date` (optional ISO str): Created on or after timestamp.
  - `end_date` (optional ISO str): Created on or before timestamp.
  - `status` (optional str, default `"pending_vobo"`): Filter status (`pending_vobo`, `approved`, `rejected`, `committed`, `all`).
- **Response Format (`200 OK`)**:
```json
{
  "total": 2,
  "status_filter": "pending_vobo",
  "drafts": [
    {
      "draft_id": "draft_a1b2c3d4e5f6",
      "agent_name": "rfq_prospeccion",
      "target_model": "crm.lead",
      "action_type": "create",
      "proposed_payload": {
        "name": "Estudio Integración PMGD Solar Ancoa",
        "expected_revenue": 45000000.0,
        "probability": 85.0
      },
      "justification": "Propuesta basada en caso histórico TENDER-2025-001 con 85% probabilidad.",
      "confidence_score": 0.92,
      "status": "pending_vobo",
      "created_at": "2026-07-28T12:00:00Z",
      "audit_trail": [
        {
          "timestamp": "2026-07-28T12:00:00Z",
          "action": "draft_created",
          "agent_name": "rfq_prospeccion"
        }
      ],
      "metadata": {
        "risk_level": "LOW"
      }
    }
  ]
}
```

---

#### Endpoint 2: `GET /api/drafts/<draft_id>`
- **Description**: Fetches detailed view of a specific draft, including comparison with existing Odoo DB state if applicable.
- **URL Parameter**: `draft_id` (str).
- **Response Format (`200 OK`)**:
```json
{
  "draft_id": "draft_a1b2c3d4e5f6",
  "agent_name": "rfq_prospeccion",
  "target_model": "crm.lead",
  "action_type": "create",
  "proposed_payload": {
    "name": "Estudio Integración PMGD Solar Ancoa",
    "partner_id": [1, "Empresa Electrica COMASA S.A."],
    "expected_revenue": 45000000.0,
    "probability": 85.0
  },
  "justification": "Basado en licitaciones pasadas Ancoa 220kV.",
  "confidence_score": 0.92,
  "status": "pending_vobo",
  "created_at": "2026-07-28T12:00:00Z",
  "risk_assessment": {
    "score": "LOW",
    "reason": "Target model crm.lead with confidence score 0.92 exceeds 0.85 safety threshold."
  },
  "current_odoo_state": null,
  "diff": {
    "type": "NEW_RECORD",
    "changes": [
      {"field": "name", "old_value": null, "new_value": "Estudio Integración PMGD Solar Ancoa"},
      {"field": "expected_revenue", "old_value": null, "new_value": 45000000.0}
    ]
  }
}
```
- **Error Response (`404 Not Found`)**:
```json
{
  "error": "Draft 'draft_nonexistent' not found in staged queue",
  "status_code": 404
}
```

---

#### Endpoint 3: `POST /api/drafts/<draft_id>/approve`
- **Description**: Submits supervisor VoBo approval signature. Invokes `OdooClient.commit_draft`, mutates Odoo DB, updates status to `"approved"` / `"committed"`, and records audit trail.
- **Request Body**:
```json
{
  "supervisor_id": "supervisor_admin_01",
  "justification": "Verificado presupuesto y especificaciones técnicas ante CEN."
}
```
- **Response Format (`200 OK`)**:
```json
{
  "success": true,
  "draft_id": "draft_a1b2c3d4e5f6",
  "status": "approved",
  "approved_by": "supervisor_admin_01",
  "odoo_record_id": 104,
  "committed_at": "2026-07-28T12:38:22Z",
  "message": "Draft successfully approved and committed to Odoo model 'crm.lead' with ID 104."
}
```
- **Error Response (`400 Bad Request`)**:
```json
{
  "error": "Field 'supervisor_id' is required for VoBo approval",
  "status_code": 400
}
```
- **Error Response (`409 Conflict`)**:
```json
{
  "error": "Draft 'draft_a1b2c3d4e5f6' has already been approved/committed.",
  "status_code": 409
}
```

---

#### Endpoint 4: `POST /api/drafts/<draft_id>/reject`
- **Description**: Submits supervisor rejection. Cancels draft execution, prevents Odoo DB mutation, updates status to `"rejected"`, and records audit trail.
- **Request Body**:
```json
{
  "supervisor_id": "supervisor_admin_01",
  "reason": "Monto excede el presupuesto autorizado por la gerencia de operaciones."
}
```
- **Response Format (`200 OK`)**:
```json
{
  "success": true,
  "draft_id": "draft_a1b2c3d4e5f6",
  "status": "rejected",
  "rejected_by": "supervisor_admin_01",
  "reason": "Monto excede el presupuesto autorizado por la gerencia de operaciones.",
  "timestamp": "2026-07-28T12:38:22Z",
  "message": "Draft successfully rejected. No execution occurred in Odoo ERP."
}
```
- **Error Response (`400 Bad Request`)**:
```json
{
  "error": "Field 'reason' is required for draft rejection",
  "status_code": 400
}
```

---

#### Endpoint 5: `GET /api/audit-logs`
- **Description**: Retrieves structured audit log history of supervisor VoBo decisions and resulting Odoo records.
- **Query Parameters**:
  - `supervisor_id` (optional str): Filter by supervisor identifier.
  - `action` (optional str): Filter by action (`approve`, `reject`, `commit`).
  - `limit` (optional int, default `50`): Maximum entries to return.
- **Response Format (`200 OK`)**:
```json
{
  "total": 1,
  "audit_logs": [
    {
      "log_id": "audit_991823",
      "draft_id": "draft_a1b2c3d4e5f6",
      "supervisor_id": "supervisor_admin_01",
      "verdict": "APPROVED",
      "timestamp": "2026-07-28T12:38:22Z",
      "odoo_model": "crm.lead",
      "odoo_record_id": 104,
      "justification": "Verificado presupuesto y especificaciones técnicas ante CEN."
    }
  ]
}
```

---

## 3. Web Interface Design Specification (`src/supervisor_ui/templates/index.html`)

### 3.1 UX/UI Layout & Components
The interface is a single-page web console styled with a modern dark theme inspired by industrial control systems (dark slate background `#0f172a`, card containers `#1e293b`, blue/indigo action accents `#3b82f6`, emerald approval buttons `#10b981`, rose rejection buttons `#ef4444`).

```
+------------------------------------------------------------------------------------+
|  [LOGO] Odoo Agentic Swarm -- Supervisor HITL Web Console       [Status: HEALTHY]  |
+------------------------------------------------------------------------------------+
|  FILTERS:                                                                          |
|  Agent: [ All Agents v ]  Min Confidence: [ 0.80 ]  Status: [ Pending VoBo v ]    |
|  Search: [ Enter keyword...                          ]  [ Refresh Queue ]          |
+------------------------------------------------------------------------------------+
| PENDING DRAFTS QUEUE (Count: 3)                                                    |
+---------------+-------------------+---------------+------------+-------+-----------+
| Draft ID      | Agent             | Target Model  | Conf Score | Status| Actions   |
+---------------+-------------------+---------------+------------+-------+-----------+
| draft_a1b2c3  | rfq_prospeccion   | crm.lead      | 92% (High) | PEND  | [View/VoBo]|
| draft_f8e7d6  | cotizacion_inv    | sale.order    | 78% (Med)  | PEND  | [View/VoBo]|
| draft_1a2b3c  | conciliador_cont  | account.move  | 95% (High) | PEND  | [View/VoBo]|
+---------------+-------------------+---------------+------------+-------+-----------+
|                                                                                    |
| [ TAB: Pending Drafts Queue ]      [ TAB: Historical Audit Logs ]                  |
+------------------------------------------------------------------------------------+
```

### 3.2 Modal Detail Viewer (Diff & VoBo Action Panel)
When the supervisor clicks `[View / VoBo]`, a modal dialog appears showing:
1. **Header**: Draft ID, Agent Name, Target Model, Confidence Score badge.
2. **Justification & Few-Shot RAG Rationale**: Complete explanation provided by the specialized AI agent.
3. **Side-by-Side Payload Comparison**:
   - Proposed Values (JSON formatted or key-value table).
   - Current Odoo Database State (or "New Record Creation").
4. **Interactive Action Form**:
   - **Supervisor ID**: Text input pre-filled with logged-in user or "supervisor_admin".
   - **VoBo Justification / Notes**: Text area for approval context.
   - **Rejection Reason**: Text area required if rejecting.
   - **Footer Action Buttons**:
     - `[ Approve & Commit to Odoo ]` (Emerald Green)
     - `[ Reject Draft ]` (Rose Red)
     - `[ Close ]` (Gray Outline)

---

## 4. Frontend Architecture (Vanilla JavaScript Single Page App)

The HTML template embeds zero-dependency vanilla JS (`<script>`) for seamless execution without requiring build steps (npm/webpack):

```javascript
// Sample Client-Side API Execution Flow
async function loadDraftsQueue() {
  const agent = document.getElementById('agentFilter').value;
  const minConf = document.getElementById('confidenceFilter').value;
  const status = document.getElementById('statusFilter').value;
  
  const url = `/api/drafts?agent=${encodeURIComponent(agent)}&min_confidence=${minConf}&status=${status}`;
  const res = await fetch(url);
  const data = await res.json();
  renderDraftsTable(data.drafts);
}

async function approveDraft(draftId) {
  const supervisorId = document.getElementById('supervisorId').value.trim();
  const justification = document.getElementById('voboJustification').value.trim();
  
  if (!supervisorId) {
    alert("Supervisor ID is required for VoBo approval signature.");
    return;
  }
  
  const res = await fetch(`/api/drafts/${draftId}/approve`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ supervisor_id: supervisorId, justification: justification })
  });
  
  const result = await res.json();
  if (res.ok) {
    closeModal();
    loadDraftsQueue();
    loadAuditLogs();
    alert(`Draft ${draftId} committed to Odoo successfully. Record ID: ${result.odoo_record_id}`);
  } else {
    alert(`Error: ${result.error}`);
  }
}
```

---

## 5. Python Application Implementation Blueprint (`src/supervisor_ui/app.py`)

`src/supervisor_ui/app.py` exposes a clean WSGI callable (`app`) and a standalone Python `http.server` runner:

```python
"""
Supervisor Web Console Application & REST API Router Engine.
Enforces 0% auto-execution compliance and exposes VoBo approval endpoints.
"""

from typing import Dict, Any, Optional
import json
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

from supervisor_ui.console import SupervisorConsole

logger = logging.getLogger(__name__)

class SupervisorRequestHandler(BaseHTTPRequestHandler):
    """BaseHTTPRequestHandler implementation serving REST API and Web Dashboard."""
    
    console_instance: Optional[SupervisorConsole] = None

    def _send_json(self, data: Any, status_code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_content: str, status_code: int = 200):
        body = html_content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            # Serve index.html template
            template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._send_html(content)
            else:
                self._send_html("<h1>Supervisor Web Console</h1>", status_code=200)
            return

        if path == "/api/drafts":
            agent = query.get("agent", [None])[0]
            min_conf = float(query.get("min_confidence", [0.0])[0])
            status = query.get("status", ["pending_vobo"])[0]
            
            drafts = self.console_instance.get_pending_drafts(
                agent_filter=agent,
                min_confidence=min_conf,
                status_filter=status
            )
            self._send_json({"total": len(drafts), "drafts": drafts})
            return

        if path.startswith("/api/drafts/"):
            draft_id = path.split("/")[3]
            try:
                draft_detail = self.console_instance.get_draft_detail(draft_id)
                self._send_json(draft_detail)
            except KeyError:
                self._send_json({"error": f"Draft '{draft_id}' not found"}, status_code=404)
            return

        if path == "/api/audit-logs":
            limit = int(query.get("limit", [50])[0])
            logs = self.console_instance.get_audit_logs(limit=limit)
            self._send_json({"total": len(logs), "audit_logs": logs})
            return

        self._send_json({"error": "Route not found"}, status_code=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, status_code=400)
            return

        if path.endswith("/approve"):
            parts = path.split("/")
            draft_id = parts[3]
            supervisor_id = body.get("supervisor_id")
            justification = body.get("justification", "")
            
            if not supervisor_id:
                self._send_json({"error": "Field 'supervisor_id' is required"}, status_code=400)
                return

            try:
                result = self.console_instance.approve_draft(
                    draft_id=draft_id,
                    supervisor_id=supervisor_id,
                    justification=justification
                )
                self._send_json(result, status_code=200)
            except KeyError:
                self._send_json({"error": f"Draft '{draft_id}' not found"}, status_code=404)
            except ValueError as ve:
                self._send_json({"error": str(ve)}, status_code=409)
            return

        if path.endswith("/reject"):
            parts = path.split("/")
            draft_id = parts[3]
            supervisor_id = body.get("supervisor_id")
            reason = body.get("reason")

            if not supervisor_id or not reason:
                self._send_json({"error": "Fields 'supervisor_id' and 'reason' are required"}, status_code=400)
                return

            try:
                result = self.console_instance.reject_draft(
                    draft_id=draft_id,
                    supervisor_id=supervisor_id,
                    reason=reason
                )
                self._send_json(result, status_code=200)
            except KeyError:
                self._send_json({"error": f"Draft '{draft_id}' not found"}, status_code=404)
            return

        self._send_json({"error": "Route not found"}, status_code=404)
```

---

## 6. Acceptance & Verification Criteria
1. **0% Auto-execution invariant**: Staged draft items remain in `"pending_vobo"` state until explicit `POST /api/drafts/<id>/approve` call with `supervisor_id` payload.
2. **REST API Filtering**: `GET /api/drafts` accurately filters by agent name, minimum confidence threshold, and status.
3. **Odoo Mutation Validation**: Approval triggers Odoo record creation via `OdooClient.commit_draft` and returns the generated `odoo_record_id`.
4. **Audit Trail Completeness**: All approvals and rejections produce immutable audit records retrievable via `GET /api/audit-logs`.
5. **No External Network Dependencies**: Web console works cleanly in offline `CODE_ONLY` mode using standard library HTML/CSS/JS.
