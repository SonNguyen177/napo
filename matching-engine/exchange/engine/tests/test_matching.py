"""Tests for the matching engine (multi-stock routing, market state)."""

from engine.config import ExchangeConfig
from engine.matching import MatchingEngine
from engine.models import ExecType, OrdStatus, OrdType, Order, Side


def make_order(
    symbol: str = "FPT",
    side: Side = Side.BUY,
    price: int = 55000,
    quantity: int = 100,
    ord_type: OrdType = OrdType.LIMIT,
    cl_ord_id: str = "",
    account: str = "ACC1",
) -> Order:
    return Order(
        cl_ord_id=cl_ord_id or f"C-{symbol}-{side.value}-{price}",
        account=account,
        symbol=symbol,
        side=side,
        ord_type=ord_type,
        price=price,
        quantity=quantity,
    )


class TestMarketState:
    def test_reject_when_market_closed(self):
        engine = MatchingEngine()
        assert not engine.config.is_open()
        order = make_order()
        result = engine.submit_order(order)

        assert order.status == OrdStatus.REJECTED
        assert result.exec_reports[0].exec_type == ExecType.REJECTED
        assert "closed" in result.exec_reports[0].reject_reason.lower()

    def test_accept_when_market_open(self):
        engine = MatchingEngine()
        engine.config.open_market()
        order = make_order()
        result = engine.submit_order(order)

        assert order.status == OrdStatus.NEW
        assert result.exec_reports[0].exec_type == ExecType.NEW

    def test_open_then_close_rejects(self):
        engine = MatchingEngine()
        engine.config.open_market()
        engine.submit_order(make_order(cl_ord_id="C1"))

        engine.config.close_market()
        order = make_order(cl_ord_id="C2")
        result = engine.submit_order(order)

        assert order.status == OrdStatus.REJECTED
        assert "closed" in result.exec_reports[0].reject_reason.lower()


class TestSymbolRouting:
    def test_reject_unknown_symbol(self):
        engine = MatchingEngine()
        engine.config.open_market()
        order = make_order(symbol="UNKNOWN")
        result = engine.submit_order(order)

        assert order.status == OrdStatus.REJECTED
        assert "Unknown symbol" in result.exec_reports[0].reject_reason

    def test_route_to_correct_book(self):
        engine = MatchingEngine()
        engine.config.open_market()

        # Place orders on different stocks
        engine.submit_order(make_order(symbol="ACB", side=Side.BUY, price=25000, cl_ord_id="ACB-B"))
        engine.submit_order(make_order(symbol="FPT", side=Side.BUY, price=55000, cl_ord_id="FPT-B"))
        engine.submit_order(make_order(symbol="VCK", side=Side.BUY, price=12000, cl_ord_id="VCK-B"))

        acb_book = engine.get_order_book("ACB")
        fpt_book = engine.get_order_book("FPT")
        vck_book = engine.get_order_book("VCK")

        assert acb_book.best_bid == 25000
        assert fpt_book.best_bid == 55000
        assert vck_book.best_bid == 12000

    def test_multi_stock_isolation(self):
        """A trade in ACB should not affect FPT's book."""
        engine = MatchingEngine()
        engine.config.open_market()

        # Set up FPT book
        engine.submit_order(make_order(symbol="FPT", side=Side.SELL, price=55000, cl_ord_id="FPT-S"))
        engine.submit_order(make_order(symbol="FPT", side=Side.BUY, price=54000, cl_ord_id="FPT-B"))

        # Trade in ACB
        engine.submit_order(make_order(symbol="ACB", side=Side.SELL, price=25000, cl_ord_id="ACB-S"))
        result = engine.submit_order(make_order(symbol="ACB", side=Side.BUY, price=25000, cl_ord_id="ACB-B"))

        # ACB trade happened
        assert len(result.trades) == 1
        assert result.trades[0].symbol == "ACB"

        # FPT book unchanged
        fpt_book = engine.get_order_book("FPT")
        assert fpt_book.best_ask == 55000
        assert fpt_book.best_bid == 54000


