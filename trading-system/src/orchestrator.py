"""Multi-agent Orchestrator coordinating Research -> Strategy -> Risk -> Execution -> Reconciliation.

SIMULATION ONLY — NO REAL BROKER — NO REAL CREDENTIALS.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from engines.risk_engine import RiskEngine
from engines.signal_engine import SignalEngine
from schemas import OrderEvent, RiskDecision, Signal, new_id, utc_now_iso
from services.audit import AuditLog
from services.data_adapter import DataAdapter
from services.simulator import Simulator


class Orchestrator:
    def __init__(self, audit_path: Optional[str] = None) -> None:
        self.data = DataAdapter()
        self.sim = Simulator()
        self.signal_engine = SignalEngine()
        self.risk_engine = RiskEngine()
        self.audit = AuditLog(log_path=audit_path)

        self.cycle_count: int = 0
        self.paused: bool = False
        self.emergency_stop: bool = False
        self.limits_configured: bool = self.risk_engine.limits_configured

        self.signals_history: List[Signal] = []
        self.risk_decisions: List[RiskDecision] = []

        # Seed prices into simulator
        for inst in ("SYNTH/BTC", "SYNTH/ETH"):
            hist = self.data.get_history(inst, limit=1)
            if hist:
                self.sim.update_price(inst, hist[-1].price)

        self.audit.log(
            event_type="SYSTEM_INIT",
            agent="Orchestrator",
            data={
                "mode": "SIMULATION",
                "limits_configured": self.limits_configured,
                "emergency_stop": self.emergency_stop,
            },
        )

    def pause(self) -> Dict[str, Any]:
        self.paused = True
        self.audit.log("SYSTEM_PAUSED", "Orchestrator", {"paused": True, "cycle_count": self.cycle_count})
        return self.get_status()

    def resume(self) -> Dict[str, Any]:
        self.paused = False
        self.audit.log("SYSTEM_RESUMED", "Orchestrator", {"paused": False, "cycle_count": self.cycle_count})
        return self.get_status()

    def activate_emergency_stop(self, reason: str = "Manual operator activation") -> Dict[str, Any]:
        self.emergency_stop = True
        self.paused = True
        self.audit.log(
            "EMERGENCY_STOP_ACTIVATED",
            "Risk",
            {"emergency_stop": True, "reason": reason, "cycle_count": self.cycle_count},
        )
        return self.get_status()

    def reset_emergency_stop(self) -> Dict[str, Any]:
        self.emergency_stop = False
        self.audit.log(
            "EMERGENCY_STOP_RESET",
            "Orchestrator",
            {"emergency_stop": False, "cycle_count": self.cycle_count},
        )
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        unrealized = round(sum(p.unrealized_pnl for p in self.sim.positions), 2)
        return {
            "mode": "SIMULATION",
            "cycle_count": self.cycle_count,
            "paused": self.paused,
            "emergency_stop": self.emergency_stop,
            "limits_configured": self.limits_configured,
            "positions": [p.to_dict() for p in self.sim.positions],
            "realized_pnl": round(self.sim.realized_pnl, 2),
            "unrealized_pnl": unrealized,
            "total_pnl": round(self.sim.realized_pnl + unrealized, 2),
            "total_orders": len(self.sim.orders),
            "risk_limits": self.risk_engine.get_limits(),
        }

    def run_cycle(self, instrument: str = "SYNTH/BTC") -> Dict[str, Any]:
        self.cycle_count += 1
        task_id = new_id(f"cycle_{self.cycle_count}")

        # 1. Research: fetch synthetic market observation
        obs = self.data.fetch(instrument)
        self.sim.update_price(instrument, obs.price)
        self.audit.log(
            "RESEARCH_OBSERVATION",
            "Researcher",
            {
                "cycle": self.cycle_count,
                "instrument": instrument,
                "price": obs.price,
                "bid": obs.bid,
                "ask": obs.ask,
                "volume": obs.volume,
                "quality": obs.quality,
            },
        )

        # Check existing position SL/TP protection first
        protection_events = self.sim.check_protection()
        for hit_inst, hit_type in protection_events:
            self.audit.log(
                "PROTECTION_TRIGGERED",
                "Executor",
                {"cycle": self.cycle_count, "instrument": hit_inst, "event": hit_type},
            )

        # 2. Strategy: evaluate deterministic signal engine
        history = self.data.get_history(instrument, limit=25)
        signal = self.signal_engine.evaluate(history, task_id=task_id)
        self.signals_history.append(signal)
        if len(self.signals_history) > 100:
            del self.signals_history[:-100]

        self.audit.log(
            "STRATEGY_SIGNAL",
            "Strategist",
            {
                "cycle": self.cycle_count,
                "signal_id": signal.signal_id,
                "instrument": signal.instrument,
                "signal_type": signal.signal_type,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "rules_triggered": signal.rules_triggered,
            },
        )

        # 3. Risk: deterministic evaluation
        risk_decision = self.risk_engine.evaluate(
            signal=signal,
            observation=obs,
            positions=self.sim.positions,
            realized_pnl=self.sim.realized_pnl,
            peak_equity=self.sim.peak_equity,
            emergency_stop=self.emergency_stop,
        )
        self.risk_decisions.append(risk_decision)
        if len(self.risk_decisions) > 100:
            del self.risk_decisions[:-100]

        self.audit.log(
            "RISK_DECISION",
            "Risk",
            {
                "cycle": self.cycle_count,
                "decision_id": risk_decision.decision_id,
                "signal_id": signal.signal_id,
                "approved": risk_decision.approved,
                "rejection_code": risk_decision.rejection_code,
                "rejection_reason": risk_decision.rejection_reason,
                "approved_quantity": risk_decision.approved_quantity,
            },
        )

        # 4. Execution: only if approved and not in emergency stop
        order_event: Optional[OrderEvent] = None
        if risk_decision.approved and signal.signal_type in ("BUY", "SELL"):
            order_event = self.sim.execute_order(
                instrument=instrument,
                side=signal.signal_type,
                quantity=risk_decision.approved_quantity,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
            )
            self.audit.log(
                "ORDER_EXECUTED",
                "Executor",
                {
                    "cycle": self.cycle_count,
                    "order_id": order_event.order_id,
                    "instrument": order_event.instrument,
                    "side": order_event.side,
                    "quantity": order_event.quantity,
                    "fill_price": order_event.fill_price,
                    "commission": order_event.commission,
                    "status": order_event.status,
                },
            )
        elif signal.signal_type in ("BUY", "SELL") and not risk_decision.approved:
            # Record rejected order in simulator history for visibility
            rejected_order = OrderEvent(
                order_id=new_id("ord"),
                instrument=instrument,
                side=signal.signal_type,
                quantity=0.0,
                status="rejected",
                fill_price=obs.price,
                commission=0.0,
                timestamp=utc_now_iso(),
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                reason=risk_decision.rejection_code,
            )
            self.sim.orders.append(rejected_order)
            order_event = rejected_order

        # 5. Reconciliation
        reconciliation = self.sim.reconcile()
        self.audit.log(
            "CYCLE_RECONCILED",
            "Orchestrator",
            {
                "cycle": self.cycle_count,
                "instrument": instrument,
                "open_positions": len(self.sim.positions),
                "realized_pnl": reconciliation["realized_pnl"],
                "unrealized_pnl": reconciliation["unrealized_pnl"],
                "total_orders": reconciliation["total_orders"],
            },
        )

        return {
            "cycle_count": self.cycle_count,
            "task_id": task_id,
            "instrument": instrument,
            "observation": obs.to_dict(),
            "signal": signal.to_dict(),
            "risk_decision": risk_decision.to_dict(),
            "order": order_event.to_dict() if order_event else None,
            "protection_events": protection_events,
            "reconciliation": reconciliation,
            "status": self.get_status(),
            "timestamp": utc_now_iso(),
        }
