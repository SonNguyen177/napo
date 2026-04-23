"""Matching engine managing per-stock order books."""

from __future__ import annotations

import os
import sys

from engine.config import ExchangeConfig, StockConfig
from engine.models import (
    ExecType,
    ExecutionReport,
    OrdStatus,
    Order,
    Side,
    Trade,
)
from engine.order_book import MatchResult, OrderBook


class MatchingEngine:
    """Central matching engine that routes orders to per-stock order books."""

    def __init__(self, config: ExchangeConfig | None = None) -> None:
        self.config = config or ExchangeConfig()
        self._books: dict[str, OrderBook] = {}
        self._trades: list[Trade] = []

        # Initialize order books for all configured stocks
        for symbol, stock_config in self.config.stocks.items():
            self._books[symbol] = OrderBook(stock_config)

    def submit_order(self, order: Order) -> MatchResult:
        """Submit an order to the engine. Returns match result with trades and exec reports."""
        result = MatchResult()

        # Check market is open
        if not self.config.is_open():
            order.reject()
            result.exec_reports.append(ExecutionReport(
                cl_ord_id=order.cl_ord_id,
                order_id="",
                exec_id="EXEC-REJ-MARKET-CLOSED",
                exec_type=ExecType.REJECTED,
                ord_status=OrdStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                leaves_qty=0,
                cum_qty=0,
                avg_px=0.0,
                reject_reason="Market is closed",
            ))
            return result

        # Check symbol exists
        book = self._books.get(order.symbol)
        if book is None:
            order.reject()
            result.exec_reports.append(ExecutionReport(
                cl_ord_id=order.cl_ord_id,
                order_id="",
                exec_id="EXEC-REJ-UNKNOWN-SYM",
                exec_type=ExecType.REJECTED,
                ord_status=OrdStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                leaves_qty=0,
                cum_qty=0,
                avg_px=0.0,
                reject_reason=f"Unknown symbol: {order.symbol}",
            ))
            return result

        # Envelope guards: fail-fast on inputs that violate book invariants.
        # These should never trip in production because upstream layers validate
        # first; if they do, abort rather than risk a corrupt book.
        if order.price < 0:
            sys.stderr.write(f"[engine] FATAL: negative price {order.price} for {order.symbol}\n")
            sys.stderr.flush()
            os._exit(1)
        if order.quantity <= 0:
            sys.stderr.write(f"[engine] FATAL: non-positive quantity {order.quantity} for {order.symbol}\n")
            sys.stderr.flush()
            os._exit(1)
        if book.config.ceiling <= book.config.floor:
            sys.stderr.write(
                f"[engine] FATAL: degenerate price range for {order.symbol} "
                f"(floor={book.config.floor}, ceiling={book.config.ceiling})\n"
            )
            sys.stderr.flush()
            os._exit(1)

        # Route to the stock's order book
        result = book.process_order(order)

        # Record trades
        self._trades.extend(result.trades)

        return result

    def get_order_book(self, symbol: str) -> OrderBook | None:
        return self._books.get(symbol)

    def get_trades(self, symbol: str | None = None) -> list[Trade]:
        if symbol is None:
            return list(self._trades)
        return [t for t in self._trades if t.symbol == symbol]

    def get_all_books(self) -> dict[str, OrderBook]:
        return dict(self._books)

    def update_stock_config(self, symbol: str, **kwargs: int) -> StockConfig | None:
        """Update stock config fields (floor, ceiling, price_step, qty_step).

        Returns the updated config, or None if symbol not found.
        Note: updating config does not affect existing orders on the book.
        """
        stock = self.config.get_stock(symbol)
        if stock is None:
            return None

        for key in ("floor", "ceiling", "price_step", "qty_step"):
            if key in kwargs:
                setattr(stock, key, kwargs[key])

        # Update the book's config reference too
        if symbol in self._books:
            self._books[symbol].config = stock

        return stock
