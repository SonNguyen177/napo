"""Regression tests for ECH-ENGINE-005.

Bug: `_handle_new_order` only catches ``(KeyError, ValueError)``. When a
client sends a payload with wrong JSON types — e.g. ``price`` / ``quantity``
as a list or dict, or ``side`` / ``symbol`` as a non-string — the casts
``int(...)`` and ``str.upper()`` raise ``TypeError`` / ``AttributeError``
respectively. These escape the handler, bubble up through ``_handle_client``,
and the WS connection is dropped on the client with no structured
``error`` message. Bad UX, debug-hostile, and exploitable for
disconnection floods.

Fix contract: `_handle_new_order` must catch these type errors at the WS
boundary, send a structured ``{"type": "error", ...}`` back to the
client, and return normally so the connection stays open.
"""

import json

from engine.matching import MatchingEngine
from engine.ws_server import ExchangeWSServer


class FakeWS:
    """Minimal stand-in for ``websockets.asyncio.server.ServerConnection``."""

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


async def test_price_as_list_does_not_crash_handler():
    """price as a JSON array triggers TypeError in int(...) — handler must survive."""
    srv, _engine, submit_calls = _build_server()
    ws = FakeWS()

    await srv._handle_new_order(ws, client_id="CLIENT-1", data={
        "cl_ord_id": "BAD-PX-LIST",
        "account": "CLIENT",
        "symbol": "ACB",
        "side": "BUY",
        "ord_type": "LIMIT",
        "price": [1, 2],
        "quantity": 100,
    })

    assert submit_calls == [], "submit_order must not be invoked for malformed payload"
    err = _received_error(ws)
    assert err is not None, "client should receive a structured error message"
    assert "invalid order" in err["message"].lower()


async def test_quantity_as_dict_does_not_crash_handler():
    """quantity as a JSON object triggers TypeError in int(...) — handler must survive."""
    srv, _engine, submit_calls = _build_server()
    ws = FakeWS()

    await srv._handle_new_order(ws, client_id="CLIENT-2", data={
        "cl_ord_id": "BAD-QTY-DICT",
        "account": "CLIENT",
        "symbol": "ACB",
        "side": "SELL",
        "ord_type": "LIMIT",
        "price": 25000,
        "quantity": {"bad": "payload"},
    })

    assert submit_calls == []
    err = _received_error(ws)
    assert err is not None
    assert "invalid order" in err["message"].lower()


async def test_side_as_non_string_does_not_crash_handler():
    """side as an int triggers AttributeError on .upper() — handler must survive."""
    srv, _engine, submit_calls = _build_server()
    ws = FakeWS()

    await srv._handle_new_order(ws, client_id="CLIENT-3", data={
        "cl_ord_id": "BAD-SIDE-INT",
        "account": "CLIENT",
        "symbol": "ACB",
        "side": 1,
        "ord_type": "LIMIT",
        "price": 25000,
        "quantity": 100,
    })

    assert submit_calls == []
    err = _received_error(ws)
    assert err is not None
    assert "invalid order" in err["message"].lower()
