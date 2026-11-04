"""Data adapter — synthetic feed with provenance and timestamps."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import random

from ..schemas.observation import Observation, DataQuality

logger = logging.getLogger(__name__)


class DataAdapter:
    """
    Synthetic data adapter. Generates price observations with full provenance.
    This is NOT real market data — it is explicitly synthetic for simulation.
    """

    def __init__(self, instruments: set[str] | None = None, seed: int = 42):
        self.instruments = instruments or {"SYNTH/BTC", "SYNTH/ETH"}
        self._prices: dict[str, float] = {}
        self._rng = random.Random(seed)
        self._source = "synthetic-feed"
        # Initialize prices
        for inst in self.instruments:
            self._prices[inst] = 100.0 + self._rng.uniform(-10, 10)

    def set_instruments(self, instruments: set[str]):
        self.instruments = instruments
        for inst in instruments:
            if inst not in self._prices:
                self._prices[inst] = 100.0 + self._rng.uniform(-10, 10)

    def fetch(self, instrument: str, max_age_sec: int = 60) -> Observation:
        """Fetch a single observation for an instrument."""
        if instrument not in self.instruments:
            return Observation(
                instrument=instrument,
                source=self._source,
                price=None,
                bid=None,
                ask=None,
                quality=DataQuality.MISSING,
                metadata={"error": "Instrument not in allowlist"},
            )

        # Random walk
        old_price = self._prices[instrument]
        change = self._rng.gauss(0, 0.5)
        new_price = max(0.01, old_price + change)
        self._prices[instrument] = new_price

        now = datetime.now(timezone.utc)
        obs = Observation(
            instrument=instrument,
            source=self._source,
            observed_at=now,
            received_at=now,
            timezone_str="UTC",
            price=new_price,
            bid=new_price * 0.999,
            ask=new_price * 1.001,
            volume=self._rng.uniform(100, 1000),
            quality=DataQuality.GOOD,
            metadata={"synthetic": True, "seed_price": old_price},
        )
        logger.debug(f"DataAdapter: {instrument} @ {new_price:.4f} (synthetic)")
        return obs

    def fetch_batch(self, instruments: set[str] | None = None) -> list[Observation]:
        """Fetch observations for all (or specified) instruments."""
        targets = instruments or self.instruments
        return [self.fetch(inst) for inst in targets]

    def fetch_stale(self, instrument: str, age_seconds: int = 120) -> Observation:
        """Generate a deliberately stale observation (for testing)."""
        obs = self.fetch(instrument)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
        return Observation(
            instrument=obs.instrument,
            source=obs.source,
            observed_at=old_time,
            received_at=datetime.now(timezone.utc),
            price=obs.price,
            bid=obs.bid,
            ask=obs.ask,
            volume=obs.volume,
            quality=DataQuality.STALE,
            metadata={"synthetic": True, "deliberately_stale": True},
        )

    def fetch_inconsistent(self, instrument: str) -> Observation:
        """Generate a deliberately inconsistent observation (for testing)."""
        return Observation(
            instrument=instrument,
            source=self._source,
            price=999999.0,  # anomalous
            bid=1.0,  # inconsistent with price
            ask=2.0,
            quality=DataQuality.INCONSISTENT,
            metadata={"synthetic": True, "deliberately_inconsistent": True},
        )
