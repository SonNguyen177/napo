"""Tests for core data models."""

from engine.models import ExecType, ExecutionReport, OrdStatus, OrdType, Order, Side, Trade


class TestOrder:
    def test_create_limit_buy(self):
        order = Order(
            cl_ord_id="C1",
            account="ACC1",
            symbol="FPT",
            side=Side.BUY,
            ord_type=OrdType.LIMIT,
            price=55000,
            quantity=200,
        )
        assert order.status == OrdStatus.NEW
        assert order.leaves_qty == 200
        assert order.filled_qty == 0
        assert order.cum_qty == 0
        assert order.avg_px == 0.0

    def test_create_market_sell(self):
        order = Order(
            cl_ord_id="C2",
            account="ACC1",
            symbol="FPT",
            side=Side.SELL,
            ord_type=OrdType.MARKET,
            price=0,
            quantity=100,
        )
        assert order.side == Side.SELL
        assert order.ord_type == OrdType.MARKET
        assert order.price == 0

    def test_fill_partial(self):
        order = Order(
            cl_ord_id="C1", account="ACC1", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=500,
        )
        order.fill(200, 55000)
        assert order.status == OrdStatus.PARTIALLY_FILLED
        assert order.filled_qty == 200
        assert order.leaves_qty == 300
        assert order.avg_px == 55000.0

    def test_fill_complete(self):
        order = Order(
            cl_ord_id="C1", account="ACC1", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=200,
        )
        order.fill(200, 55000)
        assert order.status == OrdStatus.FILLED
        assert order.filled_qty == 200
        assert order.leaves_qty == 0

    def test_fill_multiple_prices(self):
        order = Order(
            cl_ord_id="C1", account="ACC1", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=56000, quantity=300,
        )
        order.fill(100, 55000)
        order.fill(200, 55500)
        assert order.status == OrdStatus.FILLED
        assert order.filled_qty == 300
        expected_avg = (100 * 55000 + 200 * 55500) / 300
        assert abs(order.avg_px - expected_avg) < 0.01

    def test_cancel(self):
        order = Order(
            cl_ord_id="C1", account="ACC1", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=200,
        )
        order.cancel()
        assert order.status == OrdStatus.CANCELLED
        assert order.leaves_qty == 0

    def test_reject(self):
        order = Order(
            cl_ord_id="C1", account="ACC1", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=200,
        )
        order.reject()
        assert order.status == OrdStatus.REJECTED
        assert order.leaves_qty == 0

    def test_partial_fill_then_cancel(self):
        order = Order(
            cl_ord_id="C1", account="ACC1", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=500,
        )
        order.fill(200, 55000)
        assert order.status == OrdStatus.PARTIALLY_FILLED
        order.cancel()
        assert order.status == OrdStatus.CANCELLED
        assert order.filled_qty == 200
        assert order.leaves_qty == 0


class TestTrade:
    def test_create_trade(self):
        trade = Trade(
            trade_id="T1",
            symbol="FPT",
            price=55000,
            quantity=100,
            buy_order_id="ORD-1",
            sell_order_id="ORD-2",
            buy_cl_ord_id="C1",
            sell_cl_ord_id="C2",
        )
        assert trade.price == 55000
        assert trade.quantity == 100
        assert trade.timestamp > 0


class TestExecutionReport:
    def test_create_new_report(self):
        report = ExecutionReport(
            cl_ord_id="C1",
            order_id="ORD-1",
            exec_id="E1",
            exec_type=ExecType.NEW,
            ord_status=OrdStatus.NEW,
            symbol="FPT",
            side=Side.BUY,
            price=55000,
            quantity=200,
            leaves_qty=200,
            cum_qty=0,
            avg_px=0.0,
        )
        assert report.exec_type == ExecType.NEW
        assert report.last_px == 0
        assert report.last_qty == 0

    def test_create_trade_report(self):
        report = ExecutionReport(
            cl_ord_id="C1",
            order_id="ORD-1",
            exec_id="E2",
            exec_type=ExecType.TRADE,
            ord_status=OrdStatus.FILLED,
            symbol="FPT",
            side=Side.BUY,
            price=55000,
            quantity=200,
            leaves_qty=0,
            cum_qty=200,
            avg_px=55000.0,
            last_px=55000,
            last_qty=200,
        )
        assert report.exec_type == ExecType.TRADE
        assert report.last_px == 55000
