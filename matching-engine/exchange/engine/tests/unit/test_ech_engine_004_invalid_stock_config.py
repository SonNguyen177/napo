"""Regression tests for ECH-ENGINE-004.

Bug: `PUT /api/stocks/{symbol}` accepts updates that leave the stock in a
degenerate state (e.g. `ceiling <= floor`). `StockConfigUpdate` only
checks each field is positive, and `MatchingEngine.update_stock_config`
setattrs each field without cross-field validation. The next order on
that symbol then trips the envelope guard
`if book.config.ceiling <= book.config.floor` in
`MatchingEngine.submit_order` and the engine calls `os._exit(1)`,
wiping all in-RAM state.

Because the admin API has no auth, anyone reachable on port 8000 can
take down the whole exchange with one PUT.

Fix contract:
  * `MatchingEngine.update_stock_config` must validate cross-field
    invariants (`ceiling > floor`, both steps `> 0`, `(ceiling - floor)
    % price_step == 0`). On violation it MUST rollback to the prior
    config and signal the error.
  * `PUT /api/stocks/{symbol}` must surface that as HTTP 400, leaving
    the stock unchanged so a subsequent order does NOT trip
    `os._exit`.
"""

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


async def test_put_ceiling_below_floor_is_rejected(client, engine):
    """ACB defaults: floor=20000, ceiling=30000. Lower ceiling to 10 → must 4xx."""
    resp = await client.put("/api/stocks/ACB", json={"ceiling": 10})
    assert resp.status_code == 400, (
        f"Expected 400 for degenerate ceiling, got {resp.status_code}: {resp.text}"
    )

    stock = engine.config.get_stock("ACB")
    assert stock is not None
    assert stock.ceiling == 30000, (
        f"Stock ceiling must be unchanged after rejected update, got {stock.ceiling}"
    )
    assert stock.floor == 20000


async def test_put_floor_above_ceiling_is_rejected(client, engine):
    """Raising floor above current ceiling must 4xx and rollback."""
    resp = await client.put("/api/stocks/ACB", json={"floor": 99999})
    assert resp.status_code == 400, resp.text
    stock = engine.config.get_stock("ACB")
    assert stock.floor == 20000
    assert stock.ceiling == 30000


async def test_engine_survives_after_rejected_admin_update(client, engine, monkeypatch):
    """The smoking gun: after a bad PUT, submitting an order must NOT fire os._exit."""
    exit_calls: list[int] = []
    monkeypatch.setattr("os._exit", lambda code: exit_calls.append(code))

    # 1. Attempt malicious update (ceiling < floor).
    resp = await client.put("/api/stocks/ACB", json={"ceiling": 10, "floor": 5000})
    assert resp.status_code == 400, resp.text

    # 2. Open market and submit a perfectly valid order.
    engine.config.open_market()
    order = Order(
        cl_ord_id="OK-1",
        account="A",
        symbol="ACB",
        side=Side.BUY,
        ord_type=OrdType.LIMIT,
        price=25000,
        quantity=100,
    )
    engine.submit_order(order)

    assert exit_calls == [], (
        f"Engine killed by stale ceiling<=floor: os._exit called with {exit_calls}"
    )


def test_update_stock_config_rejects_ceiling_le_floor(engine):
    """Direct call: setting ceiling <= floor must error and not mutate state."""
    with pytest.raises(ValueError, match="(?i)ceiling"):
        engine.update_stock_config("ACB", ceiling=10)

    stock = engine.config.get_stock("ACB")
    assert stock.ceiling == 30000


def test_update_stock_config_rejects_misaligned_step(engine):
    """`(ceiling - floor) % price_step == 0` must hold after update."""
    # ACB defaults: floor=20000, ceiling=30000, price_step=100 → range=10000 % 100 == 0.
    # Setting price_step=300 makes 10000 % 300 != 0.
    with pytest.raises(ValueError, match="(?i)step"):
        engine.update_stock_config("ACB", price_step=300)

    stock = engine.config.get_stock("ACB")
    assert stock.price_step == 100
