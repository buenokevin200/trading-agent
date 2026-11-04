"""Authorization schema — single-use, parameter-bound, expiring."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid


@dataclass(frozen=True)
class Authorization:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"auth-{uuid.uuid4().hex[:12]}")
    risk_decision_id: str = ""
    signal_id: str = ""
    # bound parameters — must match exactly on use
    instrument: str = ""
    intent_type: str = ""  # BUY | SELL | CLOSE
    quantity: float = 0.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    # lifecycle
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=30)
    )
    used: bool = False
    used_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.risk_decision_id:
            raise ValueError("Authorization must reference a risk_decision_id")
        if not self.signal_id:
            raise ValueError("Authorization must reference a signal_id")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired
