"""Background cycle loop, Binance balance broadcaster, and state adapter.

SIMULATION & PAPER TESTNET ONLY — NO REAL BROKER — NO CREDENTIALS IN CODE.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional

from binance_service import BinanceBalanceService
from ws_manager import WebSocketManager


def _resolve_trading_system_src() -> Path:
    env_path = os.getenv("TRADING_SYSTEM_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path) / "src")
        candidates.append(Path(env_path))
    candidates.extend(
        [
            Path("/home/champa/trading-system/src"),
            Path(__file__).resolve().parents[1] / "trading-system" / "src",
        ]
    )
    for cand in candidates:
        if cand.exists() and (cand / "orchestrator.py").exists():
            return cand
    return Path(__file__).resolve().parents[1] / "trading-system" / "src"


TRADING_SRC_PATH = _resolve_trading_system_src()
if str(TRADING_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(TRADING_SRC_PATH))

from orchestrator import Orchestrator  # noqa: E402


def _to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return obj


class CycleRunner:
    def __init__(self, ws_manager: WebSocketManager, frequency_sec: float = 5.0) -> None:
        self.ws_manager = ws_manager
        self.frequency_sec: float = max(1.0, min(60.0, float(frequency_sec)))
        self.active_instrument: str = "SYNTH/BTC"
        self.orch = Orchestrator()
        self.binance = BinanceBalanceService(
            default_reference_capital=float(
                getattr(self.orch.risk_engine, "reference_capital", 10000.0)
            )
        )
        self._task: Optional[asyncio.Task] = None
        self._balance_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._lock = asyncio.Lock()
        self._rng = random.Random(101)

        # Monotonic chart time cursor per instrument (Unix seconds) for lightweight-charts
        now_sec = int(time.time()) - 3600
        self._last_chart_time: Dict[str, int] = {
            "SYNTH/BTC": now_sec,
            "SYNTH/ETH": now_sec,
        }
        self.candles: Dict[str, List[Dict[str, Any]]] = {
            "SYNTH/BTC": [],
            "SYNTH/ETH": [],
        }
        self.signals: List[Dict[str, Any]] = []
        self.risk_decisions: List[Dict[str, Any]] = []
        self.orders: List[Dict[str, Any]] = []

        self._bootstrap_history()

    def _next_chart_time(self, instrument: str) -> int:
        prev = self._last_chart_time.get(instrument, int(time.time()) - 600)
        now_sec = int(time.time())
        nxt = max(now_sec, prev + 60)
        self._last_chart_time[instrument] = nxt
        return nxt

    def _build_candle(self, instrument: str, obs: Dict[str, Any]) -> Dict[str, Any]:
        close_price = float(obs.get("price", 0.0))
        prev_candles = self.candles.setdefault(instrument, [])
        open_price = float(prev_candles[-1]["close"]) if prev_candles else round(
            close_price * (1.0 + self._rng.uniform(-0.002, 0.002)), 2
        )
        wick_up = abs(close_price - open_price) * self._rng.uniform(0.35, 1.1) + close_price * 0.0008
        wick_dn = abs(close_price - open_price) * self._rng.uniform(0.35, 1.1) + close_price * 0.0008
        high_price = round(max(open_price, close_price) + wick_up, 2)
        low_price = round(min(open_price, close_price) - wick_dn, 2)
        chart_time = self._next_chart_time(instrument)

        candle = {
            "time": chart_time,
            "open": round(open_price, 2),
            "high": high_price,
            "low": low_price,
            "close": round(close_price, 2),
            "volume": float(obs.get("volume", 25.0)),
        }
        prev_candles.append(candle)
        if len(prev_candles) > 300:
            del prev_candles[:-300]
        return candle

    def _bootstrap_history(self) -> None:
        """Seed initial synthetic candles and warm-up cycles for both instruments."""
        for inst in ("SYNTH/BTC", "SYNTH/ETH"):
            hist = []
            if hasattr(self.orch, "data") and hasattr(self.orch.data, "get_history"):
                hist = [_to_dict(x) for x in self.orch.data.get_history(inst, limit=25)]
            for obs in hist:
                self._build_candle(inst, obs)

        for inst in ("SYNTH/BTC", "SYNTH/BTC", "SYNTH/ETH", "SYNTH/BTC", "SYNTH/BTC", "SYNTH/ETH"):
            self._execute_cycle_sync(inst)

    def _execute_cycle_sync(self, instrument: str) -> Dict[str, Any]:
        result = self.orch.run_cycle(instrument=instrument)
        obs = _to_dict(result.get("observation")) or {}
        candle = self._build_candle(instrument, obs)

        sig = _to_dict(result.get("signal"))
        if sig:
            sig["chart_time"] = candle["time"]
            self.signals.append(sig)
            if len(self.signals) > 100:
                del self.signals[:-100]

        risk_dec = _to_dict(result.get("risk_decision"))
        if risk_dec:
            self.risk_decisions.append(risk_dec)
            if len(self.risk_decisions) > 100:
                del self.risk_decisions[:-100]

        order_ev = _to_dict(result.get("order"))
        if order_ev:
            self.orders.append(order_ev)
            if len(self.orders) > 200:
                del self.orders[:-200]

        result["candle"] = candle
        return result

    def get_balance(self) -> Dict[str, Any]:
        positions = self.get_positions()
        status = self.get_status()
        ref_cap = status.get("risk_limits", {}).get("reference_capital", 100000.0)
        return self.binance.get_balance(
            positions=positions,
            realized_pnl=status.get("realized_pnl", 0.0),
            config_reference_capital=ref_cap,
        )

    async def broadcast_balance(self) -> Dict[str, Any]:
        bal = self.get_balance()
        await self.ws_manager.broadcast("balance_update", bal)
        return bal

    async def execute_and_broadcast_cycle(self, instrument: Optional[str] = None) -> Dict[str, Any]:
        target_instrument = instrument or self.active_instrument
        async with self._lock:
            result = self._execute_cycle_sync(target_instrument)

        obs = _to_dict(result.get("observation")) or {}
        candle = result.get("candle")
        sig = _to_dict(result.get("signal"))
        risk_dec = _to_dict(result.get("risk_decision"))
        order_ev = _to_dict(result.get("order"))
        positions_payload = self.get_positions()
        status_payload = self.get_status()
        audit_payload = self.get_audit(limit=25)
        balance_payload = self.get_balance()

        # 1. price_update
        await self.ws_manager.broadcast(
            "price_update",
            {
                "instrument": target_instrument,
                "price": obs.get("price"),
                "bid": obs.get("bid"),
                "ask": obs.get("ask"),
                "volume": obs.get("volume"),
                "timestamp": obs.get("observed_at") or datetime.now(timezone.utc).isoformat(),
                "candle": candle,
            },
        )

        # 2. signal
        if sig:
            await self.ws_manager.broadcast(
                "signal",
                {
                    "signal_id": sig.get("signal_id"),
                    "signal_type": sig.get("signal_type"),
                    "instrument": sig.get("instrument", target_instrument),
                    "entry_price": sig.get("entry_price"),
                    "stop_loss": sig.get("stop_loss"),
                    "take_profit": sig.get("take_profit"),
                    "rules_triggered": sig.get("rules_triggered", []),
                    "timestamp": sig.get("timestamp"),
                    "chart_time": sig.get("chart_time"),
                },
            )

        # 3. risk_decision
        if risk_dec:
            await self.ws_manager.broadcast(
                "risk_decision",
                {
                    "decision_id": risk_dec.get("decision_id"),
                    "signal_id": risk_dec.get("signal_id"),
                    "instrument": risk_dec.get("instrument", target_instrument),
                    "approved": risk_dec.get("approved"),
                    "rejection_code": risk_dec.get("rejection_code"),
                    "rejection_reason": risk_dec.get("rejection_reason"),
                    "approved_quantity": risk_dec.get("approved_quantity", 0.0),
                    "risk_amount": risk_dec.get("risk_amount", 0.0),
                    "timestamp": risk_dec.get("timestamp"),
                },
            )

        # 4. order_fill
        if order_ev:
            await self.ws_manager.broadcast(
                "order_fill",
                {
                    "order_id": order_ev.get("order_id"),
                    "instrument": order_ev.get("instrument", target_instrument),
                    "side": order_ev.get("side"),
                    "quantity": order_ev.get("quantity"),
                    "fill_price": order_ev.get("fill_price"),
                    "commission": order_ev.get("commission"),
                    "status": order_ev.get("status"),
                    "reason": order_ev.get("reason"),
                    "timestamp": order_ev.get("timestamp"),
                },
            )

        # 5. position_update
        await self.ws_manager.broadcast(
            "position_update",
            {
                "positions": positions_payload,
                "realized_pnl": status_payload.get("realized_pnl", 0.0),
                "unrealized_pnl": status_payload.get("unrealized_pnl", 0.0),
                "total_pnl": status_payload.get("total_pnl", 0.0),
            },
        )

        # 6. balance_update
        await self.ws_manager.broadcast("balance_update", balance_payload)

        # 7. cycle_complete
        await self.ws_manager.broadcast(
            "cycle_complete",
            {
                "cycle_count": status_payload.get("cycle_count"),
                "instrument": target_instrument,
                "status": status_payload,
                "audit": audit_payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return result

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        self._balance_task = asyncio.create_task(self._balance_loop())

    async def stop(self) -> None:
        self._running = False
        for t in (self._task, self._balance_task):
            if t:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass

    async def _loop(self) -> None:
        while self._running:
            try:
                status = self.orch.get_status()
                if not status.get("paused", False) and not status.get("emergency_stop", False):
                    await self.execute_and_broadcast_cycle(self.active_instrument)
            except Exception as exc:
                print(f"[CycleRunner] Error in cycle loop: {exc}")
            await asyncio.sleep(self.frequency_sec)

    async def _balance_loop(self) -> None:
        """Broadcasts balance every 5 seconds via WebSocket as required by SPEC-002."""
        while self._running:
            try:
                await self.broadcast_balance()
            except Exception as exc:
                print(f"[CycleRunner] Error in balance loop: {exc}")
            await asyncio.sleep(max(1, self.binance.refresh_sec))

    def get_status(self) -> Dict[str, Any]:
        raw = _to_dict(self.orch.get_status()) or {}
        positions = self.get_positions()
        realized = float(raw.get("realized_pnl", getattr(self.orch.sim, "realized_pnl", 0.0)))
        unrealized = round(sum(float(p.get("unrealized_pnl", 0.0)) for p in positions), 2)
        risk_limits = raw.get("risk_limits")
        if not risk_limits and hasattr(self.orch, "risk_engine") and hasattr(self.orch.risk_engine, "get_limits"):
            risk_limits = self.orch.risk_engine.get_limits()
        if not risk_limits:
            risk_limits = {
                "reference_capital": 100000.0,
                "risk_per_trade": 0.01,
                "max_exposure": 0.50,
                "max_daily_loss": 0.03,
                "max_drawdown": 0.06,
                "max_positions": 4,
            }

        return {
            "mode": self.binance.mode.upper(),
            "system_source": str(TRADING_SRC_PATH),
            "cycle_count": int(raw.get("cycle_count", getattr(self.orch, "cycle_count", 0))),
            "paused": bool(raw.get("paused", getattr(self.orch, "paused", False))),
            "emergency_stop": bool(raw.get("emergency_stop", getattr(self.orch, "emergency_stop", False))),
            "limits_configured": bool(raw.get("limits_configured", getattr(self.orch, "limits_configured", True))),
            "active_instrument": self.active_instrument,
            "cycle_frequency_sec": self.frequency_sec,
            "positions": positions,
            "realized_pnl": round(realized, 2),
            "unrealized_pnl": unrealized,
            "total_pnl": round(realized + unrealized, 2),
            "total_orders": len(self.get_orders()),
            "risk_limits": risk_limits,
            "last_risk_decision": self.risk_decisions[-1] if self.risk_decisions else None,
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        sim = getattr(self.orch, "sim", None) or getattr(self.orch, "simulator", None)
        if sim is not None and hasattr(sim, "positions"):
            return [_to_dict(p) for p in sim.positions]
        status = _to_dict(self.orch.get_status()) or {}
        return [_to_dict(p) for p in status.get("positions", [])]

    def get_orders(self) -> List[Dict[str, Any]]:
        sim = getattr(self.orch, "sim", None) or getattr(self.orch, "simulator", None)
        if sim is not None and hasattr(sim, "orders"):
            return list(reversed([_to_dict(o) for o in sim.orders]))
        return list(reversed(self.orders))

    def get_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.signals[-limit:]))

    def get_audit(self, limit: int = 25) -> List[Dict[str, Any]]:
        audit_svc = getattr(self.orch, "audit", None)
        if audit_svc is not None and hasattr(audit_svc, "read_all"):
            entries = audit_svc.read_all()
            return list(reversed(entries[-limit:]))
        return []

    def get_candles(self, instrument: str = "SYNTH/BTC", limit: int = 120) -> List[Dict[str, Any]]:
        return list(self.candles.get(instrument, [])[-limit:])
