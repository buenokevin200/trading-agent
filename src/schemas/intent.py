"""Intent schema — what the executor sends to the execution service."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class IntentType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


@dataclass(frozen=True)
class Intent:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"intent-{uuid.uuid4().hex[:12]}")
    authorization_id: str = ""
    signal_id: str = ""
    instrument: str = ""
    intent_type: IntentType = IntentType.BUY
    quantity: float = 0.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    mode: str = "simulation"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.authorization_id:
            raise ValueError("Intent must reference an authorization_id")
        if not self.instrument:
            raise ValueError("Intent must reference an instrument")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
