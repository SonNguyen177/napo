"""Integration tests for the WebSocket server."""

import asyncio
import json

import pytest
import websockets
from websockets.asyncio.client import connect

from engine.matching import MatchingEngine
from engine.ws_server import ExchangeWSServer


@pytest.fixture
async def server():
    """Start a WS server on a random port, yield it, then stop."""
    engine = MatchingEngine()
    engine.config.open_market()
    srv = ExchangeWSServer(engine=engine, host="127.0.0.1", port=0)
    ws_server = await srv.start()
    # Get the actual port assigned
    port = ws_server.sockets[0].getsockname()[1]
    srv._test_port = port
    yield srv
    await srv.stop()


def url(server: ExchangeWSServer) -> str:
    return f"ws://127.0.0.1:{server._test_port}"


async def recv_json(ws, timeout: float = 2.0) -> dict:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def recv_all(ws, count: int, timeout: float = 2.0) -> list[dict]:
    msgs = []
    for _ in range(count):
        msgs.append(await recv_json(ws, timeout))
    return msgs


@pytest.mark.asyncio
async def test_connect_receives_snapshot(server):
    """Client connects and receives market snapshots for all 3 stocks."""
    async with connect(url(server)) as ws:
        snapshots = await recv_all(ws, 3)
        symbols = {s["symbol"] for s in snapshots}
        assert symbols == {"ACB", "FPT", "VCK"}
        for s in snapshots:
            assert s["type"] == "market_snapshot"
            assert "floor" in s
            assert "ceiling" in s
            assert "bids" in s
            assert "asks" in s
            assert s["market_state"] == "OPEN"


@pytest.mark.asyncio
async def test_place_valid_order(server):
    """Client sends valid order and receives execution report."""
    async with connect(url(server)) as ws:
        # Consume snapshots
        await recv_all(ws, 3)

        await ws.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "TEST-001",
            "account": "ACC1",
            "symbol": "FPT",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 55000,
            "quantity": 100,
        }))

        # Should receive execution report (NEW) + market_update
        msg = await recv_json(ws)
        assert msg["type"] == "execution_report"
        assert msg["cl_ord_id"] == "TEST-001"
        assert msg["exec_type"] == "NEW"
        assert msg["ord_status"] == "NEW"
        assert msg["symbol"] == "FPT"


@pytest.mark.asyncio
async def test_place_invalid_order(server):
    """Client sends invalid order and receives rejection."""
    async with connect(url(server)) as ws:
        await recv_all(ws, 3)

        # Invalid price (above ceiling for FPT which is 75000)
        await ws.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "TEST-BAD",
            "account": "ACC1",
            "symbol": "FPT",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 99000,
            "quantity": 100,
        }))

        msg = await recv_json(ws)
        assert msg["type"] == "execution_report"
        assert msg["exec_type"] == "REJECTED"
        assert "ceiling" in msg["reject_reason"]


@pytest.mark.asyncio
async def test_order_matching_both_parties(server):
    """Two clients place matching orders, both receive execution reports."""
    async with connect(url(server)) as ws1, connect(url(server)) as ws2:
        # Consume snapshots
        await recv_all(ws1, 3)
        await recv_all(ws2, 3)

        # Client 1 places sell
        await ws1.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "SELL-001",
            "account": "SELLER",
            "symbol": "FPT",
            "side": "SELL",
            "ord_type": "LIMIT",
            "price": 55000,
            "quantity": 100,
        }))

        # ws1 gets NEW exec report + market update
        sell_new = await recv_json(ws1)
        assert sell_new["type"] == "execution_report"
        assert sell_new["exec_type"] == "NEW"

        # ws2 gets market update (broadcast)
        ws2_update = await recv_json(ws2)
        assert ws2_update["type"] == "market_update"

        # Client 2 places matching buy
        await ws2.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "BUY-001",
            "account": "BUYER",
            "symbol": "FPT",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 55000,
            "quantity": 100,
        }))

        # ws2 should receive: exec report (TRADE for buyer)
        # ws1 and ws2 should both receive: exec report (TRADE for seller), trade broadcast, market update
        # Collect several messages from ws2
        ws2_msgs = []
        for _ in range(4):
            try:
                msg = await recv_json(ws2, timeout=2.0)
                ws2_msgs.append(msg)
            except asyncio.TimeoutError:
                break

        # Check ws2 got a trade exec report for BUY-001
        buyer_trades = [m for m in ws2_msgs if m.get("type") == "execution_report" and m.get("cl_ord_id") == "BUY-001" and m.get("exec_type") == "TRADE"]
        assert len(buyer_trades) == 1
        assert buyer_trades[0]["ord_status"] == "FILLED"
        assert buyer_trades[0]["last_px"] == 55000

        # Check ws2 got trade broadcast
        trade_msgs = [m for m in ws2_msgs if m.get("type") == "trade"]
        assert len(trade_msgs) == 1
        assert trade_msgs[0]["price"] == 55000


@pytest.mark.asyncio
async def test_market_update_broadcast(server):
    """All connected clients receive market updates when order book changes."""
    async with connect(url(server)) as ws1, connect(url(server)) as ws2:
        await recv_all(ws1, 3)
        await recv_all(ws2, 3)

        # ws1 places order
        await ws1.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "ORD-1",
            "account": "ACC1",
            "symbol": "ACB",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 25000,
            "quantity": 100,
        }))

        # ws1 gets exec report
        msg1 = await recv_json(ws1)
        assert msg1["type"] == "execution_report"

        # ws2 gets market update
        msg2 = await recv_json(ws2)
        assert msg2["type"] == "market_update"
        assert msg2["symbol"] == "ACB"
        assert msg2["side"] == "BUY"
        assert msg2["price"] == 25000
        assert msg2["quantity"] == 100


