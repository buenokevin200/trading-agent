"""Synthetic market data adapter (SIMULATION ONLY)."""
from __future__ import annotations

import math
import random
from typing import Dict, List
from schemas import Observation, utc_now_iso


class DataAdapter:
    """Generates synthetic price observations with realistic cyclical dynamics for SMA crossover testing."""

    BASE_PRICES: Dict[str, float] = {
        "SYNTH/BTC": 68400.0,
        "SYNTH/ETH": 3480.0,
    }

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._step: Dict[str, int] = {"SYNTH/BTC": 0, "SYNTH/ETH": 0}
        self._prices: Dict[str, float] = dict(self.BASE_PRICES)
        self._history: Dict[str, List[Observation]] = {"SYNTH/BTC": [], "SYNTH/ETH": []}
        # Pre-seed history so SMA cross is warm immediately
        for inst in self.BASE_PRICES:
            for _ in range(15):
                self.fetch(inst)

    def fetch(self, instrument: str = "SYNTH/BTC") -> Observation:
        if instrument not in self._prices:
            self._prices[instrument] = 1000.0
            self._step[instrument] = 0
            self._history[instrument] = []

        self._step[instrument] += 1
        t = self._step[instrument]
        current = self._prices[instrument]
        base = self.BASE_PRICES.get(instrument, 1000.0)

        # Combine a smooth cycle wave + random noise + slight mean reversion so SMA crossovers happen regularly
        wave = math.sin(t * 0.48) * 0.0045 + math.cos(t * 0.21) * 0.0025
        noise = self._rng.gauss(0, 0.0018)
        reversion = (base - current) / base * 0.08
        pct_move = wave + noise + reversion

        new_price = round(max(base * 0.5, current * (1.0 + pct_move)), 2)
        self._prices[instrument] = new_price

        spread_pct = 0.0004  # 4 bps synthetic spread
        half_spread = max(0.01, new_price * spread_pct / 2.0)
        bid = round(new_price - half_spread, 2)
        ask = round(new_price + half_spread, 2)
        volume = round(self._rng.uniform(12.5, 165.0) * (1.0 + abs(pct_move) * 80.0), 2)

        obs = Observation(
            instrument=instrument,
            price=new_price,
            bid=bid,
            ask=ask,
            volume=volume,
            observed_at=utc_now_iso(),
            received_at=utc_now_iso(),
            quality="SYNTHETIC_OK",
        )
        hist = self._history.setdefault(instrument, [])
        hist.append(obs)
        if len(hist) > 200:
            del hist[:-200]
        return obs

    def get_history(self, instrument: str = "SYNTH/BTC", limit: int = 30) -> List[Observation]:
        hist = self._history.get(instrument, [])
        return list(hist[-limit:])
