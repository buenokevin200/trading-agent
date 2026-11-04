"""Observation schema — market data with provenance."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
import uuid


class DataQuality(str, Enum):
    GOOD = "good"
    STALE = "stale"
    PARTIAL = "partial"
    INCONSISTENT = "inconsistent"
    MISSING = "missing"


@dataclass(frozen=True)
class Observation:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"obs-{uuid.uuid4().hex[:12]}")
    instrument: str = ""  # e.g. "SYNTH/BTC"
    source: str = ""  # e.g. "synthetic-feed"
    # timestamps in UTC
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timezone_str: str = "UTC"
    # data payload
    price: Optional[float] = None
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    quality: DataQuality = DataQuality.GOOD

    def __post_init__(self):
        if not self.instrument:
            raise ValueError("Instrument is required")
        if not self.source:
            raise ValueError("Source is required")
        if self.price is not None and self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")
        if self.price is None and self.bid is None and self.ask is None:
            raise ValueError("At least one of price/bid/ask must be present")

    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.observed_at).total_seconds()