class TestExecReports:
    def test_new_order_report(self):
        engine = MatchingEngine()
        engine.config.open_market()
        result = engine.submit_order(make_order(cl_ord_id="C1"))

        er = result.exec_reports[0]
        assert er.cl_ord_id == "C1"
        assert er.exec_type == ExecType.NEW
        assert er.ord_status == OrdStatus.NEW
        assert er.symbol == "FPT"
        assert er.side == Side.BUY
        assert er.leaves_qty == 100
        assert er.cum_qty == 0

    def test_fill_reports(self):
        engine = MatchingEngine()
        engine.config.open_market()

        engine.submit_order(make_order(side=Side.SELL, price=55000, quantity=100, cl_ord_id="S1"))
        result = engine.submit_order(make_order(side=Side.BUY, price=55000, quantity=100, cl_ord_id="B1"))

        trade_reports = [r for r in result.exec_reports if r.exec_type == ExecType.TRADE]
        assert len(trade_reports) == 2

        buyer = next(r for r in trade_reports if r.cl_ord_id == "B1")
        seller = next(r for r in trade_reports if r.cl_ord_id == "S1")

        assert buyer.ord_status == OrdStatus.FILLED
        assert buyer.last_px == 55000
        assert buyer.last_qty == 100
        assert buyer.leaves_qty == 0
        assert buyer.cum_qty == 100

        assert seller.ord_status == OrdStatus.FILLED
        assert seller.last_px == 55000

    def test_partial_fill_reports(self):
        engine = MatchingEngine()
        engine.config.open_market()

        engine.submit_order(make_order(side=Side.SELL, price=55000, quantity=100, cl_ord_id="S1"))
        result = engine.submit_order(make_order(side=Side.BUY, price=55000, quantity=300, cl_ord_id="B1"))

        trade_reports = [r for r in result.exec_reports if r.exec_type == ExecType.TRADE]
        buyer_report = next(r for r in trade_reports if r.cl_ord_id == "B1")

        assert buyer_report.ord_status == OrdStatus.PARTIALLY_FILLED
        assert buyer_report.last_qty == 100
        assert buyer_report.leaves_qty == 200
        assert buyer_report.cum_qty == 100

    def test_market_order_across_levels(self):
        engine = MatchingEngine()
        engine.config.open_market()

        engine.submit_order(make_order(side=Side.SELL, price=55000, quantity=100, cl_ord_id="S1"))
        engine.submit_order(make_order(side=Side.SELL, price=55500, quantity=100, cl_ord_id="S2"))

        order = make_order(side=Side.BUY, price=0, quantity=200, ord_type=OrdType.MARKET, cl_ord_id="B1")
        result = engine.submit_order(order)

        assert len(result.trades) == 2
        assert result.trades[0].price == 55000
        assert result.trades[1].price == 55500
        assert order.status == OrdStatus.FILLED


class TestTradeHistory:
    def test_trades_recorded(self):
        engine = MatchingEngine()
        engine.config.open_market()

        engine.submit_order(make_order(side=Side.SELL, price=55000, quantity=100, cl_ord_id="S1"))
        engine.submit_order(make_order(side=Side.BUY, price=55000, quantity=100, cl_ord_id="B1"))

        trades = engine.get_trades()
        assert len(trades) == 1
        assert trades[0].symbol == "FPT"
        assert trades[0].price == 55000

    def test_trades_filtered_by_symbol(self):
        engine = MatchingEngine()
        engine.config.open_market()

        # FPT trade
        engine.submit_order(make_order(symbol="FPT", side=Side.SELL, price=55000, quantity=100, cl_ord_id="FS1"))
        engine.submit_order(make_order(symbol="FPT", side=Side.BUY, price=55000, quantity=100, cl_ord_id="FB1"))

        # ACB trade
        engine.submit_order(make_order(symbol="ACB", side=Side.SELL, price=25000, quantity=100, cl_ord_id="AS1"))
        engine.submit_order(make_order(symbol="ACB", side=Side.BUY, price=25000, quantity=100, cl_ord_id="AB1"))

        all_trades = engine.get_trades()
        assert len(all_trades) == 2

        fpt_trades = engine.get_trades("FPT")
        assert len(fpt_trades) == 1
        assert fpt_trades[0].symbol == "FPT"

        acb_trades = engine.get_trades("ACB")
        assert len(acb_trades) == 1
        assert acb_trades[0].symbol == "ACB"

    def test_no_trades_for_unknown_symbol(self):
        engine = MatchingEngine()
        assert engine.get_trades("UNKNOWN") == []


class TestStockConfigUpdate:
    def test_update_ceiling(self):
        engine = MatchingEngine()
        engine.config.open_market()

        updated = engine.update_stock_config("FPT", ceiling=80000)
        assert updated is not None
        assert updated.ceiling == 80000

        # New ceiling enforced
        order = make_order(price=77000)
        result = engine.submit_order(order)
        assert order.status == OrdStatus.NEW

    def test_update_enforces_new_floor(self):
        engine = MatchingEngine()
        engine.config.open_market()

        engine.update_stock_config("FPT", floor=52000)

        # Order below new floor rejected
        order = make_order(price=50000)
        result = engine.submit_order(order)
        assert order.status == OrdStatus.REJECTED
        assert "below floor" in result.exec_reports[0].reject_reason

    def test_update_price_step(self):
        engine = MatchingEngine()
        engine.config.open_market()

        engine.update_stock_config("FPT", price_step=1000)

        # 55000 is valid with step 1000 (from floor 50000)
        order = make_order(price=55000, cl_ord_id="C1")
        result = engine.submit_order(order)
        assert order.status == OrdStatus.NEW

        # 55500 is invalid with step 1000
        order2 = make_order(price=55500, cl_ord_id="C2")
        result2 = engine.submit_order(order2)
        assert order2.status == OrdStatus.REJECTED

    def test_update_unknown_symbol(self):
        engine = MatchingEngine()
        result = engine.update_stock_config("UNKNOWN", ceiling=99999)
        assert result is None

    def test_get_all_books(self):
        engine = MatchingEngine()
        books = engine.get_all_books()
        assert set(books.keys()) == {"ACB", "FPT", "VCK"}
