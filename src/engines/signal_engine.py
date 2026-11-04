"""Deterministic signal engine — evaluates strategy rules in code, not via model."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from ..schemas.observation import Observation, DataQuality
from ..schemas.signal import Signal, SignalType

logger = logging.getLogger(__name__)


class SignalEngine:
    """
    Deterministic signal engine. Evaluates a versioned strategy's entry/exit
    conditions using code, not model arithmetic. Returns NO_OPERATION when
    strategy is not configured, data is stale, or no condition is met.

    Supported strategies:
      - 'sma_cross': simple moving average crossover (synthetic, for testing)
      - 'none': no strategy active (always NO_OPERATION)
    """

    SUPPORTED_STRATEGIES = {"none", "sma_cross"}
    STRATEGY_VERSION = "1.0"

    def __init__(self, strategy_name: str = "none", strategy_params: dict | None = None):
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params or {}
        self.strategy_version = f"{strategy_name}@{self.STRATEGY_VERSION}"

        if strategy_name not in self.SUPPORTED_STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy_name}")

    def evaluate(self, observations: list[Observation], task_id: str) -> Signal:
        """Evaluate observations and produce a signal."""
        if self.strategy_name == "none":
            return self._no_op(task_id, observations, "No strategy configured")

        if not observations:
            return self._no_op(task_id, [], "No observations provided")

        # Check data quality
        for obs in observations:
            if obs.quality == DataQuality.MISSING:
                return self._no_op(task_id, observations, "Missing data")
            if obs.quality == DataQuality.STALE:
                return self._no_op(task_id, observations, "Stale data")
            if obs.quality == DataQuality.INCONSISTENT:
                return self._no_op(task_id, observations, "Inconsistent data")

        if self.strategy_name == "sma_cross":
            return self._sma_cross(observations, task_id)

        return self._no_op(task_id, observations, "Strategy not implemented")

    def _sma_cross(self, observations: list[Observation], task_id: str) -> Signal:
        """Simple moving average crossover strategy."""
        prices = [o.price for o in observations if o.price is not None]
        if len(prices) < 2:
            return self._no_op(task_id, observations, "Insufficient data for SMA")

        short_window = self.strategy_params.get("short_window", 2)
        long_window = self.strategy_params.get("long_window", 5)

        if len(prices) < long_window:
            return self._no_op(task_id, observations, "Insufficient data for long SMA")

        short_sma = sum(prices[-short_window:]) / short_window
        long_sma = sum(prices[-long_window:]) / long_window

        instrument = observations[-1].instrument
        current_price = prices[-1]
        obs_ids = [o.id for o in observations]

        valid_until = datetime.now(timezone.utc) + timedelta(seconds=60)

        if short_sma > long_sma:
            # Bullish crossover
            return Signal(
                task_id=task_id,
                instrument=instrument,
                signal_type=SignalType.BUY,
                strategy_version=self.strategy_version,
                entry_price=current_price,
                stop_loss=current_price * 0.98,  # 2% stop
                take_profit=current_price * 1.04,  # 4% target
                observation_ids=obs_ids,
                valid_until=valid_until,
                rules_triggered=["sma_cross_bullish"],
            )
        elif short_sma < long_sma:
            # Bearish — but shorts disabled by default, so NO_OPERATION
            return self._no_op(task_id, observations, "Bearish crossover but shorts not enabled")

        return self._no_op(task_id, observations, "No crossover detected")

    def _no_op(self, task_id: str, observations: list[Observation], reason: str) -> Signal:
        instrument = observations[-1].instrument if observations else "UNKNOWN"
        return Signal(
            task_id=task_id,
            instrument=instrument,
            signal_type=SignalType.NO_OPERATION,
            strategy_version=self.strategy_version,
            observation_ids=[o.id for o in observations],
            invalidation_reason=reason,
        )
