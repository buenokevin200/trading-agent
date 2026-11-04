"""Local deterministic execution simulator (SIMULATION ONLY — NO REAL BROKER)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from schemas import OrderEvent, Position, new_id, utc_now_iso


class Simulator:
    """Tracks synthetic prices, open positions, orders, protection levels, and realized/unrealized PnL."""

    COMMISSION_RATE = 0.0005  # 5 bps synthetic fee

    def __init__(self, initial_capital: float = 100000.0) -> None:
        self.initial_capital: float = initial_capital
        self.realized_pnl: float = 0.0
        self.peak_equity: float = initial_capital
        self.positions: List[Position] = []
        self.orders: List[OrderEvent] = []
        self._prices: Dict[str, float] = {
            "SYNTH/BTC": 68400.0,
            "SYNTH/ETH": 3480.0,
        }

    def update_price(self, instrument: str, price: float) -> None:
        self._prices[instrument] = price
        for pos in self.positions:
            if pos.instrument == instrument:
                pos.current_price = price
                if pos.side == "LONG":
                    pos.unrealized_pnl = round((price - pos.entry_price) * pos.quantity, 2)
                else:
                    pos.unrealized_pnl = round((pos.entry_price - price) * pos.quantity, 2)

    def get_price(self, instrument: str = "SYNTH/BTC") -> float:
        return self._prices.get(instrument, 0.0)

    def check_protection(self) -> List[Tuple[str, str]]:
        """Checks stop_loss and take_profit on open positions and closes hit positions."""
        triggered: List[Tuple[str, str]] = []
        remaining: List[Position] = []

        for pos in self.positions:
            price = self.get_price(pos.instrument)
            pos.current_price = price
            hit_type: Optional[str] = None

            if pos.is_protected:
                if pos.side == "LONG":
                    if pos.stop_loss is not None and price <= pos.stop_loss:
                        hit_type = "stop_loss_hit"
                    elif pos.take_profit is not None and price >= pos.take_profit:
                        hit_type = "take_profit_hit"
                else:
                    if pos.stop_loss is not None and price >= pos.stop_loss:
                        hit_type = "stop_loss_hit"
                    elif pos.take_profit is not None and price <= pos.take_profit:
                        hit_type = "take_profit_hit"

            if hit_type is not None:
                triggered.append((pos.instrument, hit_type))
                close_side = "SELL" if pos.side == "LONG" else "BUY"
                notional = price * pos.quantity
                commission = round(notional * self.COMMISSION_RATE, 2)
                if pos.side == "LONG":
                    pnl = round((price - pos.entry_price) * pos.quantity - commission, 2)
                else:
                    pnl = round((pos.entry_price - price) * pos.quantity - commission, 2)
                self.realized_pnl = round(self.realized_pnl + pnl, 2)
                self.orders.append(
                    OrderEvent(
                        order_id=new_id("ord"),
                        instrument=pos.instrument,
                        side=close_side,
                        quantity=pos.quantity,
                        status="filled",
                        fill_price=price,
                        commission=commission,
                        timestamp=utc_now_iso(),
                        stop_loss=pos.stop_loss,
                        take_profit=pos.take_profit,
                        reason=hit_type,
                    )
                )
            else:
                remaining.append(pos)

        self.positions = remaining
        self._update_peak_equity()
        return triggered

    def execute_order(
        self,
        instrument: str,
        side: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderEvent:
        price = self.get_price(instrument)
        if price <= 0 or quantity <= 0:
            order = OrderEvent(
                order_id=new_id("ord"),
                instrument=instrument,
                side=side,
                quantity=quantity,
                status="rejected",
                fill_price=0.0,
                commission=0.0,
                timestamp=utc_now_iso(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason="INVALID_PRICE_OR_QUANTITY",
            )
            self.orders.append(order)
            return order

        notional = price * quantity
        commission = round(notional * self.COMMISSION_RATE, 2)
        self.realized_pnl = round(self.realized_pnl - commission, 2)

        existing = next((p for p in self.positions if p.instrument == instrument), None)
        target_pos_side = "LONG" if side == "BUY" else "SHORT"

        if existing is not None and existing.side != target_pos_side:
            # Close existing opposite position and open new one
            if existing.side == "LONG":
                close_pnl = round((price - existing.entry_price) * existing.quantity, 2)
            else:
                close_pnl = round((existing.entry_price - price) * existing.quantity, 2)
            self.realized_pnl = round(self.realized_pnl + close_pnl, 2)
            self.positions.remove(existing)
            existing = None

        is_protected = stop_loss is not None and take_profit is not None
        if existing is None:
            self.positions.append(
                Position(
                    instrument=instrument,
                    side=target_pos_side,
                    quantity=round(quantity, 4),
                    entry_price=price,
                    current_price=price,
                    unrealized_pnl=0.0,
                    is_protected=is_protected,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
            )
        else:
            total_qty = round(existing.quantity + quantity, 4)
            avg_entry = round(
                ((existing.entry_price * existing.quantity) + (price * quantity)) / total_qty,
                2,
            )
            existing.quantity = total_qty
            existing.entry_price = avg_entry
            existing.current_price = price
            existing.stop_loss = stop_loss or existing.stop_loss
            existing.take_profit = take_profit or existing.take_profit
            existing.is_protected = existing.stop_loss is not None and existing.take_profit is not None

        order = OrderEvent(
            order_id=new_id("ord"),
            instrument=instrument,
            side=side,
            quantity=round(quantity, 4),
            status="filled",
            fill_price=price,
            commission=commission,
            timestamp=utc_now_iso(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason="SIGNAL_EXECUTION",
        )
        self.orders.append(order)
        self._update_peak_equity()
        return order

    def _update_peak_equity(self) -> None:
        unrealized = sum(p.unrealized_pnl for p in self.positions)
        equity = self.initial_capital + self.realized_pnl + unrealized
        if equity > self.peak_equity:
            self.peak_equity = equity

    def reconcile(self) -> Dict[str, Any]:
        for pos in self.positions:
            price = self.get_price(pos.instrument)
            pos.current_price = price
            if pos.side == "LONG":
                pos.unrealized_pnl = round((price - pos.entry_price) * pos.quantity, 2)
            else:
                pos.unrealized_pnl = round((pos.entry_price - price) * pos.quantity, 2)

        filled = [o for o in self.orders if o.status == "filled"]
        rejected = [o for o in self.orders if o.status == "rejected"]
        return {
            "positions": [p.to_dict() for p in self.positions],
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(sum(p.unrealized_pnl for p in self.positions), 2),
            "total_orders": len(self.orders),
            "filled_orders": len(filled),
            "rejected_orders": len(rejected),
        }
