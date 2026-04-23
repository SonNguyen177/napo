"""Tests for the FastAPI admin REST API."""

import pytest
from httpx import ASGITransport, AsyncClient

from engine.api import create_app
from engine.matching import MatchingEngine
from engine.models import OrdType, Order, Side
from engine.ws_server import ExchangeWSServer


@pytest.fixture
def engine():
    return MatchingEngine()


@pytest.fixture
def ws_server(engine):
    return ExchangeWSServer(engine=engine, host="127.0.0.1", port=0)


@pytest.fixture
def app(engine, ws_server):
    return create_app(engine=engine, ws_server=ws_server)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestMarketControl:
    async def test_start_market(self, client, engine):
        resp = await client.post("/api/market/start")
        assert resp.status_code == 200
        assert resp.json()["state"] == "OPEN"
        assert engine.config.is_open()

    async def test_stop_market(self, client, engine):
        engine.config.open_market()
        resp = await client.post("/api/market/stop")
        assert resp.status_code == 200
        assert resp.json()["state"] == "CLOSED"
        assert not engine.config.is_open()

    async def test_get_market_state(self, client):
        resp = await client.get("/api/market/state")
        assert resp.status_code == 200
        assert resp.json()["state"] == "CLOSED"

    async def test_start_then_stop(self, client):
        await client.post("/api/market/start")
        resp = await client.get("/api/market/state")
        assert resp.json()["state"] == "OPEN"

        await client.post("/api/market/stop")
        resp = await client.get("/api/market/state")
        assert resp.json()["state"] == "CLOSED"


class TestStockConfig:
    async def test_list_stocks(self, client):
        resp = await client.get("/api/stocks")
        assert resp.status_code == 200
        stocks = resp.json()
        assert len(stocks) == 3
        symbols = {s["symbol"] for s in stocks}
        assert symbols == {"ACB", "FPT", "VCK"}

    async def test_get_stock(self, client):
        resp = await client.get("/api/stocks/FPT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "FPT"
        assert data["floor"] == 50000
        assert data["ceiling"] == 75000
        assert data["price_step"] == 500
        assert data["qty_step"] == 100

    async def test_get_stock_case_insensitive(self, client):
        resp = await client.get("/api/stocks/fpt")
        assert resp.status_code == 200
        assert resp.json()["symbol"] == "FPT"

    async def test_get_unknown_stock(self, client):
        resp = await client.get("/api/stocks/UNKNOWN")
        assert resp.status_code == 404

    async def test_update_stock(self, client, engine):
        resp = await client.put("/api/stocks/FPT", json={"ceiling": 80000})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ceiling"] == 80000
        assert engine.config.get_stock("FPT").ceiling == 80000

    async def test_update_multiple_fields(self, client):
        resp = await client.put("/api/stocks/ACB", json={
            "floor": 18000,
            "ceiling": 35000,
            "price_step": 200,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["floor"] == 18000
        assert data["ceiling"] == 35000
        assert data["price_step"] == 200

    async def test_update_invalid_value(self, client):
        resp = await client.put("/api/stocks/FPT", json={"ceiling": -100})
        assert resp.status_code == 422  # Pydantic validation error

    async def test_update_no_fields(self, client):
        resp = await client.put("/api/stocks/FPT", json={})
        assert resp.status_code == 400

    async def test_update_unknown_stock(self, client):
        resp = await client.put("/api/stocks/UNKNOWN", json={"ceiling": 99999})
        assert resp.status_code == 404


class TestOrderBook:
    async def test_get_empty_orderbook(self, client):
        resp = await client.get("/api/orderbook/FPT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "FPT"
        assert data["bids"] == []
        assert data["asks"] == []

    async def test_get_orderbook_with_orders(self, client, engine):
        engine.config.open_market()
        engine.submit_order(Order(
            cl_ord_id="B1", account="A", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        ))
        engine.submit_order(Order(
            cl_ord_id="S1", account="A", symbol="FPT",
            side=Side.SELL, ord_type=OrdType.LIMIT, price=60000, quantity=200,
        ))

        resp = await client.get("/api/orderbook/FPT")
        data = resp.json()
        assert data["bids"] == [[55000, 100]]
        assert data["asks"] == [[60000, 200]]

    async def test_get_orderbook_unknown_symbol(self, client):
        resp = await client.get("/api/orderbook/UNKNOWN")
        assert resp.status_code == 404


class TestTrades:
    async def test_get_trades_empty(self, client):
        resp = await client.get("/api/trades")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_trades_with_data(self, client, engine):
        engine.config.open_market()
        engine.submit_order(Order(
            cl_ord_id="S1", account="A", symbol="FPT",
            side=Side.SELL, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        ))
        engine.submit_order(Order(
            cl_ord_id="B1", account="A", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        ))

        resp = await client.get("/api/trades")
        trades = resp.json()
        assert len(trades) == 1
        assert trades[0]["symbol"] == "FPT"
        assert trades[0]["price"] == 55000
        assert trades[0]["quantity"] == 100

    async def test_get_trades_filter_by_symbol(self, client, engine):
        engine.config.open_market()
        # FPT trade
        engine.submit_order(Order(
            cl_ord_id="FS1", account="A", symbol="FPT",
            side=Side.SELL, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        ))
        engine.submit_order(Order(
            cl_ord_id="FB1", account="A", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        ))
        # ACB trade
        engine.submit_order(Order(
            cl_ord_id="AS1", account="A", symbol="ACB",
            side=Side.SELL, ord_type=OrdType.LIMIT, price=25000, quantity=100,
        ))
        engine.submit_order(Order(
            cl_ord_id="AB1", account="A", symbol="ACB",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=25000, quantity=100,
        ))

        resp = await client.get("/api/trades?symbol=FPT")
        trades = resp.json()
        assert len(trades) == 1
        assert trades[0]["symbol"] == "FPT"

        resp = await client.get("/api/trades?symbol=ACB")
        trades = resp.json()
        assert len(trades) == 1
        assert trades[0]["symbol"] == "ACB"


class TestLogs:
    async def test_get_logs_empty(self, client):
        resp = await client.get("/api/logs")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_logs_with_limit(self, client, ws_server):
        # Manually add some logs
        from engine.ws_server import CommLog
        import time
        for i in range(10):
            ws_server._comm_logs.append(CommLog(
                timestamp=time.time(),
                direction="IN",
                client_id=f"C-{i}",
                message_type="test",
                summary=f"Log {i}",
            ))

        resp = await client.get("/api/logs?limit=5")
        logs = resp.json()
        assert len(logs) == 5
        # Should be the last 5
        assert logs[0]["summary"] == "Log 5"


class TestClientCount:
    async def test_get_client_count(self, client):
        resp = await client.get("/api/clients")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestOrdersRejectedAfterStop:
    async def test_orders_rejected_after_market_stop(self, client, engine):
        # Start market, place an order
        await client.post("/api/market/start")
        engine.submit_order(Order(
            cl_ord_id="B1", account="A", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        ))

        # Stop market
        await client.post("/api/market/stop")

        # Try to place another order directly via engine
        order = Order(
            cl_ord_id="B2", account="A", symbol="FPT",
            side=Side.BUY, ord_type=OrdType.LIMIT, price=55000, quantity=100,
        )
        result = engine.submit_order(order)
        assert result.exec_reports[0].reject_reason == "Market is closed"
