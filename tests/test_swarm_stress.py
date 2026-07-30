"""
Adversarial Stress Test Suite for Swarm Agentic Engine (Milestone 3).
Executes high-throughput concurrent event dispatches (100+ threads),
exception/crash injection during broadcast dispatches for error isolation,
and event routing edge cases (unregistered event types, empty payloads, malformed payloads).
"""

import pytest
import concurrent.futures
import threading
from typing import Dict, Any, List
from pydantic import ValidationError

from swarm_engine.base_agent import BaseAgent, DraftAction
from swarm_engine.swarm import AgentSwarm, KNOWN_AGENTS, EVENT_ROUTING_MAP
from swarm_engine.agents.rfq_prospeccion import RFQProspeccionAgent
from swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent
from swarm_engine.agents.operaciones_presupuesto import OperacionesPresupuestoAgent
from swarm_engine.agents.estados_pago import EstadosPagoAgent
from swarm_engine.agents.gestion_documental import GestionDocumentalAgent
from swarm_engine.agents.conciliador_contable import ConciliadorContableAgent


class CrashAgent(BaseAgent):
    """Specialized agent designed to crash with specified exception types."""
    def __init__(self, agent_name: str, exception_to_raise: Exception):
        super().__init__(agent_name=agent_name, domain="test_crash")
        self.exception_to_raise = exception_to_raise

    def process_event(self, event_type: str, payload: Dict[str, Any]) -> DraftAction:
        raise self.exception_to_raise


class TestSwarmEngineStressAndConcurrency:

    def test_high_throughput_concurrent_dispatch_100_threads(self):
        """
        STRESS TEST 1: High-throughput concurrent dispatches across 150 threads.
        Simulates heavy concurrent business event streams across targeted event dispatches.
        """
        swarm = AgentSwarm()
        num_threads = 150

        event_types = [
            "rfq_received",
            "quote_request",
            "audit_budget_overrun",
            "generate_progress_invoice",
            "verify_contractor_compliance",
            "process_dte",
        ]

        results = []
        errors = []

        def worker(thread_idx: int):
            event_type = event_types[thread_idx % len(event_types)]
            payload = {
                "title": f"Concurrent Event #{thread_idx}",
                "partner_id": (thread_idx % 5) + 1,
                "amount_untaxed": 100000.0 * (thread_idx + 1),
                "items": [{"name": f"Item {thread_idx}", "qty": 1.0, "unit_price": 50000.0}],
                "documents": [{"doc_type": "F30-1", "status": "valid"}],
                "dte_folio": f"F-{1000 + thread_idx}",
            }
            try:
                drafts = swarm.dispatch_event(event_type, payload)
                return drafts
            except Exception as e:
                errors.append((thread_idx, e))
                return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        assert len(errors) == 0, f"Encountered {len(errors)} unhandled exceptions during concurrent dispatches: {errors}"
        assert len(results) == num_threads

        total_drafts = sum(len(drafts) for drafts in results)
        assert total_drafts == num_threads, f"Expected {num_threads} drafts, got {total_drafts}"

        # Verify all drafts have pending_vobo status and unique draft_ids
        draft_ids = set()
        for drafts in results:
            for draft in drafts:
                assert draft.status == "pending_vobo"
                draft_ids.add(draft.draft_id)

        assert len(draft_ids) == num_threads

    def test_concurrent_broadcast_dispatch_100_threads(self):
        """
        STRESS TEST 2: 100 concurrent threads executing broadcast_audit.
        Each broadcast call invokes all 6 registered agents.
        Total expected drafts = 100 threads * 6 agents = 600 drafts.
        """
        swarm = AgentSwarm()
        num_threads = 100

        results = []
        errors = []

        def broadcast_worker(thread_idx: int):
            payload = {"title": f"Broadcast Stress Test #{thread_idx}", "thread_id": thread_idx}
            try:
                return swarm.dispatch_event("broadcast_audit", payload)
            except Exception as e:
                errors.append((thread_idx, e))
                return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            futures = [executor.submit(broadcast_worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        assert len(errors) == 0
        assert len(results) == num_threads

        total_drafts = sum(len(drafts) for drafts in results)
        assert total_drafts == num_threads * 6, f"Expected {num_threads * 6} drafts, got {total_drafts}"

    def test_concurrent_registration_and_dispatch(self):
        """
        STRESS TEST 3: Concurrent agent registration/unregistration while dispatches occur.
        Verifies dictionary access safety and lack of unhandled race crashes.
        """
        swarm = AgentSwarm()

        stop_event = threading.Event()
        dispatch_errors = []
        register_errors = []

        def dispatch_loop():
            while not stop_event.is_set():
                try:
                    swarm.dispatch_event("broadcast_audit", {"test": "concurrency"})
                except Exception as e:
                    dispatch_errors.append(e)

        def register_unregister_loop():
            counter = 0
            while not stop_event.is_set():
                counter += 1
                name = f"dynamic_agent_{counter % 5}"
                try:
                    agent = CotizacionInventarioAgent()
                    agent.agent_name = name
                    swarm.register_agent(agent)
                    swarm.unregister_agent(name)
                except Exception as e:
                    register_errors.append(e)

        t1 = threading.Thread(target=dispatch_loop)
        t2 = threading.Thread(target=register_unregister_loop)

        t1.start()
        t2.start()

        threading.Event().wait(1.0)  # Run concurrent loop for 1 second
        stop_event.set()

        t1.join()
        t2.join()

        assert len(dispatch_errors) == 0, f"Dispatch errors during concurrent reg/unreg: {dispatch_errors}"
        assert len(register_errors) == 0, f"Register errors during concurrent reg/unreg: {register_errors}"


class TestSwarmEngineErrorIsolation:

    def test_broadcast_audit_error_isolation_single_crash(self):
        """
        ERROR ISOLATION 1: Inject single agent crash during broadcast.
        Verifies that broadcast_audit does not halt remaining 5 agents.
        """
        swarm = AgentSwarm(agents=[])

        rfq = RFQProspeccionAgent()
        cotiz = CotizacionInventarioAgent()
        crasher = CrashAgent("failing_agent_1", RuntimeError("Database connection reset"))
        ops = OperacionesPresupuestoAgent()
        inv = EstadosPagoAgent()
        doc = GestionDocumentalAgent()

        swarm.register_agent(rfq)
        swarm.register_agent(cotiz)
        swarm.register_agent(crasher)
        swarm.register_agent(ops)
        swarm.register_agent(inv)
        swarm.register_agent(doc)

        drafts = swarm.dispatch_event("broadcast_audit", {"title": "Single Crash Audit"})

        # 5 healthy agents must return valid DraftActions
        assert len(drafts) == 5
        agent_names_returned = {d.agent_name for d in drafts}
        assert "failing_agent_1" not in agent_names_returned
        assert swarm.get_agent("failing_agent_1").status == "error"
        assert swarm.get_agent("rfq_prospeccion").status == "idle"

    def test_broadcast_audit_error_isolation_multiple_different_exceptions(self):
        """
        ERROR ISOLATION 2: Inject multiple distinct exception types (ValueError, ZeroDivisionError, TypeError).
        Verifies that all healthy agents complete and failing agents transition to error state.
        """
        swarm = AgentSwarm(agents=[])

        crasher_val = CrashAgent("crash_val", ValueError("Invalid value parameter"))
        crasher_zero = CrashAgent("crash_zero", ZeroDivisionError("division by zero"))
        crasher_type = CrashAgent("crash_type", TypeError("object of type 'NoneType' has no len()"))

        healthy_1 = RFQProspeccionAgent()
        healthy_2 = ConciliadorContableAgent()

        swarm.register_agent(crasher_val)
        swarm.register_agent(healthy_1)
        swarm.register_agent(crasher_zero)
        swarm.register_agent(healthy_2)
        swarm.register_agent(crasher_type)

        drafts = swarm.dispatch_event("broadcast_audit", {"title": "Multi-Exception Audit"})

        assert len(drafts) == 2
        returned_agents = {d.agent_name for d in drafts}
        assert returned_agents == {"rfq_prospeccion", "conciliador_contable"}

        assert swarm.get_agent("crash_val").status == "error"
        assert swarm.get_agent("crash_zero").status == "error"
        assert swarm.get_agent("crash_type").status == "error"

    def test_broadcast_audit_all_agents_crashing(self):
        """
        ERROR ISOLATION 3: All registered agents crash during broadcast dispatch.
        Verifies that dispatch_event returns empty list [] without raising unhandled exceptions.
        """
        swarm = AgentSwarm(agents=[])
        for i in range(4):
            swarm.register_agent(CrashAgent(f"crash_{i}", RuntimeError(f"Failure #{i}")))

        drafts = swarm.dispatch_event("broadcast", {"test": "all_fail"})
        assert drafts == []
        for i in range(4):
            assert swarm.get_agent(f"crash_{i}").status == "error"


class TestSwarmEngineRoutingEdgeCases:

    def test_unregistered_event_type(self):
        """
        EDGE CASE 1: Dispatching an unmapped/unregistered event type.
        Should return empty list [] and log a warning without throwing exception.
        """
        swarm = AgentSwarm()
        drafts = swarm.dispatch_event("completely_unknown_unregistered_event_xyz", {"data": 123})
        assert drafts == []

    def test_empty_payload_dict(self):
        """
        EDGE CASE 2: Dispatching empty dict payload {} to all routed events and broadcast.
        Verifies that specialized agents fallback to safe defaults without crashing.
        """
        swarm = AgentSwarm()

        for event_type in ["rfq_received", "quote_request", "audit_budget_overrun", "generate_progress_invoice", "verify_contractor_compliance", "process_dte"]:
            drafts = swarm.dispatch_event(event_type, {})
            assert len(drafts) == 1
            assert isinstance(drafts[0], DraftAction)
            assert drafts[0].status == "pending_vobo"

        broadcast_drafts = swarm.dispatch_event("broadcast_audit", {})
        assert len(broadcast_drafts) == 6

    def test_malformed_non_dict_payloads_in_dispatch(self):
        """
        EDGE CASE 3: Dispatching malformed payloads (None, str, list) to dispatch_event.
        Verifies that error isolation catches AttributeError/TypeError from handlers and isolates error per agent.
        """
        swarm = AgentSwarm()

        for malformed in [None, "invalid_string_payload", [1, 2, 3], 12345]:
            # dispatch_event should isolate handler errors and return []
            drafts = swarm.dispatch_event("rfq_received", malformed)
            assert drafts == []

    def test_process_task_with_malformed_payload_raises(self):
        """
        EDGE CASE 4: Calling process_task directly with malformed payload (None).
        Unlike dispatch_event, process_task contract re-raises the exception.
        """
        swarm = AgentSwarm()

        with pytest.raises(AttributeError):
            swarm.process_task("rfq_prospeccion", None)

        assert swarm.get_agent("rfq_prospeccion").status == "error"

    def test_broadcast_event_aliases(self):
        """
        EDGE CASE 5: Testing all broadcast alias strings ("broadcast_audit", "broadcast", "*", "all").
        """
        swarm = AgentSwarm()

        aliases = ["broadcast_audit", "broadcast", "*", "all"]
        for alias in aliases:
            drafts = swarm.dispatch_event(alias, {"test": alias})
            assert len(drafts) == 6, f"Alias '{alias}' did not trigger all 6 agents"
