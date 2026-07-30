"""
Supervisor Web Console REST API Application Router Engine.
Enforces 0% auto-execution compliance and exposes VoBo approval/rejection endpoints.
"""

from typing import Dict, Any, Optional
import os
import logging
from flask import Flask, jsonify, request, render_template

from supervisor_ui.console import SupervisorConsole, DraftNotFoundError, InvalidDraftStateError
from swarm_engine.base_agent import DraftAction
from src.operations import (
    DocAutomator,
    FatSatSimulator,
    KittingEngine,
    AccreditationAutomator,
    PaymentStatementAutomator,
    FinancialImpactEngine
)

logger = logging.getLogger(__name__)


def create_app(console: Optional[SupervisorConsole] = None) -> Flask:
    """
    Factory function creating the Supervisor Web Console Flask Application.
    """
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    app = Flask(__name__, template_folder=template_dir)
    
    # Store console instance on app
    app.console = console or SupervisorConsole()

    @app.route("/", methods=["GET"])
    def index():
        """Serves the executive hub main console interface."""
        try:
            return render_template("index.html")
        except Exception as e:
            logger.warning("Template rendering failed: %s", e)
            return "<h1>Odoo Agentic Swarm - Hub Principal</h1>", 200

    @app.route("/comercial", methods=["GET"])
    def portal_comercial():
        """Serves the dedicated Commercial Portal for estimators and proposals engineers."""
        try:
            return render_template("comercial.html")
        except Exception as e:
            logger.warning("Commercial template rendering failed: %s", e)
            return "<h1>Portal Comercial Conecta S.A.</h1>", 200

    @app.route("/operaciones", methods=["GET"])
    def portal_operaciones():
        """Serves the dedicated Operations Portal for project engineers and field managers."""
        try:
            return render_template("operaciones.html")
        except Exception as e:
            logger.warning("Operations template rendering failed: %s", e)
            return "<h1>Portal de Operaciones Conecta S.A.</h1>", 200

    @app.route("/api/documents/download", methods=["GET"])
    def download_document():
        """Generates and serves downloadable commercial and project documentation."""
        draft_id = request.args.get("draft_id", "draft_demo")
        doc_type = request.args.get("doc_type", "propuesta_comercial")

        try:
            draft = app.console.get_draft_detail(draft_id)
            payload = draft.proposed_payload
        except Exception:
            payload = {
                "partner_id": "Cliente Coordinado Conecta",
                "amount_untaxed": 58628319.0,
                "amount_tax": 11139381.0,
                "amount_total": 69767700.0,
                "order_line": [
                    {"item_code": "HW-RTU-SUBSTATION", "name": "Remota RTU NovaTech Orion LX+", "product_uom_qty": 1, "price_unit": 21681416, "price_subtotal": 21681416},
                    {"item_code": "HW-SWITCH-IND", "name": "Switch Belden Hirschmann RS20", "product_uom_qty": 1, "price_unit": 5088496, "price_subtotal": 5088496}
                ]
            }

        client_name = payload.get("partner_id", "Cliente")
        lines = payload.get("order_line", [])

        if doc_type == "bom_xlsx":
            content = f"# LISTA DE MATERIALES (BOM) - CLIENTE: {client_name}\n\n"
            content += "Código\tDescripción\tCantidad\tPrecio Unitario CLP\tSubtotal CLP\n"
            for item in lines:
                content += f"{item.get('item_code')}\t{item.get('name')}\t{item.get('product_uom_qty')}\t{item.get('price_unit')}\t{item.get('price_subtotal')}\n"
            mimetype = "text/plain"
            filename = f"BOM_{client_name.replace(' ', '_')}.txt"
        elif doc_type == "especificacion_tecnica":
            content = f"# ESPECIFICACIÓN TÉCNICA DE ARQUITECTURA - {client_name}\n\n"
            content += "Estándar de Equipamiento: Belden Hirschmann RS20/RS30, NovaTech Orion LX+, VIZIMAX SynchroTeq Plus.\n"
            content += f"Monto Neto Propuesto: ${payload.get('amount_untaxed', 0):,.0f} CLP.\n"
            mimetype = "text/markdown"
            filename = f"Especificacion_Tecnica_{client_name.replace(' ', '_')}.md"
        elif doc_type == "anexos_licitacion":
            content = f"# FORMULARIOS ANEXOS DE LICITACIÓN - {client_name}\n\n"
            content += "ANEXO A: Oferta Económica Neto: $" + f"{payload.get('amount_untaxed', 0):,.0f} CLP.\n"
            content += "ANEXO B: Formulario de Lista de Equipamiento BOM.\n"
            content += "ANEXO C: Certificación de Cumplimiento Normativo CEN/SEC.\n"
            mimetype = "text/markdown"
            filename = f"Anexos_Licitacion_{client_name.replace(' ', '_')}.md"
        else:
            content = f"# PROPUESTA COMERCIAL OFICIAL - CONECTA INGENIERÍA S.A.\n\n"
            content += f"**Cliente**: {client_name}\n"
            content += f"**Monto Neto**: ${payload.get('amount_untaxed', 0):,.0f} CLP\n"
            content += f"**IVA (19%)**: ${payload.get('amount_tax', 0):,.0f} CLP\n"
            content += f"**Total Bruto**: ${payload.get('amount_total', 0):,.0f} CLP\n\n"
            content += "## Desglose de Partidas:\n"
            for item in lines:
                content += f"- [{item.get('item_code')}] {item.get('name')} x{item.get('product_uom_qty')}: ${item.get('price_subtotal'):,.0f} CLP\n"
            mimetype = "text/markdown"
            filename = f"Propuesta_Comercial_{client_name.replace(' ', '_')}.md"

        from flask import Response
        return Response(
            content,
            mimetype=mimetype,
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    @app.route("/api/drafts", methods=["GET"])
    def get_drafts():
        """Lists staged draft actions filtered by agent, confidence threshold, and status."""
        agent = request.args.get("agent") or request.args.get("agent_filter")
        min_conf_str = request.args.get("min_confidence", "0.0")
        try:
            min_conf = float(min_conf_str)
        except ValueError:
            min_conf = 0.0
            
        status = request.args.get("status") or request.args.get("status_filter") or "pending_vobo"

        drafts = app.console.get_pending_drafts(
            agent_filter=agent,
            min_confidence=min_conf,
            status_filter=status
        )
        
        drafts_dict_list = [d.model_dump() for d in drafts]
        return jsonify({
            "success": True,
            "count": len(drafts_dict_list),
            "total": len(drafts_dict_list),
            "status_filter": status,
            "drafts": drafts_dict_list
        }), 200

    @app.route("/api/guided-questions", methods=["POST"])
    def get_guided_questions():
        """Returns business line classification and interactive guided questions for prompt."""
        body = request.get_json(silent=True) or {}
        prompt = body.get("prompt") or body.get("query") or "PMUS"

        from rag_memory.business_lines import BusinessLineClassifier, BusinessLineType, STANDARD_BOM_TEMPLATES
        b_type = BusinessLineClassifier.classify(prompt)
        template = STANDARD_BOM_TEMPLATES.get(b_type, STANDARD_BOM_TEMPLATES[BusinessLineType.PMU_PDC])

        return jsonify({
            "success": True,
            "business_line": b_type.value,
            "template_name": template.name,
            "description": template.description,
            "guided_questions": template.guided_questions,
            "default_items": [i.model_dump() for i in template.items]
        }), 200

    @app.route("/api/request-quote", methods=["POST"])
    def request_quote():
        """Generates a guided quotation draft using AgentSwarm and stores it in the staged queue."""
        body = request.get_json(silent=True) or {}
        prompt = body.get("prompt") or body.get("query") or "Generame una cotización para PMUS"
        client = body.get("client") or "Cliente Coordinado 2026"
        num_pmus = float(body.get("num_pmus", 1.0))
        modality = body.get("modality", "compra_directa")
        include_pdc = body.get("include_pdc", True)
        include_gps = body.get("include_gps", True)
        include_cen = body.get("include_cen", True)

        try:
            from swarm_engine.swarm import AgentSwarm
            from rag_memory.few_shot import HistoricalMemory

            memory = HistoricalMemory("rag_store_2026.json")
            swarm = AgentSwarm(memory=memory)

            draft = swarm.process_task("cotizacion_inventario", {
                "prompt": prompt,
                "client": client,
                "num_pmus": num_pmus,
                "modality": modality,
                "include_pdc": include_pdc,
                "include_gps": include_gps,
                "include_cen": include_cen
            })

            app.console.register_draft(draft)

            return jsonify({
                "success": True,
                "message": f"Borrador de cotización '{draft.draft_id}' generado exitosamente.",
                "draft": draft.model_dump()
            }), 201

        except Exception as e:
            logger.error("Error generating quote: %s", e, exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500




    @app.route("/api/drafts/<draft_id>", methods=["GET"])
    def get_draft_detail(draft_id: str):
        """Returns detail view of a specific staged draft action."""
        try:
            detail = app.console.get_draft_detail(draft_id)
            return jsonify({
                "success": True,
                "draft": detail,
                **detail
            }), 200
        except DraftNotFoundError as e:
            return jsonify({"success": False, "error": str(e)}), 404
        except KeyError as e:
            return jsonify({"success": False, "error": f"Draft '{draft_id}' not found"}), 404

    @app.route("/api/drafts/<draft_id>/approve", methods=["POST"])
    def approve_draft(draft_id: str):
        """Executes supervisor VoBo approval signature."""
        data = request.get_json(silent=True) or {}
        supervisor_id = data.get("supervisor_id", "").strip()
        justification = data.get("justification", "")

        if not supervisor_id:
            return jsonify({"success": False, "error": "Field 'supervisor_id' is required"}), 400

        try:
            res = app.console.approve_draft(
                draft_id=draft_id,
                supervisor_id=supervisor_id,
                justification=justification
            )
            return jsonify({
                "success": True,
                "message": f"Draft successfully approved and committed to Odoo model '{res['target_model']}'.",
                **res
            }), 200
        except DraftNotFoundError as e:
            return jsonify({"success": False, "error": str(e)}), 404
        except KeyError as e:
            return jsonify({"success": False, "error": f"Draft '{draft_id}' not found"}), 404
        except ValueError as ve:
            return jsonify({"success": False, "error": str(ve)}), 400
        except InvalidDraftStateError as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/drafts/<draft_id>/reject", methods=["POST"])
    def reject_draft(draft_id: str):
        """Executes supervisor rejection signature."""
        data = request.get_json(silent=True) or {}
        supervisor_id = data.get("supervisor_id", "").strip()
        reason = data.get("reason") or data.get("justification") or ""

        if not supervisor_id:
            return jsonify({"success": False, "error": "Field 'supervisor_id' is required"}), 400

        try:
            res = app.console.reject_draft(
                draft_id=draft_id,
                supervisor_id=supervisor_id,
                reason=reason
            )
            return jsonify({
                "success": True,
                "message": "Draft successfully rejected. No execution occurred in Odoo ERP.",
                **res
            }), 200
        except DraftNotFoundError as e:
            return jsonify({"success": False, "error": str(e)}), 404
        except KeyError as e:
            return jsonify({"success": False, "error": f"Draft '{draft_id}' not found"}), 404
        except ValueError as ve:
            return jsonify({"success": False, "error": str(ve)}), 400
        except InvalidDraftStateError as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/audit-logs", methods=["GET"])
    def get_audit_logs():
        """Fetches historical supervisor VoBo decision audit logs."""
        supervisor_id = request.args.get("supervisor_id")
        verdict = request.args.get("verdict") or request.args.get("action")
        odoo_model = request.args.get("odoo_model")
        limit_str = request.args.get("limit", "50")
        try:
            limit = int(limit_str)
        except ValueError:
            limit = 50

        logs = app.console.get_audit_logs(
            supervisor_id=supervisor_id,
            verdict=verdict,
            odoo_model=odoo_model,
            limit=limit
        )

        return jsonify({
            "success": True,
            "count": len(logs),
            "total": len(logs),
            "audit_logs": logs
        }), 200

    @app.route("/api/v1/webhook/rfp-email", methods=["POST"])
    def webhook_rfp_email():
        """
        Production Webhook: Auto-ingests RFP emails (e.g. cotizaciones@empresa.cl),
        parses client requirements, and generates a staged Odoo draft quotation.
        """
        data = request.get_json(silent=True) or {}
        sender = data.get("sender") or data.get("from") or "Cliente Desconocido"
        subject = data.get("subject") or "Solicitud de Cotización"
        body = data.get("body") or data.get("content") or ""
        modality = "licitacion" if "licitacion" in body.lower() or "bases" in body.lower() else "compra_directa"

        payload = {
            "prompt": f"{subject} {body}",
            "client": sender,
            "modality": modality,
            "source": "email_webhook"
        }

        agent = app.console.swarm.agents.get("cotizacion_inventario")
        if not agent:
            return jsonify({"success": False, "error": "Agent cotizacion_inventario unavailable"}), 500

        draft = agent.process_event("guided_quote", payload)
        app.console.register_draft(draft)

        return jsonify({
            "success": True,
            "message": "Email RFP ingested and Odoo draft staged successfully.",
            "draft_id": draft.draft_id,
            "client": sender,
            "modality": modality
        }), 200

    @app.route("/api/v1/webhook/whatsapp", methods=["POST"])
    def webhook_whatsapp():
        """
        Production Webhook: Responds to WhatsApp Business / Telegram bot messages in < 5 seconds.
        """
        data = request.get_json(silent=True) or {}
        phone = data.get("phone") or data.get("from") or "+56900000000"
        message_text = data.get("text") or data.get("message") or ""

        payload = {
            "prompt": message_text,
            "client": f"Cliente WhatsApp ({phone})",
            "source": "whatsapp_bot"
        }

        agent = app.console.swarm.agents.get("cotizacion_inventario")
        if not agent:
            return jsonify({"success": False, "error": "Agent cotizacion_inventario unavailable"}), 500

        draft = agent.process_event("guided_quote", payload)
        app.console.register_draft(draft)

        total_amount = draft.metadata.get("total_amount", 0)
        win_rate = draft.metadata.get("win_rate_prediction", {}).get("estimated_win_rate_pct", 85)

        reply_message = (
            f"🤖 *Bot Comercial Inteligente*\n"
            f"✅ Cotización Generada: *{draft.draft_id}*\n"
            f"💰 Monto Oferta: *${total_amount:,.0f} CLP*\n"
            f"🏆 Probabilidad Win-Rate Est.: *{win_rate:.0f}%*\n"
            f"🔗 Revisa y da tu VoBo en: http://localhost:5001"
        )

        return jsonify({
            "success": True,
            "reply": reply_message,
            "draft_id": draft.draft_id
        }), 200

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        """Returns statistical overview metrics for supervisor console queue."""
        stats = app.console.get_stats()
        return jsonify({
            "success": True,
            "stats": stats,
            **stats
        }), 200

    # ==========================================
    # OPERATIONS ENGINE REST API ENDPOINTS
    # ==========================================

    @app.route("/api/operations/doc-automator/generate", methods=["POST"])
    def ops_doc_automator_generate():
        """Auto-generates technical documentation (Handover, FAT Protocol, IPES Report, Batch)."""
        data = request.get_json(silent=True) or {}
        doc_type = (data.get("doc_type") or "batch").lower().strip()
        ot_code = data.get("ot_code") or "OT-7048"
        client_name = data.get("client_name") or data.get("client") or "Enel Generación Chile"
        proj_name = data.get("proj_name") or data.get("project") or data.get("proj") or "Planta Solar CEME 1"
        try:
            monto_uf = float(data.get("monto_uf", 1250.0))
        except ValueError:
            monto_uf = 1250.0
        substation_name = data.get("substation_name") or data.get("substation") or "Subestación CEME 1"
        device_model = data.get("device_model") or data.get("device") or "SEL-735 / Orion MX"
        equipment_summary = data.get("equipment_summary") or "Gabinete PMU SEL-735 + Gateway Orion MX"
        output_format = data.get("output_format") or "pdf"

        automator = DocAutomator()

        if doc_type == "handover":
            result = automator.generate_handover_sheet(ot_code, client_name, proj_name, monto_uf, output_format)
        elif doc_type == "fat_protocol":
            result = automator.generate_cen_fat_protocol(ot_code, substation_name, device_model, output_format)
        elif doc_type == "ipes":
            result = automator.generate_ipes_report(ot_code, client_name, substation_name, equipment_summary, output_format)
        else:
            result = automator.batch_generate_ot_documentation(ot_code, client_name, proj_name, output_format)

        app.console.audit_logger.log_operations_event("doc_automator_generate", {
            "ot_code": ot_code,
            "doc_type": doc_type,
            "client": client_name
        })

        return jsonify({
            "success": True,
            "doc_type": doc_type,
            "result": result,
            "document": result
        }), 200

    @app.route("/api/operations/fat-sat/run-fat", methods=["POST"])
    def ops_fat_sat_run_fat():
        """Executes virtual FAT testing suite on laboratory bench."""
        data = request.get_json(silent=True) or {}
        ot_code = data.get("ot_code") or "OT-7048"
        device_list = data.get("device_list") or ["SEL-735", "ORION-MX"]
        if isinstance(device_list, str):
            device_list = [d.strip() for d in device_list.split(",")]

        sim = FatSatSimulator()
        result = sim.run_virtual_fat_test(ot_code, device_list)

        app.console.audit_logger.log_operations_event("fat_test_run", {
            "ot_code": ot_code,
            "device_list": device_list
        })

        return jsonify({
            "success": True,
            "result": result,
            **result
        }), 200

    @app.route("/api/operations/fat-sat/run-sat", methods=["POST"])
    def ops_fat_sat_run_sat():
        """Executes SAT testing suite on field substation."""
        data = request.get_json(silent=True) or {}
        ot_code = data.get("ot_code") or "OT-7048"
        substation_name = data.get("substation_name") or data.get("substation") or "Subestación Ancud"
        engineer_name = data.get("engineer_name") or data.get("engineer") or "Víctor Vilche"

        sim = FatSatSimulator()
        result = sim.run_virtual_sat_test(ot_code, substation_name, engineer_name)

        app.console.audit_logger.log_operations_event("sat_test_run", {
            "ot_code": ot_code,
            "substation": substation_name,
            "engineer": engineer_name
        })

        return jsonify({
            "success": True,
            "result": result,
            **result
        }), 200

    @app.route("/api/operations/fat-sat/certificate", methods=["POST"])
    def ops_fat_sat_certificate():
        """Generates formal FAT/SAT testing certificate."""
        data = request.get_json(silent=True) or {}
        ot_code = data.get("ot_code") or "OT-7048"
        client_name = data.get("client_name") or data.get("client") or "Enel Generación Chile"

        sim = FatSatSimulator()
        result = sim.generate_test_certificate(ot_code, client_name)

        app.console.audit_logger.log_operations_event("fat_sat_certificate", {
            "ot_code": ot_code,
            "client": client_name
        })

        return jsonify({
            "success": True,
            "certificate": result,
            "result": result
        }), 200

    @app.route("/api/operations/kitting/build-kit", methods=["POST"])
    def ops_kitting_build_kit():
        """Generates standardized assembly kit (PMU / SCADA RTU) and checks inventory."""
        data = request.get_json(silent=True) or {}
        ot_code = data.get("ot_code") or "OT-7050"
        kit_type = data.get("kit_type") or "PMU_PANEL_KIT_A"
        kit_type_str = kit_type.upper()

        engine = KittingEngine()
        if "SCADA" in kit_type_str or "KIT_B" in kit_type_str:
            result = engine.build_scada_rtu_kit(ot_code)
        else:
            result = engine.build_pmu_assembly_kit(ot_code)

        inventory = engine.verify_inventory_stock(kit_type, odoo_client=app.console.odoo_client)
        checklist = engine.get_prewiring_workshop_checklist(kit_type)

        app.console.audit_logger.log_operations_event("kitting_build_kit", {
            "ot_code": ot_code,
            "kit_type": kit_type,
            "kit_id": result.get("kit_id")
        })

        return jsonify({
            "success": True,
            "kit": result,
            "result": result,
            "inventory": inventory,
            "checklist": checklist
        }), 200

    @app.route("/api/operations/accreditation/compile", methods=["POST"])
    def ops_accreditation_compile():
        """Compiles worker and subcontractor accreditation packages."""
        data = request.get_json(silent=True) or {}
        ot_code = data.get("ot_code") or "OT-7060"
        client = data.get("client") or data.get("client_name") or "Transelec"
        workers = data.get("workers") or [
            {"rut": "15.420.110-8", "name": "Carlos Mendoza"},
            {"rut": "16.890.344-K", "name": "Roberto Silva"}
        ]
        target_platform = data.get("target_platform")
        worker_rut = data.get("worker_rut")
        worker_name = data.get("worker_name")
        substation = data.get("substation")

        acc = AccreditationAutomator()

        if target_platform and (worker_rut or (isinstance(workers, list) and len(workers) == 1)):
            w_rut = worker_rut or workers[0].get("rut") or workers[0].get("worker_rut")
            w_name = worker_name or workers[0].get("name") or workers[0].get("worker_name")
            sub = substation or f"Subestación {ot_code}"
            result = acc.compile_platform_dossier(w_rut, w_name, sub, target_platform)
            audit_res = acc.audit_document_expirations(result)
            package = {"dossier": result, "audit": audit_res}
        else:
            package = acc.generate_substation_access_package(ot_code, client, workers)

        app.console.audit_logger.log_operations_event("accreditation_compile", {
            "ot_code": ot_code,
            "client": client
        })

        return jsonify({
            "success": True,
            "package": package,
            "result": package
        }), 200

    @app.route("/api/operations/payment-statement/generate", methods=["POST"])
    def ops_payment_statement_generate():
        """
        Generates official Payment Milestone Statement (Estado de Pago) and
        stages an Odoo account.move draft payload into console VoBo queue.
        """
        data = request.get_json(silent=True) or {}
        ot_code = data.get("ot_code") or "OT-7048"
        client_name = data.get("client_name") or data.get("client") or "Enel Generación Chile"
        milestone_name = data.get("milestone_name") or "Hito 2: Entrega Equipos y Pruebas FAT"
        try:
            milestone_pct = float(data.get("milestone_pct", 50.0))
        except ValueError:
            milestone_pct = 50.0
        try:
            total_contract_uf = float(data.get("total_contract_uf", 1500.0))
        except ValueError:
            total_contract_uf = 1500.0
        try:
            uf_value_clp = float(data.get("uf_value_clp", 38377.09))
        except ValueError:
            uf_value_clp = 38377.09

        edp_automator = PaymentStatementAutomator()
        statement = edp_automator.generate_payment_statement(
            ot_code, client_name, milestone_name, milestone_pct, total_contract_uf, uf_value_clp
        )
        odoo_payload = edp_automator.create_odoo_invoice_draft_payload(ot_code, statement)

        draft_action = DraftAction(
            agent_name="estados_pago",
            target_model="account.move",
            action_type="create",
            proposed_payload=odoo_payload,
            justification=f"Estado de Pago {statement['statement_id']} para {client_name} - VoBo Trigger",
            confidence_score=0.95
        )

        draft_id = app.console.stage_operations_draft(draft_action)

        app.console.audit_logger.log_operations_event("payment_statement_generate", {
            "ot_code": ot_code,
            "draft_id": draft_id,
            "statement_id": statement.get("statement_id")
        })

        return jsonify({
            "success": True,
            "draft_id": draft_id,
            "statement": statement,
            "odoo_payload": odoo_payload,
            "result": statement
        }), 201

    @app.route("/api/operations/metrics", methods=["GET"])
    def ops_metrics():
        """Returns financial impact metrics with 54.8% gross margin retention."""
        try:
            num_ots = int(request.args.get("num_ots", 5))
        except ValueError:
            num_ots = 5
        try:
            total_contract_uf = float(request.args.get("total_contract_uf", 3500.0))
        except ValueError:
            total_contract_uf = 3500.0
        try:
            uf_value_clp = float(request.args.get("uf_value_clp", 38377.09))
        except ValueError:
            uf_value_clp = 38377.09
        try:
            num_devices = int(request.args.get("num_devices", 10))
        except ValueError:
            num_devices = 10
        try:
            num_workers = int(request.args.get("num_workers", 4))
        except ValueError:
            num_workers = 4
        try:
            num_substations = int(request.args.get("num_substations", 3))
        except ValueError:
            num_substations = 3

        fin_engine = FinancialImpactEngine()
        metrics = fin_engine.calculate_financial_summary(
            num_ots=num_ots,
            total_contract_uf=total_contract_uf,
            uf_value_clp=uf_value_clp,
            num_devices=num_devices,
            num_workers=num_workers,
            num_substations=num_substations
        )

        return jsonify({
            "success": True,
            "metrics": metrics,
            **metrics
        }), 200

    return app


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app = create_app()
    print(f"🚀 Servidor Web de Supervisión iniciado en http://127.0.0.1:{port}/")
    app.run(host="0.0.0.0", port=port, debug=False)


