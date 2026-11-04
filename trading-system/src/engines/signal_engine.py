"""Deterministic SMA Crossover Signal Engine (SIMULATION ONLY)."""
from __future__ import annotations

from typing import List
from schemas import Observation, Signal, new_id, utc_now_iso


class SignalEngine:
    """Evaluates synthetic observations using fast/slow Simple Moving Average crossover."""

    def __init__(
        self,
        fast_window: int = 4,
        slow_window: int = 9,
        sl_pct: float = 0.008,
        tp_pct: float = 0.016,
    ) -> None:
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct

    def evaluate(self, observations: List[Observation], task_id: str = "task_auto") -> Signal:
        if not observations:
            return Signal(
                signal_id=new_id("sig"),
                task_id=task_id,
                instrument="SYNTH/BTC",
                signal_type="NO_OPERATION",
                entry_price=0.0,
                stop_loss=None,
                take_profit=None,
                rules_triggered=["INSUFFICIENT_OBSERVATIONS"],
                timestamp=utc_now_iso(),
            )

        latest = observations[-1]
        instrument = latest.instrument
        price = latest.price

        if len(observations) < self.slow_window + 1:
            return Signal(
                signal_id=new_id("sig"),
                task_id=task_id,
                instrument=instrument,
                signal_type="NO_OPERATION",
                entry_price=price,
                stop_loss=None,
                take_profit=None,
                rules_triggered=[f"WARMUP_{len(observations)}_OF_{self.slow_window + 1}"],
                timestamp=utc_now_iso(),
            )

        prices = [o.price for o in observations]
        fast_curr = sum(prices[-self.fast_window :]) / self.fast_window
        slow_curr = sum(prices[-self.slow_window :]) / self.slow_window
        fast_prev = sum(prices[-self.fast_window - 1 : -1]) / self.fast_window
        slow_prev = sum(prices[-self.slow_window - 1 : -1]) / self.slow_window

        momentum = (prices[-1] - prices[-3]) / prices[-3] if len(prices) >= 3 else 0.0

        # Crossover or strong momentum separation after crossover
        bullish_cross = fast_prev <= slow_prev and fast_curr > slow_curr
        bearish_cross = fast_prev >= slow_prev and fast_curr < slow_curr
        bullish_impulse = fast_curr > slow_curr and momentum > 0.0022
        bearish_impulse = fast_curr < slow_curr and momentum < -0.0022

        if bullish_cross or bullish_impulse:
            sl = round(price * (1.0 - self.sl_pct), 2)
            tp = round(price * (1.0 + self.tp_pct), 2)
            rules = ["SMA_FAST_ABOVE_SLOW"]
            if bullish_cross:
                rules.append("GOLDEN_CROSS_TRIGGER")
            else:
                rules.append("BULLISH_MOMENTUM_CONTINUATION")
            rules.append("RR_RATIO_2.0")
            return Signal(
                signal_id=new_id("sig"),
                task_id=task_id,
                instrument=instrument,
                signal_type="BUY",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                rules_triggered=rules,
                timestamp=utc_now_iso(),
            )

        if bearish_cross or bearish_impulse:
            sl = round(price * (1.0 + self.sl_pct), 2)
            tp = round(price * (1.0 - self.tp_pct), 2)
            rules = ["SMA_FAST_BELOW_SLOW"]
            if bearish_cross:
                rules.append("DEATH_CROSS_TRIGGER")
            else:
                rules.append("BEARISH_MOMENTUM_CONTINUATION")
            rules.append("RR_RATIO_2.0")
            return Signal(
                signal_id=new_id("sig"),
                task_id=task_id,
                instrument=instrument,
                signal_type="SELL",
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                rules_triggered=rules,
                timestamp=utc_now_iso(),
            )

        return Signal(
            signal_id=new_id("sig"),
            task_id=task_id,
            instrument=instrument,
            signal_type="NO_OPERATION",
            entry_price=price,
            stop_loss=round(price * (1.0 - self.sl_pct), 2),
            take_profit=round(price * (1.0 + self.tp_pct), 2),
            rules_triggered=["NO_SMA_CROSSOVER", f"SMA{self.fast_window}_{fast_curr:.1f}_VS_SMA{self.slow_window}_{slow_curr:.1f}"],
            timestamp=utc_now_iso(),
        )
