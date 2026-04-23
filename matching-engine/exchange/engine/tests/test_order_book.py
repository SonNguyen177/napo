"""Tests for the order book with price-time priority matching."""

from engine.config import StockConfig
from engine.models import ExecType, OrdStatus, OrdType, Order, Side
from engine.order_book import OrderBook


def make_config() -> StockConfig:
    return StockConfig(symbol="TST", floor=10000, ceiling=20000, price_step=100, qty_step=100)


def make_order(
    side: Side,
    price: int,
    quantity: int,
    ord_type: OrdType = OrdType.LIMIT,
    cl_ord_id: str = "",
) -> Order:
    return Order(
        cl_ord_id=cl_ord_id or f"C-{side.value}-{price}-{quantity}",
        account="ACC1",
        symbol="TST",
        side=side,
        ord_type=ord_type,
        price=price,
        quantity=quantity,
    )


class TestEmptyBook:
    def test_limit_buy_rests_on_book(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 15000, 100)
        result = book.process_order(order)

        assert len(result.trades) == 0
        assert len(result.exec_reports) == 1
        assert result.exec_reports[0].exec_type == ExecType.NEW
        assert result.exec_reports[0].ord_status == OrdStatus.NEW
        assert book.best_bid == 15000
        assert book.best_ask is None

    def test_limit_sell_rests_on_book(self):
        book = OrderBook(make_config())
        order = make_order(Side.SELL, 16000, 100)
        result = book.process_order(order)

        assert len(result.trades) == 0
        assert len(result.exec_reports) == 1
        assert result.exec_reports[0].exec_type == ExecType.NEW
        assert book.best_bid is None
        assert book.best_ask == 16000

    def test_market_buy_on_empty_book_cancelled(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 0, 100, OrdType.MARKET)
        result = book.process_order(order)

        assert len(result.trades) == 0
        assert result.exec_reports[-1].exec_type == ExecType.CANCELLED
        assert order.status == OrdStatus.CANCELLED

    def test_market_sell_on_empty_book_cancelled(self):
        book = OrderBook(make_config())
        order = make_order(Side.SELL, 0, 100, OrdType.MARKET)
        result = book.process_order(order)

        assert len(result.trades) == 0
        assert result.exec_reports[-1].exec_type == ExecType.CANCELLED


class TestSimpleMatching:
    def test_exact_match(self):
        """Buy limit at 15000, sell limit at 15000 -> trade at 15000."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 100))
        result = book.process_order(make_order(Side.BUY, 15000, 100))

        assert len(result.trades) == 1
        assert result.trades[0].price == 15000
        assert result.trades[0].quantity == 100
        assert book.best_bid is None
        assert book.best_ask is None

    def test_price_improvement(self):
        """Buy at 16000, sell resting at 15000 -> trade at 15000 (resting price)."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 100))
        result = book.process_order(make_order(Side.BUY, 16000, 100))

        assert len(result.trades) == 1
        assert result.trades[0].price == 15000  # resting order's price
        assert book.best_bid is None
        assert book.best_ask is None

    def test_no_match_buy_below_ask(self):
        """Buy at 14000, sell resting at 15000 -> no match, both rest."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 100))
        result = book.process_order(make_order(Side.BUY, 14000, 100))

        assert len(result.trades) == 0
        assert book.best_bid == 14000
        assert book.best_ask == 15000

    def test_no_match_sell_above_bid(self):
        """Sell at 16000, buy resting at 15000 -> no match."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.BUY, 15000, 100))
        result = book.process_order(make_order(Side.SELL, 16000, 100))

        assert len(result.trades) == 0
        assert book.best_bid == 15000
        assert book.best_ask == 16000


