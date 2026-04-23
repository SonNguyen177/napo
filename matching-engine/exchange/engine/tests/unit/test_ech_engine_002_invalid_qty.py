"""Regression tests for ECH-ENGINE-002.

Bug: a WS client can kill the engine process by sending `quantity <= 0`
(or `price < 0`). The WS handler casts the raw value with `int(...)` and
forwards it to `MatchingEngine.submit_order`, which calls `os._exit(1)`
on the envelope guard. This is a DoS: a single malformed client message
wipes all in-RAM state (order books, trades, stock config, comm logs).

Fix contract: `_handle_new_order` must reject invalid quantity/price at
the WS boundary with a structured `error` message — `submit_order` must
NOT be called, and `os._exit` must NOT fire.
"""

import json

from engine.matching import MatchingEngine
from engine.ws_server import ExchangeWSServer


class FakeWS:
    """Minimal stand-in for `websockets.asyncio.server.ServerConnection`."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)


def _build_server() -> tuple[ExchangeWSServer, MatchingEngine, list]:
    engine = MatchingEngine()
    engine.config.open_market()
    srv = ExchangeWSServer(engine=engine, host="127.0.0.1", port=0)

    submit_calls: list = []
    original_submit = engine.submit_order

    def spy(order):
        submit_calls.append(order)
        return original_submit(order)

    engine.submit_order = spy  # type: ignore[assignment]
    return srv, engine, submit_calls


def _received_error(ws: FakeWS) -> dict | None:
    for raw in ws.sent:
        msg = json.loads(raw)
        if msg.get("type") == "error":
            return msg
    return None


async def test_negative_quantity_is_rejected_at_ws_boundary(monkeypatch):
    """quantity=-1 must NOT trip the engine's os._exit envelope guard."""
    exit_calls: list[int] = []
    monkeypatch.setattr("os._exit", lambda code: exit_calls.append(code))

    srv, _engine, submit_calls = _build_server()
    ws = FakeWS()

    await srv._handle_new_order(ws, client_id="CLIENT-1", data={
        "cl_ord_id": "DOS-NEG",
        "account": "ATTACKER",
        "symbol": "ACB",
        "side": "BUY",
        "ord_type": "LIMIT",
        "price": 25000,
        "quantity": -1,
    })

    assert exit_calls == [], (
        f"Engine killed by malformed client input: os._exit called with {exit_calls}"
    )
    assert submit_calls == [], (
        "submit_order must not be invoked for non-positive quantity"
    )
    err = _received_error(ws)
    assert err is not None, "client should receive an error message"
    assert "quantity" in err["message"].lower()


async def test_zero_quantity_is_rejected_at_ws_boundary(monkeypatch):
    """quantity=0 must NOT trip the engine's os._exit envelope guard."""
    exit_calls: list[int] = []
    monkeypatch.setattr("os._exit", lambda code: exit_calls.append(code))

    srv, _engine, submit_calls = _build_server()
    ws = FakeWS()

    await srv._handle_new_order(ws, client_id="CLIENT-2", data={
        "cl_ord_id": "DOS-ZERO",
        "account": "ATTACKER",
        "symbol": "ACB",
        "side": "SELL",
        "ord_type": "LIMIT",
        "price": 25000,
        "quantity": 0,
    })

    assert exit_calls == []
    assert submit_calls == []
    err = _received_error(ws)
    assert err is not None
    assert "quantity" in err["message"].lower()
