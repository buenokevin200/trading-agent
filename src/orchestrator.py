"""Orchestrator — coordinates the trading flow and manages the cycle."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import logging
import json
import os

from .schemas.task import Task, TaskStatus, TaskPriority
from .schemas.observation import Observation
from .schemas.signal import Signal, SignalType
from .schemas.risk_decision import RiskDecision
from .schemas.authorization import Authorization
from .schemas.intent import Intent, IntentType
from .schemas.order_event import OrderEvent, OrderStatus
from .schemas.incident import Incident, IncidentType
from .engines.signal_engine import SignalEngine
from .engines.risk_engine import RiskEngine, RiskLimits, RiskConfig
from .services.simulator import Simulator
from .services.execution import ExecutionService
from .services.data_adapter import DataAdapter
from .services.audit import AuditLog

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Coordinates the trading flow:
    Research → Strategy → Risk → Execution → Reconciliation

    Does NOT generate signals, call trading tools, or make discretionary decisions.
    Routes work to the appropriate engine/service in the correct order.
    """

    def __init__(
        self,
        signal_engine: SignalEngine,
        risk_engine: RiskEngine,
        execution_service: ExecutionService,
        data_adapter: DataAdapter,
        audit: AuditLog,
    ):
        self.signal_engine = signal_engine
        self.risk_engine = risk_engine
        self.execution = execution_service
        self.data = data_adapter
        self.audit = audit
        self._cycle_count = 0
        self._paused = False

    def pause(self):
        self._paused = True
        self.audit.append("orchestrator_paused", {}, agent="orchestrator")

    def resume(self):
        self._paused = False
        self.audit.append("orchestrator_resumed", {}, agent="orchestrator")

    def run_cycle(self, instrument: str = "SYNTH/BTC") -> dict:
        """
        Run one complete cycle: research → strategy → risk → execution → reconcile.
        Returns a summary dict for the kanban board / audit.
        """
        if self._paused:
            return {"status": "paused", "cycle": self._cycle_count}

        self._cycle_count += 1
        cycle_id = self._cycle_count
        result = {"cycle": cycle_id, "instrument": instrument, "steps": []}

        # Step 1: Research — fetch data
        self.audit.append("cycle_start", {"cycle": cycle_id, "instrument": instrument}, agent="orchestrator")
        observations = [self.data.fetch(instrument)]
        result["steps"].append({"step": "research", "observations": len(observations)})

        # Step 2: Strategy — evaluate signal
        task_id = f"cycle-{cycle_id}"
        signal = self.signal_engine.evaluate(observations, task_id)
        self.audit.append("signal_generated", {
            "signal_id": signal.id,
            "type": signal.signal_type.value,
            "instrument": signal.instrument,
            "strategy": signal.strategy_version,
        }, agent="strategist")
        result["steps"].append({
            "step": "strategy",
            "signal_type": signal.signal_type.value,
            "signal_id": signal.id,
        })

        if signal.is_no_op:
            result["status"] = "no_operation"
            self.audit.append("cycle_complete", {"cycle": cycle_id, "result": "NO_OPERATION"}, agent="orchestrator")
            return result

        # Step 3: Risk — evaluate
        decision = self.risk_engine.evaluate(signal, observations)
        self.audit.append("risk_decision", {
            "decision_id": decision.id,
            "approved": decision.approved,
            "rejection_code": decision.rejection_code.value if decision.rejection_code else None,
        }, agent="risk")
        result["steps"].append({
            "step": "risk",
            "approved": decision.approved,
            "rejection_code": decision.rejection_code.value if decision.rejection_code else None,
        })

        if not decision.approved:
            result["status"] = "rejected"
            self.audit.append("cycle_complete", {"cycle": cycle_id, "result": "rejected"}, agent="orchestrator")
            return result

        # Issue authorization
        auth = self.risk_engine.issue_authorization(decision, signal)

        # Step 4: Execution
        intent = Intent(
            authorization_id=auth.id,
            signal_id=signal.id,
            instrument=signal.instrument,
            intent_type=IntentType(signal.signal_type.value) if signal.signal_type != SignalType.CLOSE else IntentType.CLOSE,
            quantity=1.0,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            mode="simulation",
        )

        order = self.execution.process(intent, auth)
        result["steps"].append({
            "step": "execution",
            "order_id": order.id,
            "order_status": order.status.value,
        })

        # Step 5: Reconciliation
        recon = self.execution.reconcile()
        result["steps"].append({"step": "reconciliation", "positions": len(recon["positions"])})

        result["status"] = order.status.value
        self.audit.append("cycle_complete", {
            "cycle": cycle_id,
            "result": order.status.value,
            "order_id": order.id,
        }, agent="orchestrator")

        return result

    def get_status(self) -> dict:
        """Get current system status for the dashboard."""
        recon = self.execution.reconcile()
        return {
            "cycle_count": self._cycle_count,
            "paused": self._paused,
            "positions": recon["positions"],
            "realized_pnl": recon["realized_pnl"],
            "total_orders": recon["total_orders"],
            "emergency_stop": self.risk_engine.limits.config.emergency_stop_active,
            "limits_configured": self.risk_engine.limits.config.is_configured(),
        }