class TestPartialFills:
    def test_partial_fill_buy(self):
        """Buy 500, sell resting 200 -> trade 200, buy rests with 300."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 200))
        result = book.process_order(make_order(Side.BUY, 15000, 500))

        assert len(result.trades) == 1
        assert result.trades[0].quantity == 200
        assert book.best_bid == 15000
        assert book.bids() == [(15000, 300)]
        assert book.best_ask is None

    def test_partial_fill_sell(self):
        """Sell 500, buy resting 200 -> trade 200, sell rests with 300."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.BUY, 15000, 200))
        result = book.process_order(make_order(Side.SELL, 15000, 500))

        assert len(result.trades) == 1
        assert result.trades[0].quantity == 200
        assert book.best_ask == 15000
        assert book.asks() == [(15000, 300)]
        assert book.best_bid is None

    def test_multiple_fills_across_levels(self):
        """Buy 500 walks through multiple ask levels."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 200))
        book.process_order(make_order(Side.SELL, 15100, 200))
        book.process_order(make_order(Side.SELL, 15200, 200))

        result = book.process_order(make_order(Side.BUY, 15200, 500))

        assert len(result.trades) == 3
        assert result.trades[0].price == 15000
        assert result.trades[0].quantity == 200
        assert result.trades[1].price == 15100
        assert result.trades[1].quantity == 200
        assert result.trades[2].price == 15200
        assert result.trades[2].quantity == 100
        # 100 remains at 15200
        assert book.best_ask == 15200
        assert book.asks() == [(15200, 100)]
        assert book.best_bid is None  # fully filled


class TestMarketOrders:
    def test_market_buy_fills_against_asks(self):
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 200))
        book.process_order(make_order(Side.SELL, 15100, 300))

        order = make_order(Side.BUY, 0, 300, OrdType.MARKET)
        result = book.process_order(order)

        assert len(result.trades) == 2
        assert result.trades[0].price == 15000
        assert result.trades[0].quantity == 200
        assert result.trades[1].price == 15100
        assert result.trades[1].quantity == 100
        assert order.status == OrdStatus.FILLED

    def test_market_sell_fills_against_bids(self):
        book = OrderBook(make_config())
        book.process_order(make_order(Side.BUY, 15000, 200))
        book.process_order(make_order(Side.BUY, 14900, 300))

        order = make_order(Side.SELL, 0, 300, OrdType.MARKET)
        result = book.process_order(order)

        assert len(result.trades) == 2
        assert result.trades[0].price == 15000
        assert result.trades[0].quantity == 200
        assert result.trades[1].price == 14900
        assert result.trades[1].quantity == 100
        assert order.status == OrdStatus.FILLED

    def test_market_order_partial_then_cancel(self):
        """Market order partially fills, remainder cancelled."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 100))

        order = make_order(Side.BUY, 0, 500, OrdType.MARKET)
        result = book.process_order(order)

        assert len(result.trades) == 1
        assert result.trades[0].quantity == 100
        assert order.status == OrdStatus.CANCELLED
        assert order.filled_qty == 100
        # Last exec report should be CANCELLED
        assert result.exec_reports[-1].exec_type == ExecType.CANCELLED


class TestPriceTimePriority:
    def test_time_priority_at_same_price(self):
        """Earlier order at same price fills first."""
        book = OrderBook(make_config())
        sell1 = make_order(Side.SELL, 15000, 100, cl_ord_id="SELL-1")
        sell2 = make_order(Side.SELL, 15000, 100, cl_ord_id="SELL-2")
        book.process_order(sell1)
        book.process_order(sell2)

        result = book.process_order(make_order(Side.BUY, 15000, 100))

        assert len(result.trades) == 1
        assert result.trades[0].sell_cl_ord_id == "SELL-1"
        # sell2 still resting
        assert book.asks() == [(15000, 100)]

    def test_price_priority_over_time(self):
        """Better-priced order fills first regardless of time."""
        book = OrderBook(make_config())
        # sell1 at higher price arrives first
        sell1 = make_order(Side.SELL, 15100, 100, cl_ord_id="SELL-HIGH")
        sell2 = make_order(Side.SELL, 15000, 100, cl_ord_id="SELL-LOW")
        book.process_order(sell1)
        book.process_order(sell2)

        result = book.process_order(make_order(Side.BUY, 15100, 100))

        assert len(result.trades) == 1
        assert result.trades[0].sell_cl_ord_id == "SELL-LOW"
        assert result.trades[0].price == 15000


