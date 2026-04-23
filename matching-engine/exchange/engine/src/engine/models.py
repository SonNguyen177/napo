"""Core data models for the exchange engine."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrdType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrdStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class ExecType(str, Enum):
    NEW = "NEW"
    TRADE = "TRADE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class MarketState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"


@dataclass
class Order:
    cl_ord_id: str
    account: str
    symbol: str
    side: Side
    ord_type: OrdType
    price: int  # VND, 0 for market orders
    quantity: int
    order_id: str = ""
    status: OrdStatus = OrdStatus.NEW
    filled_qty: int = 0
    leaves_qty: int = 0
    avg_px: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.leaves_qty == 0:
            self.leaves_qty = self.quantity

    @property
    def cum_qty(self) -> int:
        return self.filled_qty

    def fill(self, qty: int, price: int) -> None:
        """Apply a fill of `qty` at `price`."""
        total_cost = self.avg_px * self.filled_qty + price * qty
        self.filled_qty += qty
        self.leaves_qty = self.quantity - self.filled_qty
        self.avg_px = total_cost / self.filled_qty if self.filled_qty > 0 else 0.0
        if self.leaves_qty == 0:
            self.status = OrdStatus.FILLED
        else:
            self.status = OrdStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        self.status = OrdStatus.CANCELLED
        self.leaves_qty = 0

    def reject(self) -> None:
        self.status = OrdStatus.REJECTED
        self.leaves_qty = 0


@dataclass
class Trade:
    trade_id: str
    symbol: str
    price: int
    quantity: int
    buy_order_id: str
    sell_order_id: str
    buy_cl_ord_id: str
    sell_cl_ord_id: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionReport:
    cl_ord_id: str
    order_id: str
    exec_id: str
    exec_type: ExecType
    ord_status: OrdStatus
    symbol: str
    side: Side
    price: int
    quantity: int
    leaves_qty: int
    cum_qty: int
    avg_px: float
    last_px: int = 0
    last_qty: int = 0
    reject_reason: str = ""
