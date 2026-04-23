"""Regression test for ECH-ENGINE-001: price-time priority must be FIFO.

The bug was that `_match` read `queue[-1]` and called `queue.pop()` while
`_add_to_book` appended to the right — so the newest resting order at a
price level matched first (LIFO) instead of the oldest (FIFO).
"""

from engine.config import StockConfig
from engine.models import OrdType, Order, Side
from engine.order_book import OrderBook


def _cfg() -> StockConfig:
    return StockConfig(symbol="TST", floor=10000, ceiling=20000, price_step=100, qty_step=100)


def _order(side: Side, price: int, qty: int, cl_ord_id: str, ord_type: OrdType = OrdType.LIMIT) -> Order:
    return Order(
        cl_ord_id=cl_ord_id,
        account="ACC1",
        symbol="TST",
        side=side,
        ord_type=ord_type,
        price=price,
        quantity=qty,
    )


def test_same_price_bids_match_in_fifo_order():
    """Two buy limits at the same price — the older one must fill first."""
    book = OrderBook(_cfg())

    book.process_order(_order(Side.BUY, 15000, 100, cl_ord_id="A-FIRST"))
    book.process_order(_order(Side.BUY, 15000, 100, cl_ord_id="B-LATER"))

    result = book.process_order(_order(Side.SELL, 0, 100, cl_ord_id="S", ord_type=OrdType.MARKET))

    assert len(result.trades) == 1, "Expected exactly one trade for qty=100"
    assert result.trades[0].buy_cl_ord_id == "A-FIRST", (
        "FIFO violated: resting order placed earlier must be matched before later ones"
    )


def test_same_price_asks_match_in_fifo_order():
    """Symmetric case: two sell limits at the same price — the older one fills first."""
    book = OrderBook(_cfg())

    book.process_order(_order(Side.SELL, 15000, 100, cl_ord_id="A-FIRST"))
    book.process_order(_order(Side.SELL, 15000, 100, cl_ord_id="B-LATER"))

    result = book.process_order(_order(Side.BUY, 0, 100, cl_ord_id="B", ord_type=OrdType.MARKET))

    assert len(result.trades) == 1
    assert result.trades[0].sell_cl_ord_id == "A-FIRST"