class TestValidation:
    def test_price_below_floor(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 9000, 100)
        result = book.process_order(order)

        assert order.status == OrdStatus.REJECTED
        assert result.exec_reports[0].exec_type == ExecType.REJECTED
        assert "below floor" in result.exec_reports[0].reject_reason

    def test_price_above_ceiling(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 25000, 100)
        result = book.process_order(order)

        assert order.status == OrdStatus.REJECTED
        assert "above ceiling" in result.exec_reports[0].reject_reason

    def test_invalid_price_step(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 15050, 100)  # step is 100, 15050 not aligned
        result = book.process_order(order)

        assert order.status == OrdStatus.REJECTED
        assert "not aligned to step" in result.exec_reports[0].reject_reason

    def test_invalid_quantity_step(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 15000, 150)  # step is 100, 150 not aligned
        result = book.process_order(order)

        assert order.status == OrdStatus.REJECTED
        assert "not aligned to step" in result.exec_reports[0].reject_reason

    def test_zero_quantity(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 15000, 0)
        result = book.process_order(order)

        assert order.status == OrdStatus.REJECTED
        assert "positive" in result.exec_reports[0].reject_reason

    def test_valid_price_at_floor(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 10000, 100)
        result = book.process_order(order)
        assert order.status == OrdStatus.NEW

    def test_valid_price_at_ceiling(self):
        book = OrderBook(make_config())
        order = make_order(Side.BUY, 20000, 100)
        result = book.process_order(order)
        assert order.status == OrdStatus.NEW

    def test_market_order_skips_price_validation(self):
        """Market orders should not be rejected for price."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 100))
        order = make_order(Side.BUY, 0, 100, OrdType.MARKET)
        result = book.process_order(order)
        assert order.status == OrdStatus.FILLED


class TestBookState:
    def test_bids_sorted_descending(self):
        book = OrderBook(make_config())
        book.process_order(make_order(Side.BUY, 14000, 100))
        book.process_order(make_order(Side.BUY, 15000, 200))
        book.process_order(make_order(Side.BUY, 13000, 300))

        bids = book.bids()
        assert bids == [(15000, 200), (14000, 100), (13000, 300)]

    def test_asks_sorted_ascending(self):
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 16000, 100))
        book.process_order(make_order(Side.SELL, 15000, 200))
        book.process_order(make_order(Side.SELL, 17000, 300))

        asks = book.asks()
        assert asks == [(15000, 200), (16000, 100), (17000, 300)]

    def test_aggregated_quantity_at_same_price(self):
        book = OrderBook(make_config())
        book.process_order(make_order(Side.BUY, 15000, 100))
        book.process_order(make_order(Side.BUY, 15000, 200))

        bids = book.bids()
        assert bids == [(15000, 300)]

    def test_book_updates_generated(self):
        """Verify book updates are generated for matching and resting."""
        book = OrderBook(make_config())
        result = book.process_order(make_order(Side.BUY, 15000, 100))
        assert len(result.book_updates) >= 1
        assert result.book_updates[0]["side"] == "BUY"
        assert result.book_updates[0]["price"] == 15000
        assert result.book_updates[0]["quantity"] == 100


class TestExecReports:
    def test_new_order_exec_report(self):
        book = OrderBook(make_config())
        result = book.process_order(make_order(Side.BUY, 15000, 100, cl_ord_id="C1"))

        assert len(result.exec_reports) == 1
        er = result.exec_reports[0]
        assert er.cl_ord_id == "C1"
        assert er.exec_type == ExecType.NEW
        assert er.ord_status == OrdStatus.NEW
        assert er.leaves_qty == 100
        assert er.cum_qty == 0

    def test_fill_generates_two_reports(self):
        """A match generates exec reports for both buyer and seller."""
        book = OrderBook(make_config())
        book.process_order(make_order(Side.SELL, 15000, 100, cl_ord_id="S1"))
        result = book.process_order(make_order(Side.BUY, 15000, 100, cl_ord_id="B1"))

        # 2 exec reports for the trade (one for each side)
        trade_reports = [r for r in result.exec_reports if r.exec_type == ExecType.TRADE]
        assert len(trade_reports) == 2
        buyer_report = next(r for r in trade_reports if r.cl_ord_id == "B1")
        seller_report = next(r for r in trade_reports if r.cl_ord_id == "S1")
        assert buyer_report.last_px == 15000
        assert buyer_report.last_qty == 100
        assert buyer_report.ord_status == OrdStatus.FILLED
        assert seller_report.last_px == 15000
        assert seller_report.ord_status == OrdStatus.FILLED
