"""Order event schema — lifecycle of an order in the simulator."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class OrderStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class OrderFill:
    filled_qty: float
    filled_price: float
    commission: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OrderEvent:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"order-{uuid.uuid4().hex[:12]}")
    intent_id: str = ""
    instrument: str = ""
    side: str = ""  # BUY | SELL | CLOSE
    quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    fills: list[OrderFill] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.intent_id:
            raise ValueError("OrderEvent must reference an intent_id")
        if not self.instrument:
            raise ValueError("OrderEvent must reference an instrument")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

    @property
    def filled_quantity(self) -> float:
        return sum(f.filled_qty for f in self.fills)

    @property
    def avg_fill_price(self) -> Optional[float]:
        total = sum(f.filled_qty * f.filled_price for f in self.fills)
        qty = self.filled_quantity
        return total / qty if qty > 0 else None

    @property
    def total_commission(self) -> float:
        return sum(f.commission for f in self.fills)
