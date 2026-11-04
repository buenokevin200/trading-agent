"""Deterministic risk engine — enforces limits in code, independent of model."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import logging
import uuid

from ..schemas.signal import Signal, SignalType
from ..schemas.risk_decision import RiskDecision, RiskRejectionCode
from ..schemas.authorization import Authorization
from ..schemas.observation import Observation, DataQuality
from ..schemas.position import Position

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Risk configuration — all fields must be explicitly set."""
    # Instrument allowlist
    allowed_instruments: set[str] = field(default_factory=set)
    # Limits (None = not configured, which blocks all new exposure)
    risk_per_trade_pct: Optional[float] = None  # % of capital per trade
    max_exposure_pct: Optional[float] = None  # max total exposure % of capital
    max_daily_loss_pct: Optional[float] = None  # max daily loss %
    max_drawdown_pct: Optional[float] = None  # max drawdown %
    max_positions: Optional[int] = None  # max concurrent positions
    max_order_frequency_sec: Optional[int] = None  # min seconds between orders
    max_pending_orders: Optional[int] = None  # max pending orders
    # Feature flags
    leverage_enabled: bool = False
    shorts_enabled: bool = False
    # Capital
    reference_capital: Optional[float] = None
    # Emergency stop
    emergency_stop_active: bool = False
    # Data freshness
    max_data_age_sec: Optional[int] = None  # max allowed data age

    def is_configured(self) -> bool:
        """Check if all required limits are configured."""
        return all(v is not None for v in [
            self.risk_per_trade_pct,
            self.max_exposure_pct,
            self.max_daily_loss_pct,
            self.max_drawdown_pct,
            self.max_positions,
            self.max_order_frequency_sec,
            self.max_pending_orders,
            self.reference_capital,
        ]) and len(self.allowed_instruments) > 0


@dataclass
class RiskLimits:
    """Current runtime state for risk evaluation."""
    config: RiskConfig = field(default_factory=RiskConfig)
    open_positions: list[Position] = field(default_factory=list)
    pending_orders: int = 0
    daily_realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    peak_capital: float = 0.0
    last_order_time: Optional[datetime] = None
    # Track used authorizations to prevent reuse
    used_authorization_ids: set[str] = field(default_factory=set)


