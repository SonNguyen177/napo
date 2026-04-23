"""Order book with price-time priority (FIFO) matching."""

from __future__ import annotations

import itertools
from collections import deque
from dataclasses import dataclass, field
from typing import Iterator

from engine.config import StockConfig
from engine.models import (
    ExecType,
    ExecutionReport,
    OrdStatus,
    OrdType,
    Order,
    Side,
    Trade,
)


@dataclass
class MatchResult:
    """Result of processing a new order through the book."""

    trades: list[Trade] = field(default_factory=list)
    exec_reports: list[ExecutionReport] = field(default_factory=list)
    book_updates: list[dict] = field(default_factory=list)


class OrderBook:
    """Order book for a single instrument using price-time priority."""

    def __init__(self, config: StockConfig) -> None:
        self.config = config
        self.symbol = config.symbol
        # bids: price -> deque of orders (highest price = best bid)
        self._bids: dict[int, deque[Order]] = {}
        # asks: price -> deque of orders (lowest price = best ask)
        self._asks: dict[int, deque[Order]] = {}
        self._order_counter = itertools.count(1)
        self._trade_counter = itertools.count(1)
        self._exec_counter = itertools.count(1)

    def _next_order_id(self) -> str:
        return f"ORD-{self.symbol}-{next(self._order_counter)}"

    def _next_trade_id(self) -> str:
        return f"TRD-{self.symbol}-{next(self._trade_counter)}"

    def _next_exec_id(self) -> str:
        return f"EXEC-{self.symbol}-{next(self._exec_counter)}"

    @property
    def best_bid(self) -> int | None:
        if not self._bids:
            return None
        return max(self._bids.keys())

    @property
    def best_ask(self) -> int | None:
        if not self._asks:
            return None
        return min(self._asks.keys())

    def bids(self) -> list[tuple[int, int]]:
        """Return bids as [(price, total_qty)] sorted descending by price."""
        result = []
        for price in sorted(self._bids.keys(), reverse=True):
            total_qty = sum(o.leaves_qty for o in self._bids[price])
            if total_qty > 0:
                result.append((price, total_qty))
        return result

    def asks(self) -> list[tuple[int, int]]:
        """Return asks as [(price, total_qty)] sorted ascending by price."""
        result = []
        for price in sorted(self._asks.keys()):
            total_qty = sum(o.leaves_qty for o in self._asks[price])
            if total_qty > 0:
                result.append((price, total_qty))
        return result

    def validate_order(self, order: Order) -> str | None:
        """Validate order against stock config. Returns error or None."""
        if order.ord_type == OrdType.LIMIT:
            err = self.config.validate_price(order.price)
            if err:
                return err
        err = self.config.validate_quantity(order.quantity)
        if err:
            return err
        return None

    def process_order(self, order: Order) -> MatchResult:
        """Process a new order: validate, match, and place remainder on book."""
        result = MatchResult()

        # Assign order ID
        order.order_id = self._next_order_id()

        # Validate
        err = self.validate_order(order)
        if err:
            order.reject()
            result.exec_reports.append(self._make_exec_report(
                order, ExecType.REJECTED, reject_reason=err,
            ))
            return result

        # Match against opposite side
        self._match(order, result)

        # Handle remainder
        if order.leaves_qty > 0:
            if order.ord_type == OrdType.MARKET:
                # Cancel unfilled remainder of market orders
                order.cancel()
                result.exec_reports.append(self._make_exec_report(
                    order, ExecType.CANCELLED,
                ))
            else:
                # Place limit order remainder on book
                self._add_to_book(order)
                if order.status == OrdStatus.NEW:
                    result.exec_reports.append(self._make_exec_report(
                        order, ExecType.NEW,
                    ))
                # Book update for the new resting order
                side_str = "BUY" if order.side == Side.BUY else "SELL"
                book_side = self._bids if order.side == Side.BUY else self._asks
                level_qty = sum(o.leaves_qty for o in book_side.get(order.price, deque()))
                result.book_updates.append({
                    "symbol": self.symbol,
                    "side": side_str,
                    "price": order.price,
                    "quantity": level_qty,
                })

        return result

    def _match(self, incoming: Order, result: MatchResult) -> None:
        """Match incoming order against the opposite side of the book."""
        if incoming.side == Side.BUY:
            opposite = self._asks
            price_key = min  # best ask = lowest price
            is_matchable = lambda ask_price: (
                incoming.ord_type == OrdType.MARKET or incoming.price >= ask_price
            )
        else:
            opposite = self._bids
            price_key = max  # best bid = highest price
            is_matchable = lambda bid_price: (
                incoming.ord_type == OrdType.MARKET or incoming.price <= bid_price
            )

        while incoming.leaves_qty > 0 and opposite:
            best_price = price_key(opposite.keys())
            if not is_matchable(best_price):
                break

            queue = opposite[best_price]
            while incoming.leaves_qty > 0 and queue:
                resting = queue[-1]
                fill_qty = min(incoming.leaves_qty, resting.leaves_qty)
                fill_price = incoming.price if incoming.price else best_price

                # Apply fills
                incoming.fill(fill_qty, fill_price)
                resting.fill(fill_qty, fill_price)

                # Create trade
                buy_order = incoming if incoming.side == Side.BUY else resting
                sell_order = incoming if incoming.side == Side.SELL else resting
                trade = Trade(
                    trade_id=self._next_trade_id(),
                    symbol=self.symbol,
                    price=fill_price,
                    quantity=fill_qty,
                    buy_order_id=buy_order.order_id,
                    sell_order_id=sell_order.order_id,
                    buy_cl_ord_id=buy_order.cl_ord_id,
                    sell_cl_ord_id=sell_order.cl_ord_id,
                )
                result.trades.append(trade)

                # Exec reports for both sides
                result.exec_reports.append(self._make_exec_report(
                    incoming, ExecType.TRADE,
                    last_px=fill_price, last_qty=fill_qty,
                ))
                result.exec_reports.append(self._make_exec_report(
                    resting, ExecType.TRADE,
                    last_px=fill_price, last_qty=fill_qty,
                ))

                # Remove fully filled resting order
                if resting.leaves_qty == 0:
                    queue.pop()

            # Clean up empty price level
            if not queue:
                del opposite[best_price]

            # Book update for the affected price level
            opp_side = "SELL" if incoming.side == Side.BUY else "BUY"
            remaining_qty = sum(o.leaves_qty for o in queue) if best_price in opposite else 0
            result.book_updates.append({
                "symbol": self.symbol,
                "side": opp_side,
                "price": best_price,
                "quantity": remaining_qty,
            })

    def _add_to_book(self, order: Order) -> None:
        """Add a resting order to the appropriate side of the book."""
        book = self._bids if order.side == Side.BUY else self._asks
        if order.price not in book:
            book[order.price] = deque()
        book[order.price].append(order)

    def _make_exec_report(
        self,
        order: Order,
        exec_type: ExecType,
        last_px: int = 0,
        last_qty: int = 0,
        reject_reason: str = "",
    ) -> ExecutionReport:
        return ExecutionReport(
            cl_ord_id=order.cl_ord_id,
            order_id=order.order_id,
            exec_id=self._next_exec_id(),
            exec_type=exec_type,
            ord_status=order.status,
            symbol=self.symbol,
            side=order.side,
            price=order.price,
            quantity=order.quantity,
            leaves_qty=order.leaves_qty,
            cum_qty=order.cum_qty,
            avg_px=order.avg_px,
            last_px=last_px,
            last_qty=last_qty,
            reject_reason=reject_reason,
        )
