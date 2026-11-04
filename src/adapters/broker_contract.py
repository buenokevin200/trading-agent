"""Broker adapter contract — interface for future verified broker integration.

This is a CONTRACT/INTERFACE only. No real broker is connected.
Any future implementation must implement this interface and be verified
before activation. The simulator satisfies this contract for simulation mode.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass

from ..schemas.intent import Intent
from ..schemas.order_event import OrderEvent


class BrokerMode(str, Enum):
    SIMULATION = "simulation"
    PAPER = "paper"
    REAL = "real"


@dataclass
class BrokerConfig:
    """Configuration for a broker adapter."""
    mode: BrokerMode = BrokerMode.SIMULATION
    api_key: str = ""  # NEVER stored in code/SOUL/memory — only in isolated service
    api_secret: str = ""
    base_url: str = ""
    # Restrictions
    allow_withdrawals: bool = False
    allow_transfers: bool = False
    # Rate limits
    max_requests_per_second: int = 10
    # Timeout
    timeout_seconds: int = 30


class BrokerAdapter(ABC):
    """
    Abstract broker adapter. Any future broker integration must implement
    this interface. The simulator is the only implementation for now.

    CONTRACT REQUIREMENTS:
    - All methods must be idempotent where noted.
    - Secrets must never leave the service (not in return values, logs, or exceptions).
    - Mode must be explicitly SIMULATION for all testing.
    - REAL mode requires explicit human approval and is NOT activated in this project.
    """

    @abstractmethod
    def submit_order(self, intent: Intent) -> OrderEvent:
        """Submit an order. Must be idempotent (same intent_id = same order)."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True if cancelled."""
        ...

    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[OrderEvent]:
        """Get current order status from broker."""
        ...

    @abstractmethod
    def get_positions(self) -> list:
        """Get current positions from broker."""
        ...

    @abstractmethod
    def reconcile(self) -> dict:
        """Reconcile local state with broker state."""
        ...

    @property
    @abstractmethod
    def mode(self) -> BrokerMode:
        """Current operating mode."""
        ...
