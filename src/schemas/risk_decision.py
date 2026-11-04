"""Risk decision schema — output of the deterministic risk engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class RiskRejectionCode(str, Enum):
    LIMITS_NOT_CONFIGURED = "R001"
    EXCEEDS_RISK_PER_TRADE = "R002"
    EXCEEDS_MAX_EXPOSURE = "R003"
    EXCEEDS_DAILY_LOSS = "R004"
    EXCEEDS_DRAWDOWN = "R005"
    EXCEEDS_MAX_POSITIONS = "R006"
    EXCEEDS_ORDER_FREQUENCY = "R007"
    EXCEEDS_PENDING_ORDERS = "R008"
    STALE_DATA = "R009"
    INCONSISTENT_DATA = "R010"
    INSTRUMENT_NOT_ALLOWED = "R011"
    LEVERAGE_NOT_ENABLED = "R012"
    SHORT_NOT_ENABLED = "R013"
    NO_AUTHORIZATION = "R014"
    AUTHORIZATION_EXPIRED = "R015"
    AUTHORIZATION_REUSED = "R016"
    PARAMETERS_ALTERED = "R017"
    EMERGENCY_STOP_ACTIVE = "R018"
    INSUFFICIENT_LIQUIDITY = "R019"
    ANOMALOUS_PRICE = "R020"


@dataclass(frozen=True)
class RiskDecision:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"risk-{uuid.uuid4().hex[:12]}")
    signal_id: str = ""
    approved: bool = False
    rejection_code: Optional[RiskRejectionCode] = None
    rejection_reason: Optional[str] = None
    # calculated values
    risk_amount: Optional[float] = None  # in account currency
    risk_percentage: Optional[float] = None
    exposure_after: Optional[float] = None
    # authorization reference (if approved)
    authorization_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.signal_id:
            raise ValueError("RiskDecision must reference a signal_id")
        if not self.approved and not self.rejection_code:
            raise ValueError("Rejected decision must have a rejection_code")
        if self.approved and not self.authorization_id:
            raise ValueError("Approved decision must have an authorization_id")
