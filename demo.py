#!/usr/bin/env python3
"""Demonstration: synthetic cycle end-to-end.

Runs a complete trading cycle with synthetic data and configured limits,
showing the full flow: Research → Strategy → Risk → Execution → Reconciliation.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.engines.signal_engine import SignalEngine
from src.engines.risk_engine import RiskEngine, RiskLimits, RiskConfig
from src.services.simulator import Simulator
from src.services.execution import ExecutionService
from src.services.data_adapter import DataAdapter
from src.services.audit import AuditLog
from src.orchestrator import Orchestrator


def main():
    print("=" * 60)
    print("TRADING SYSTEM — SYNTHETIC DEMONSTRATION")
    print("Mode: SIMULATION (no real money, no real broker)")
    print("=" * 60)

    # Setup audit
    audit_path = os.path.join(os.path.dirname(__file__), "..", "data", "audit.jsonl")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    audit = AuditLog(audit_path)

    # Configure risk limits (fully configured for demo)
    config = RiskConfig(
        allowed_instruments={"SYNTH/BTC", "SYNTH/ETH"},
        risk_per_trade_pct=1.0,
        max_exposure_pct=10.0,
        max_daily_loss_pct=5.0,
        max_drawdown_pct=20.0,
        max_positions=3,
        max_order_frequency_sec=1,
        max_pending_orders=5,
        leverage_enabled=False,
        shorts_enabled=False,
        reference_capital=10000.0,
        emergency_stop_active=False,
        max_data_age_sec=60,
    )
    limits = RiskLimits(config=config)
    risk_engine = RiskEngine(limits)

    # Setup simulator
    sim = Simulator(commission_pct=0.001, slippage_pct=0.0005)
    sim.set_price("SYNTH/BTC", 100.0)
    sim.set_price("SYNTH/ETH", 50.0)

    # Setup execution
    exec_service = ExecutionService(sim, risk_engine, audit)

    # Setup data adapter (synthetic)
    data = DataAdapter({"SYNTH/BTC", "SYNTH/ETH"}, seed=42)

    # Setup signal engine with SMA cross strategy
    signal_engine = SignalEngine("sma_cross", {"short_window": 2, "long_window": 5})

    # Setup orchestrator
    orch = Orchestrator(signal_engine, risk_engine, exec_service, data, audit)

    # Run cycles — accumulate observations for SMA strategy
    print("\n─ Running 10 synthetic cycles ─\n")
    from src.schemas.observation import Observation, DataQuality
    from src.schemas.signal import Signal, SignalType
    from src.schemas.intent import Intent, IntentType
    from datetime import datetime, timezone
    import uuid

    obs_history: dict[str, list] = {"SYNTH/BTC": [], "SYNTH/ETH": []}

    # Inject a bullish trend for SYNTH/BTC to trigger a BUY signal
    bullish_prices = [95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0]

    for i in range(10):
        instrument = "SYNTH/BTC" if i % 2 == 0 else "SYNTH/ETH"

        # Research: fetch observation (use injected price for BTC, synthetic for ETH)
        if instrument == "SYNTH/BTC" and i < len(bullish_prices):
            obs = Observation(
                instrument=instrument, source="synthetic-feed",
                price=bullish_prices[i], bid=bullish_prices[i]*0.999,
                ask=bullish_prices[i]*1.001, volume=500.0,
            )
            sim.set_price(instrument, bullish_prices[i])
        else:
            obs = data.fetch(instrument)
        obs_history[instrument].append(obs)
        audit.append("observation_fetched", {
            "instrument": instrument, "price": obs.price, "quality": obs.quality.value
        }, agent="researcher")

        # Strategy: evaluate with full history
        task_id = f"demo-cycle-{i+1}"
        signal = signal_engine.evaluate(obs_history[instrument], task_id)
        audit.append("signal_generated", {
            "signal_id": signal.id, "type": signal.signal_type.value,
            "instrument": signal.instrument, "strategy": signal.strategy_version,
        }, agent="strategist")

        print(f"Cycle {i+1}: instrument={instrument} → signal={signal.signal_type.value}", end="")

        if signal.is_no_op:
            print(f" (reason: {signal.invalidation_reason})")
            continue

        # Risk
        decision = risk_engine.evaluate(signal, obs_history[instrument])
        print(f" → risk={'APPROVED' if decision.approved else 'REJECTED'}", end="")

        if not decision.approved:
            print(f" ({decision.rejection_code.value}: {decision.rejection_reason})")
            continue

        # Authorization + Execution
        auth = risk_engine.issue_authorization(decision, signal)
        intent = Intent(
            authorization_id=auth.id, signal_id=signal.id, instrument=signal.instrument,
            intent_type=IntentType(signal.signal_type.value), quantity=1.0,
            entry_price=signal.entry_price, stop_loss=signal.stop_loss,
            take_profit=signal.take_profit, mode="simulation",
        )
        order = exec_service.process(intent, auth)
        print(f" → order={order.status.value}")

        # Update risk limits with current positions
        limits.open_positions = sim.positions
        limits.last_order_time = datetime.now(timezone.utc)

    # Show final status
    print("\n─ Final Status ─\n")
    status = orch.get_status()
    print(json.dumps(status, indent=2, default=str))

    # Verify audit chain
    ok, errors = audit.verify_chain()
    print(f"\n─ Audit chain integrity: {'OK' if ok else 'BROKEN'} ─")
    if errors:
        for e in errors:
            print(f"  ⚠ {e}")

    # Reconciliation
    print("\n─ Reconciliation ─\n")
    recon = exec_service.reconcile()
    print(json.dumps(recon, indent=2, default=str))

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE — All synthetic, no real money involved")
    print("=" * 60)


if __name__ == "__main__":
    main()
