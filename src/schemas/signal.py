"""Signal schema — output of the deterministic signal engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class SignalType(str, Enum):
    NO_OPERATION = "NO_OPERATION"
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


@dataclass(frozen=True)
class Signal:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"sig-{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    instrument: str = ""
    signal_type: SignalType = SignalType.NO_OPERATION
    strategy_version: str = "none"
    # entry/exit levels
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    # data references
    observation_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # validity
    valid_until: Optional[datetime] = None
    invalidation_reason: Optional[str] = None
    # rules activated
    rules_triggered: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.task_id:
            raise ValueError("Signal must reference a task_id")
        if not self.instrument:
            raise ValueError("Signal must reference an instrument")

    @property
    def is_no_op(self) -> bool:
        return self.signal_type == SignalType.NO_OPERATION

    @property
    def is_expired(self) -> bool:
        if self.valid_until is None:
            return False
        return datetime.now(timezone.utc) > self.valid_until
