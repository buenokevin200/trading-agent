"""Incident schema — audit trail for anomalies and events."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
import uuid


class IncidentType(str, Enum):
    EMERGENCY_STOP = "emergency_stop"
    LIMIT_BREACH = "limit_breach"
    DATA_STALE = "data_stale"
    RECONCILIATION = "reconciliation"
    PROTECTION_LOST = "protection_lost"
    MODEL_FAILURE = "model_failure"
    BUDGET_EXHAUSTED = "budget_exhausted"
    DUPLICATE_EXECUTOR = "duplicate_executor"
    PROMPT_INJECTION = "prompt_injection"
    ORDER_DISCREPANCY = "order_discrepancy"
    GENERIC = "generic"


@dataclass(frozen=True)
class Incident:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"inc-{uuid.uuid4().hex[:12]}")
    type: IncidentType = IncidentType.GENERIC
    description: str = ""
    severity: str = "warning"  # info | warning | critical
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.description:
            raise ValueError("Incident description is required")
