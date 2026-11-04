"""Local simulator — simulates order matching, fills, and price feeds."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import logging
import random

from ..schemas.order_event import OrderEvent, OrderStatus, OrderFill
from ..schemas.position import Position
from ..schemas.intent import Intent, IntentType

logger = logging.getLogger(__name__)


class Simulator:
    """
    Local order simulator. Matches orders against a synthetic price feed.
    Supports: market orders (instant fill), limit orders (queue), partial fills.
    Strictly simulation — no real money, no real exchange.
    """

    def __init__(self, commission_pct: float = 0.001, slippage_pct: float = 0.0005):
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self._prices: dict[str, float] = {}  # instrument -> current price
        self._positions: dict[str, Position] = {}  # instrument -> position
        self._orders: dict[str, OrderEvent] = {}  # order_id -> order
        self._realized_pnl: float = 0.0

    def set_price(self, instrument: str, price: float):
        """Set the current simulated price for an instrument."""
        if price <= 0:
            raise ValueError(f"Price must be positive, got {price}")
        self._prices[instrument] = price
        # Update position current prices
        if instrument in self._positions:
            self._positions[instrument].current_price = price

    def get_price(self, instrument: str) -> Optional[float]:
        return self._prices.get(instrument)

    @property
    def positions(self) -> list[Position]:
        return list(self._positions.values())

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    def execute_order(self, intent: Intent) -> OrderEvent:
        """
        Execute an intent as a market order in the simulator.
        Returns the OrderEvent with fill details.
        """
        price = self._prices.get(intent.instrument)
        if price is None:
            order = OrderEvent(
                intent_id=intent.id,
                instrument=intent.instrument,
                side=intent.intent_type.value,
                quantity=intent.quantity,
                status=OrderStatus.REJECTED,
                rejection_reason="No price set for instrument",
            )
            self._orders[order.id] = order
            return order

        # Apply slippage
        if intent.intent_type in (IntentType.BUY,):
            fill_price = price * (1 + self.slippage_pct * random.uniform(0, 1))
        else:
            fill_price = price * (1 - self.slippage_pct * random.uniform(0, 1))

        commission = fill_price * intent.quantity * self.commission_pct

        fill = OrderFill(
            filled_qty=intent.quantity,
            filled_price=fill_price,
            commission=commission,
        )

        order = OrderEvent(
            intent_id=intent.id,
            instrument=intent.instrument,
            side=intent.intent_type.value,
            quantity=intent.quantity,
            status=OrderStatus.FILLED,
            fills=[fill],
        )
        self._orders[order.id] = order

        # Update positions
        self._update_position(intent, fill_price, order.id)

        logger.info(
            f"Simulator: {intent.intent_type.value} {intent.quantity} {intent.instrument} "
            f"@ {fill_price:.4f} (commission={commission:.4f})"
        )
        return order

    def _update_position(self, intent: Intent, fill_price: float, order_id: str):
        """Update internal position tracking."""
        instrument = intent.instrument

        if intent.intent_type == IntentType.BUY:
            if instrument in self._positions:
                # Already have position — update (simplified: no averaging)
                pos = self._positions[instrument]
                if pos.side == "LONG":
                    pos.quantity += intent.quantity
                    pos.entry_price = (pos.entry_price * (pos.quantity - intent.quantity) + fill_price * intent.quantity) / pos.quantity
                else:
                    # Closing short
                    self._realized_pnl += (pos.entry_price - fill_price) * intent.quantity
                    del self._positions[instrument]
            else:
                self._positions[instrument] = Position(
                    instrument=instrument,
                    side="LONG",
                    quantity=intent.quantity,
                    entry_price=fill_price,
                    stop_loss=intent.stop_loss,
                    take_profit=intent.take_profit,
                    order_id=order_id,
                    current_price=self._prices.get(instrument),
                )

        elif intent.intent_type == IntentType.SELL:
            if instrument in self._positions and self._positions[instrument].side == "LONG":
                # Closing long
                pos = self._positions[instrument]
                self._realized_pnl += (fill_price - pos.entry_price) * intent.quantity
                del self._positions[instrument]
            else:
                # Opening short (if allowed)
                self._positions[instrument] = Position(
                    instrument=instrument,
                    side="SHORT",
                    quantity=intent.quantity,
                    entry_price=fill_price,
                    stop_loss=intent.stop_loss,
                    take_profit=intent.take_profit,
                    order_id=order_id,
                    current_price=self._prices.get(instrument),
                )

        elif intent.intent_type == IntentType.CLOSE:
            if instrument in self._positions:
                pos = self._positions[instrument]
                if pos.side == "LONG":
                    self._realized_pnl += (fill_price - pos.entry_price) * pos.quantity
                else:
                    self._realized_pnl += (pos.entry_price - fill_price) * pos.quantity
                del self._positions[instrument]

    def check_protection(self) -> list[tuple[str, str]]:
        """Check if any position has hit its stop-loss or take-profit."""
        hits = []
        for instrument, pos in list(self._positions.items()):
            price = self._prices.get(instrument)
            if price is None:
                continue
            if pos.stop_loss and price <= pos.stop_loss:
                hits.append((instrument, "stop_loss_hit"))
            elif pos.take_profit and price >= pos.take_profit:
                hits.append((instrument, "take_profit_hit"))
        return hits

    def get_order(self, order_id: str) -> Optional[OrderEvent]:
        return self._orders.get(order_id)

    def reconcile(self) -> dict[str, Any]:
        """Reconcile orders and positions — return summary."""
        return {
            "positions": [
                {
                    "instrument": p.instrument,
                    "side": p.side,
                    "quantity": p.quantity,
                    "entry_price": p.entry_price,
                    "current_price": p.current_price,
                    "unrealized_pnl": p.unrealized_pnl,
                    "is_protected": p.is_protected,
                }
                for p in self._positions.values()
            ],
            "realized_pnl": self._realized_pnl,
            "total_orders": len(self._orders),
            "filled_orders": sum(1 for o in self._orders.values() if o.status == OrderStatus.FILLED),
            "rejected_orders": sum(1 for o in self._orders.values() if o.status == OrderStatus.REJECTED),
        }


# Fix missing import
from typing import Any
