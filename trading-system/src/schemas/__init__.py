"""Internal versioned data schemas for the synthetic multi-agent trading system.

SIMULATION ONLY — NO REAL BROKER — NO REAL CREDENTIALS.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Observation:
    instrument: str
    price: float
    bid: float
    ask: float
    volume: float
    observed_at: str = field(default_factory=utc_now_iso)
    received_at: str = field(default_factory=utc_now_iso)
    quality: str = "SYNTHETIC_OK"
    source: str = "LOCAL_SYNTHETIC_SIMULATOR"
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Signal:
    signal_id: str
    task_id: str
    instrument: str
    signal_type: str  # "BUY" | "SELL" | "NO_OPERATION"
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    rules_triggered: List[str] = field(default_factory=list)
    strategy_version: str = "SMA_CROSS_v1.0"
    timestamp: str = field(default_factory=utc_now_iso)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskDecision:
    decision_id: str
    signal_id: str
    instrument: str
    approved: bool
    rejection_code: Optional[str] = None
    rejection_reason: Optional[str] = None
    approved_quantity: float = 0.0
    risk_amount: float = 0.0
    timestamp: str = field(default_factory=utc_now_iso)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Authorization:
    auth_id: str
    decision_id: str
    instrument: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    issued_at: str = field(default_factory=utc_now_iso)
    used: bool = False
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Intent:
    intent_id: str
    auth_id: str
    instrument: str
    side: str  # "BUY" | "SELL"
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    created_at: str = field(default_factory=utc_now_iso)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrderEvent:
    order_id: str
    instrument: str
    side: str  # "BUY" | "SELL"
    quantity: float
    status: str  # "filled" | "rejected" | "pending"
    fill_price: float
    commission: float
    timestamp: str = field(default_factory=utc_now_iso)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: Optional[str] = None
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Position:
    instrument: str
    side: str  # "LONG" | "SHORT"
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    is_protected: bool = True
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: str = field(default_factory=utc_now_iso)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Incident:
    incident_id: str
    severity: str
    code: str
    description: str
    timestamp: str = field(default_factory=utc_now_iso)
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