class RiskEngine:
    """
    Deterministic risk engine. Evaluates proposals against configured limits.
    Returns RiskDecision with approval or rejection + code.
    Does NOT depend on model output for limit enforcement.
    """

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self._issued_authorizations: set[str] = set()  # track issued auth IDs

    def evaluate(self, signal: Signal, observations: list[Observation] | None = None) -> RiskDecision:
        """Evaluate a signal against risk limits."""
        cfg = self.limits.config

        # 1. NO_OPERATION signals are always "approved" (no action needed)
        #    This takes priority over emergency stop — surveillance continues.
        if signal.is_no_op:
            return RiskDecision(
                signal_id=signal.id,
                approved=True,
                authorization_id=f"auth-noop-{uuid.uuid4().hex[:8]}",
            )

        # 2. Emergency stop
        if cfg.emergency_stop_active:
            return self._reject(signal, RiskRejectionCode.EMERGENCY_STOP_ACTIVE,
                              "Emergency stop is active — no new exposures")

        # 3. Limits must be configured
        if not cfg.is_configured():
            return self._reject(signal, RiskRejectionCode.LIMITS_NOT_CONFIGURED,
                              "Risk limits not fully configured")

        # 4. Instrument allowlist
        if signal.instrument not in cfg.allowed_instruments:
            return self._reject(signal, RiskRejectionCode.INSTRUMENT_NOT_ALLOWED,
                              f"Instrument {signal.instrument} not in allowlist")

        # 5. Shorts check
        if signal.signal_type == SignalType.SELL and not cfg.shorts_enabled:
            return self._reject(signal, RiskRejectionCode.SHORT_NOT_ENABLED,
                              "Short positions not enabled")

        # 6. Data freshness
        if observations and cfg.max_data_age_sec is not None:
            for obs in observations:
                if obs.quality in (DataQuality.STALE, DataQuality.MISSING, DataQuality.INCONSISTENT):
                    return self._reject(signal, RiskRejectionCode.STALE_DATA,
                                      f"Data quality issue: {obs.quality.value} for {obs.instrument}")
                if obs.age_seconds > cfg.max_data_age_sec:
                    return self._reject(signal, RiskRejectionCode.STALE_DATA,
                                      f"Data age {obs.age_seconds:.0f}s exceeds max {cfg.max_data_age_sec}s")

        # 7. Max positions
        if len(self.limits.open_positions) >= cfg.max_positions:
            return self._reject(signal, RiskRejectionCode.EXCEEDS_MAX_POSITIONS,
                              f"Max positions ({cfg.max_positions}) reached")

        # 8. Max pending orders
        if self.limits.pending_orders >= cfg.max_pending_orders:
            return self._reject(signal, RiskRejectionCode.EXCEEDS_PENDING_ORDERS,
                              f"Max pending orders ({cfg.max_pending_orders}) reached")

        # 9. Order frequency
        if self.limits.last_order_time and cfg.max_order_frequency_sec:
            elapsed = (datetime.now(timezone.utc) - self.limits.last_order_time).total_seconds()
            if elapsed < cfg.max_order_frequency_sec:
                return self._reject(signal, RiskRejectionCode.EXCEEDS_ORDER_FREQUENCY,
                                  f"Order frequency limit: {cfg.max_order_frequency_sec}s, elapsed {elapsed:.0f}s")

        # 10. Daily loss limit
        if cfg.reference_capital and cfg.max_daily_loss_pct is not None:
            max_daily_loss = cfg.reference_capital * (cfg.max_daily_loss_pct / 100)
            total_daily = self.limits.daily_realized_pnl + self.limits.unrealized_pnl
            if total_daily <= -max_daily_loss:
                return self._reject(signal, RiskRejectionCode.EXCEEDS_DAILY_LOSS,
                                  f"Daily loss limit reached: {total_daily:.2f} <= -{max_daily_loss:.2f}")

        # 11. Drawdown
        if cfg.reference_capital and cfg.max_drawdown_pct is not None and self.limits.peak_capital > 0:
            current = cfg.reference_capital + self.limits.daily_realized_pnl + self.limits.unrealized_pnl
            drawdown = (self.limits.peak_capital - current) / self.limits.peak_capital * 100
            if drawdown >= cfg.max_drawdown_pct:
                return self._reject(signal, RiskRejectionCode.EXCEEDS_DRAWDOWN,
                                  f"Drawdown {drawdown:.2f}% >= limit {cfg.max_drawdown_pct}%")

        # 12. Exposure check
        if cfg.reference_capital and cfg.max_exposure_pct is not None:
            current_exposure = sum(abs(p.quantity * p.entry_price) for p in self.limits.open_positions)
            max_exposure = cfg.reference_capital * (cfg.max_exposure_pct / 100)
            if signal.entry_price:
                trade_value = signal.entry_price  # simplified — 1 unit
                if current_exposure + trade_value > max_exposure:
                    return self._reject(signal, RiskRejectionCode.EXCEEDS_MAX_EXPOSURE,
                                      f"Exposure would exceed limit: {current_exposure + trade_value:.2f} > {max_exposure:.2f}")

        # 13. Anomalous price check
        if signal.entry_price and signal.entry_price <= 0:
            return self._reject(signal, RiskRejectionCode.ANOMALOUS_PRICE,
                              f"Anomalous entry price: {signal.entry_price}")

        # All checks passed — issue authorization
        auth_id = f"auth-{uuid.uuid4().hex[:12]}"
        self._issued_authorizations.add(auth_id)
        risk_amount = cfg.reference_capital * (cfg.risk_per_trade_pct / 100) if cfg.reference_capital else 0

        logger.info(f"Risk approved signal {signal.id}, auth={auth_id}")
        return RiskDecision(
            signal_id=signal.id,
            approved=True,
            risk_amount=risk_amount,
            risk_percentage=cfg.risk_per_trade_pct,
            authorization_id=auth_id,
        )

    def issue_authorization(self, decision: RiskDecision, signal: Signal) -> Authorization:
        """Issue a single-use authorization bound to exact parameters."""
        if not decision.approved:
            raise ValueError("Cannot issue authorization for rejected decision")

        # Use the authorization_id from the decision (already tracked in _issued_authorizations)
        auth = Authorization(
            id=decision.authorization_id,
            risk_decision_id=decision.id,
            signal_id=signal.id,
            instrument=signal.instrument,
            intent_type=signal.signal_type.value,
            quantity=1.0,  # simplified — 1 unit
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
        )
        return auth

    def validate_authorization(
        self,
        auth: Authorization,
        instrument: str,
        intent_type: str,
        quantity: float,
        entry_price: float | None,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> tuple[bool, Optional[RiskRejectionCode]]:
        """Validate that an authorization matches exact parameters and is still valid."""
        # Check if auth was issued by this engine
        if auth.id not in self._issued_authorizations:
            return False, RiskRejectionCode.NO_AUTHORIZATION
        # Check if already used
        if auth.id in self.limits.used_authorization_ids:
            return False, RiskRejectionCode.AUTHORIZATION_REUSED
        if auth.used:
            return False, RiskRejectionCode.AUTHORIZATION_REUSED
        if auth.is_expired:
            return False, RiskRejectionCode.AUTHORIZATION_EXPIRED
        # Parameter match
        if auth.instrument != instrument:
            return False, RiskRejectionCode.PARAMETERS_ALTERED
        if auth.intent_type != intent_type:
            return False, RiskRejectionCode.PARAMETERS_ALTERED
        if auth.quantity != quantity:
            return False, RiskRejectionCode.PARAMETERS_ALTERED
        if auth.entry_price != entry_price:
            return False, RiskRejectionCode.PARAMETERS_ALTERED
        if auth.stop_loss != stop_loss:
            return False, RiskRejectionCode.PARAMETERS_ALTERED
        if auth.take_profit != take_profit:
            return False, RiskRejectionCode.PARAMETERS_ALTERED
        return True, None

    def mark_authorization_used(self, auth_id: str):
        """Mark an authorization as used (single-use enforcement)."""
        self.limits.used_authorization_ids.add(auth_id)

    def _reject(self, signal: Signal, code: RiskRejectionCode, reason: str) -> RiskDecision:
        logger.warning(f"Risk rejected signal {signal.id}: {code.value} — {reason}")
        return RiskDecision(
            signal_id=signal.id,
            approved=False,
            rejection_code=code,
            rejection_reason=reason,
        )