@pytest.mark.asyncio
async def test_trade_broadcast_to_all(server):
    """Trade is broadcast to all connected clients."""
    async with connect(url(server)) as ws1, connect(url(server)) as ws2, connect(url(server)) as ws3:
        await recv_all(ws1, 3)
        await recv_all(ws2, 3)
        await recv_all(ws3, 3)

        # ws1 sells
        await ws1.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "S1",
            "symbol": "VCK",
            "side": "SELL",
            "ord_type": "LIMIT",
            "price": 12000,
            "quantity": 100,
        }))
        await recv_json(ws1)  # NEW exec report

        # Drain market update from ws2, ws3
        await recv_json(ws2)
        await recv_json(ws3)

        # ws2 buys (match)
        await ws2.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "B1",
            "symbol": "VCK",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 12000,
            "quantity": 100,
        }))

        # ws3 (observer) should receive trade broadcast
        ws3_msgs = []
        for _ in range(5):
            try:
                msg = await recv_json(ws3, timeout=2.0)
                ws3_msgs.append(msg)
            except asyncio.TimeoutError:
                break

        trade_msgs = [m for m in ws3_msgs if m.get("type") == "trade"]
        assert len(trade_msgs) == 1
        assert trade_msgs[0]["symbol"] == "VCK"
        assert trade_msgs[0]["price"] == 12000


@pytest.mark.asyncio
async def test_multiple_clients_connected(server):
    """Multiple clients can connect simultaneously."""
    async with connect(url(server)) as ws1, connect(url(server)) as ws2, connect(url(server)) as ws3:
        await recv_all(ws1, 3)
        await recv_all(ws2, 3)
        await recv_all(ws3, 3)
        assert server.client_count == 3


@pytest.mark.asyncio
async def test_client_disconnect_cleanup(server):
    """Client count decreases after disconnect."""
    ws = await connect(url(server))
    await recv_all(ws, 3)
    assert server.client_count == 1

    await ws.close()
    # Give server time to process disconnect
    await asyncio.sleep(0.1)
    assert server.client_count == 0


@pytest.mark.asyncio
async def test_connection_count_tracked(server):
    """Connection count reflects actual connections."""
    assert server.client_count == 0

    ws1 = await connect(url(server))
    await recv_all(ws1, 3)
    assert server.client_count == 1

    ws2 = await connect(url(server))
    await recv_all(ws2, 3)
    assert server.client_count == 2

    await ws1.close()
    await asyncio.sleep(0.1)
    assert server.client_count == 1

    await ws2.close()
    await asyncio.sleep(0.1)
    assert server.client_count == 0


@pytest.mark.asyncio
async def test_comm_log_captures_messages(server):
    """Communication log captures connect, order, and exec report events."""
    async with connect(url(server)) as ws:
        await recv_all(ws, 3)

        await ws.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "LOG-TEST",
            "account": "ACC1",
            "symbol": "FPT",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 55000,
            "quantity": 100,
        }))
        await recv_json(ws)

    await asyncio.sleep(0.1)
    logs = server.comm_logs
    types = [log.message_type for log in logs]
    assert "connect" in types
    assert "snapshot" in types
    assert "new_order" in types
    assert "execution_report" in types
    assert "disconnect" in types

    # Check FIX raw is populated for orders
    order_logs = [l for l in logs if l.message_type == "new_order"]
    assert len(order_logs) == 1
    assert "35=D" in order_logs[0].fix_raw


@pytest.mark.asyncio
async def test_invalid_json(server):
    """Server handles invalid JSON gracefully."""
    async with connect(url(server)) as ws:
        await recv_all(ws, 3)
        await ws.send("not json at all")
        msg = await recv_json(ws)
        assert msg["type"] == "error"
        assert "Invalid JSON" in msg["message"]


@pytest.mark.asyncio
async def test_unknown_message_type(server):
    """Server handles unknown message types."""
    async with connect(url(server)) as ws:
        await recv_all(ws, 3)
        await ws.send(json.dumps({"type": "bogus"}))
        msg = await recv_json(ws)
        assert msg["type"] == "error"
        assert "Unknown message type" in msg["message"]


@pytest.mark.asyncio
async def test_subscribe_resends_snapshot(server):
    """Subscribe message re-sends market snapshot."""
    async with connect(url(server)) as ws:
        await recv_all(ws, 3)

        await ws.send(json.dumps({"type": "subscribe"}))
        snapshots = await recv_all(ws, 3)
        assert all(s["type"] == "market_snapshot" for s in snapshots)


@pytest.mark.asyncio
async def test_market_closed_rejects_order(server):
    """Orders are rejected when market is closed."""
    server.engine.config.close_market()

    async with connect(url(server)) as ws:
        await recv_all(ws, 3)

        await ws.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "CLOSED-TEST",
            "symbol": "FPT",
            "side": "BUY",
            "ord_type": "LIMIT",
            "price": 55000,
            "quantity": 100,
        }))

        msg = await recv_json(ws)
        assert msg["type"] == "execution_report"
        assert msg["exec_type"] == "REJECTED"
        assert "closed" in msg["reject_reason"].lower()


@pytest.mark.asyncio
async def test_missing_order_fields(server):
    """Order with missing required fields returns error."""
    async with connect(url(server)) as ws:
        await recv_all(ws, 3)

        await ws.send(json.dumps({
            "type": "new_order",
            "cl_ord_id": "BAD-1",
            # missing symbol, side, quantity
        }))

        msg = await recv_json(ws)
        assert msg["type"] == "error"
        assert "Invalid order" in msg["message"]
