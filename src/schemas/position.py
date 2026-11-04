"""Position schema — current open positions."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class Position:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"pos-{uuid.uuid4().hex[:12]}")
    instrument: str = ""
    side: str = ""  # LONG | SHORT
    quantity: float = 0.0
    entry_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    order_id: str = ""
    # unrealized PnL
    current_price: Optional[float] = None

    def __post_init__(self):
        if not self.instrument:
            raise ValueError("Position must reference an instrument")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

    @property
    def unrealized_pnl(self) -> Optional[float]:
        if self.current_price is None:
            return None
        if self.side == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        elif self.side == "SHORT":
            return (self.entry_price - self.current_price) * self.quantity
        return None

    @property
    def is_protected(self) -> bool:
        return self.stop_loss is not None
