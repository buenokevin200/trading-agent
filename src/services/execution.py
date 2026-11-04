"""Execution service — processes authorized intents, manages idempotency and reconciliation."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import logging
import threading
import os

from ..schemas.intent import Intent, IntentType
from ..schemas.authorization import Authorization
from ..schemas.order_event import OrderEvent, OrderStatus
from ..schemas.risk_decision import RiskRejectionCode
from ..engines.risk_engine import RiskEngine
from .simulator import Simulator
from .audit import AuditLog

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Execution service. Processes authorized intents through the simulator.
    Enforces: authorization validation, idempotency, single-executor lock,
    revalidation before send, and reconciliation.
    """

    def __init__(
        self,
        simulator: Simulator,
        risk_engine: RiskEngine,
        audit: AuditLog,
        lock_path: str = "/tmp/trading-executor.lock",
    ):
        self.simulator = simulator
        self.risk_engine = risk_engine
        self.audit = audit
        self.lock_path = lock_path
        self._processed_intents: set[str] = set()
        self._lock = threading.Lock()

    def acquire_lock(self) -> bool:
        """Acquire single-executor lock (file-based, persists across restarts)."""
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is alive
                os.kill(pid, 0)
                logger.warning(f"Another executor is active (PID {pid})")
                return False
            except (ProcessLookupError, ValueError, OSError):
                pass  # Stale lock
        with open(self.lock_path, "w") as f:
            f.write(str(os.getpid()))
        return True

    def release_lock(self):
        """Release the single-executor lock."""
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)

    def process(self, intent: Intent, auth: Authorization) -> OrderEvent:
        """
        Process an authorized intent. Validates authorization, executes
        through simulator, records audit, enforces idempotency.
        """
        # Idempotency check
        if intent.id in self._processed_intents:
            self.audit.append("duplicate_intent_rejected", {
                "intent_id": intent.id,
                "reason": "Already processed",
            }, agent="executor")
            return OrderEvent(
                intent_id=intent.id,
                instrument=intent.instrument,
                side=intent.intent_type.value,
                quantity=intent.quantity,
                status=OrderStatus.REJECTED,
                rejection_reason="Duplicate intent (idempotency)",
            )

        # Validate authorization
        valid, code = self.risk_engine.validate_authorization(
            auth,
            instrument=intent.instrument,
            intent_type=intent.intent_type.value,
            quantity=intent.quantity,
            entry_price=intent.entry_price,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
        )

        if not valid:
            self.audit.append("authorization_invalid", {
                "intent_id": intent.id,
                "auth_id": auth.id,
                "rejection_code": code.value if code else "unknown",
            }, agent="executor")
            return OrderEvent(
                intent_id=intent.id,
                instrument=intent.instrument,
                side=intent.intent_type.value,
                quantity=intent.quantity,
                status=OrderStatus.REJECTED,
                rejection_reason=f"Authorization invalid: {code.value if code else 'unknown'}",
            )

        # Mark authorization as used (single-use)
        self.risk_engine.mark_authorization_used(auth.id)

        # Execute through simulator
        with self._lock:
            order = self.simulator.execute_order(intent)
            self._processed_intents.add(intent.id)

        # Audit
        self.audit.append("order_executed", {
            "order_id": order.id,
            "intent_id": intent.id,
            "auth_id": auth.id,
            "instrument": order.instrument,
            "side": order.side,
            "quantity": order.quantity,
            "status": order.status.value,
            "fills": [
                {"qty": f.filled_qty, "price": f.filled_price, "commission": f.commission}
                for f in order.fills
            ] if order.fills else [],
        }, agent="executor")

        return order

    def reconcile(self) -> dict:
        """Reconcile positions and orders."""
        sim_report = self.simulator.reconcile()
        self.audit.append("reconciliation", sim_report, agent="executor")
        return sim_report

    def check_protections(self) -> list[tuple[str, str]]:
        """Check position protections."""
        hits = self.simulator.check_protection()
        if hits:
            self.audit.append("protection_hit", {
                "hits": [{"instrument": i, "type": t} for i, t in hits],
            }, agent="executor")
        return hits
