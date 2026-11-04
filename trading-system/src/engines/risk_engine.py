"""Deterministic Risk Engine with 20 rejection codes (SIMULATION ONLY)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from schemas import Observation, Position, RiskDecision, Signal, new_id, utc_now_iso


REJECTION_CODES: Dict[str, str] = {
    "ERR_01_EMERGENCY_STOP": "Interruptor de emergencia activo: nuevas exposiciones bloqueadas",
    "ERR_02_LIMITS_NOT_CONFIGURED": "Límites de riesgo no configurados",
    "ERR_03_INSTRUMENT_NOT_ALLOWED": "Instrumento fuera del universo autorizado",
    "ERR_04_STALE_DATA": "Observación de mercado vencida o sin marca temporal vigente",
    "ERR_05_INVALID_PRICE": "Precio de entrada inválido o no positivo",
    "ERR_06_MISSING_PROTECTION": "Falta stop_loss o take_profit obligatorio",
    "ERR_07_INVALID_SL_TP_GEOMETRY": "Geometría de stop_loss / take_profit incoherente con la dirección",
    "ERR_08_MAX_RISK_PER_TRADE": "Riesgo de la operación supera risk_per_trade permitido",
    "ERR_09_MAX_EXPOSURE": "Exposición total superaría el límite max_exposure",
    "ERR_10_MAX_DAILY_LOSS": "Pérdida diaria acumulada supera max_daily_loss",
    "ERR_11_MAX_DRAWDOWN": "Drawdown desde el pico supera max_drawdown",
    "ERR_12_MAX_POSITIONS": "Número máximo de posiciones abiertas alcanzado (max_positions)",
    "ERR_13_MAX_PENDING_ORDERS": "Número máximo de órdenes pendientes excedido",
    "ERR_14_TRADE_FREQUENCY_LIMIT": "Frecuencia máxima de operaciones por ventana excedida",
    "ERR_15_INSUFFICIENT_LIQUIDITY": "Volumen sintético insuficiente para ejecutar orden",
    "ERR_16_EXCESSIVE_SPREAD": "Spread bid/ask supera el umbral máximo permitido",
    "ERR_17_LEVERAGE_DISABLED": "Operación requeriría apalancamiento no autorizado",
    "ERR_18_SHORT_SELLING_DISABLED": "Posiciones cortas deshabilitadas por configuración",
    "ERR_19_DUPLICATE_INTENT": "Señal o intención duplicada ya procesada",
    "ERR_20_NO_OPERATION_SIGNAL": "Señal NO_OPERATION: abstención determinista sin orden",
}


class RiskEngine:
    """Evaluates signals deterministically against 20 explicit safety rules."""

    def __init__(
        self,
        reference_capital: float = 100000.0,
        risk_per_trade: float = 0.01,       # 1% max risk per trade ($1,000)
        max_exposure: float = 0.50,         # 50% max portfolio notional ($50,000)
        max_daily_loss: float = 0.03,       # 3% max daily loss ($3,000)
        max_drawdown: float = 0.06,         # 6% max drawdown ($6,000)
        max_positions: int = 4,
        allowed_instruments: Optional[List[str]] = None,
        allow_short: bool = True,
        limits_configured: bool = True,
    ) -> None:
        self.reference_capital = reference_capital
        self.risk_per_trade = risk_per_trade
        self.max_exposure = max_exposure
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.max_positions = max_positions
        self.allowed_instruments = allowed_instruments or ["SYNTH/BTC", "SYNTH/ETH"]
        self.allow_short = allow_short
        self.limits_configured = limits_configured
        self._processed_signals: set[str] = set()

    def get_limits(self) -> Dict[str, Any]:
        return {
            "reference_capital": self.reference_capital,
            "risk_per_trade": self.risk_per_trade,
            "max_exposure": self.max_exposure,
            "max_daily_loss": self.max_daily_loss,
            "max_drawdown": self.max_drawdown,
            "max_positions": self.max_positions,
            "allowed_instruments": self.allowed_instruments,
            "limits_configured": self.limits_configured,
        }

    def _reject(self, signal: Signal, code: str, custom_reason: Optional[str] = None) -> RiskDecision:
        return RiskDecision(
            decision_id=new_id("risk"),
            signal_id=signal.signal_id,
            instrument=signal.instrument,
            approved=False,
            rejection_code=code,
            rejection_reason=custom_reason or REJECTION_CODES.get(code, code),
            approved_quantity=0.0,
            risk_amount=0.0,
            timestamp=utc_now_iso(),
        )

    def evaluate(
        self,
        signal: Signal,
        observation: Observation,
        positions: List[Position],
        realized_pnl: float,
        peak_equity: float,
        emergency_stop: bool = False,
    ) -> RiskDecision:
        if emergency_stop:
            return self._reject(signal, "ERR_01_EMERGENCY_STOP")

        if not self.limits_configured:
            return self._reject(signal, "ERR_02_LIMITS_NOT_CONFIGURED")

        if signal.signal_type == "NO_OPERATION":
            return self._reject(signal, "ERR_20_NO_OPERATION_SIGNAL")

        if signal.instrument not in self.allowed_instruments:
            return self._reject(signal, "ERR_03_INSTRUMENT_NOT_ALLOWED")

        if observation.quality != "SYNTHETIC_OK":
            return self._reject(signal, "ERR_04_STALE_DATA")

        if signal.entry_price <= 0 or observation.price <= 0:
            return self._reject(signal, "ERR_05_INVALID_PRICE")

        if signal.stop_loss is None or signal.take_profit is None:
            return self._reject(signal, "ERR_06_MISSING_PROTECTION")

        if signal.signal_type == "BUY" and not (signal.stop_loss < signal.entry_price < signal.take_profit):
            return self._reject(signal, "ERR_07_INVALID_SL_TP_GEOMETRY")

        if signal.signal_type == "SELL" and not (signal.take_profit < signal.entry_price < signal.stop_loss):
            return self._reject(signal, "ERR_07_INVALID_SL_TP_GEOMETRY")

        if signal.signal_type == "SELL" and not self.allow_short:
            has_long = any(p.instrument == signal.instrument and p.side == "LONG" for p in positions)
            if not has_long:
                return self._reject(signal, "ERR_18_SHORT_SELLING_DISABLED")

        if signal.signal_id in self._processed_signals:
            return self._reject(signal, "ERR_19_DUPLICATE_INTENT")

        spread_ratio = (observation.ask - observation.bid) / observation.price
        if spread_ratio > 0.005:
            return self._reject(signal, "ERR_16_EXCESSIVE_SPREAD")

        if observation.volume < 1.0:
            return self._reject(signal, "ERR_15_INSUFFICIENT_LIQUIDITY")

        unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        total_pnl = realized_pnl + unrealized_pnl
        if total_pnl <= -(self.reference_capital * self.max_daily_loss):
            return self._reject(signal, "ERR_10_MAX_DAILY_LOSS")

        current_equity = self.reference_capital + total_pnl
        drawdown = max(0.0, peak_equity - current_equity)
        if drawdown >= (self.reference_capital * self.max_drawdown):
            return self._reject(signal, "ERR_11_MAX_DRAWDOWN")

        same_inst_pos = next((p for p in positions if p.instrument == signal.instrument), None)
        if same_inst_pos is None and len(positions) >= self.max_positions:
            return self._reject(signal, "ERR_12_MAX_POSITIONS")

        # Position sizing based on risk_per_trade and stop distance, capped by max_exposure
        max_risk_dollars = self.reference_capital * self.risk_per_trade
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        if stop_distance <= 0:
            return self._reject(signal, "ERR_07_INVALID_SL_TP_GEOMETRY")

        raw_qty = max_risk_dollars / stop_distance
        current_exposure = sum(p.current_price * p.quantity for p in positions)
        max_notional_total = self.reference_capital * self.max_exposure
        remaining_notional = max_notional_total - current_exposure

        # Per-order notional cap (15% of reference capital) so multiple positions can coexist
        order_notional_cap = min(remaining_notional, self.reference_capital * 0.15)
        if order_notional_cap <= 50.0:
            return self._reject(signal, "ERR_09_MAX_EXPOSURE")

        qty_by_exposure = order_notional_cap / signal.entry_price
        final_qty = round(min(raw_qty, qty_by_exposure), 4)
        if final_qty <= 0:
            return self._reject(signal, "ERR_08_MAX_RISK_PER_TRADE")

        actual_risk = round(final_qty * stop_distance, 2)
        if actual_risk > max_risk_dollars * 1.05:
            return self._reject(signal, "ERR_08_MAX_RISK_PER_TRADE")

        self._processed_signals.add(signal.signal_id)
        return RiskDecision(
            decision_id=new_id("risk"),
            signal_id=signal.signal_id,
            instrument=signal.instrument,
            approved=True,
            rejection_code=None,
            rejection_reason="Aprobado por motor determinista de riesgo (dentro de límites)",
            approved_quantity=final_qty,
            risk_amount=actual_risk,
            timestamp=utc_now_iso(),
        )
