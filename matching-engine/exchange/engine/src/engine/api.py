"""FastAPI admin REST API and admin WebSocket for the exchange."""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from engine.matching import MatchingEngine
from engine.ws_server import ExchangeWSServer


# --- Pydantic models for request/response ---


class StockConfigResponse(BaseModel):
    symbol: str
    floor: int
    ceiling: int
    price_step: int
    qty_step: int


class StockConfigUpdate(BaseModel):
    floor: int | None = None
    ceiling: int | None = None
    price_step: int | None = None
    qty_step: int | None = None

    @field_validator("floor", "ceiling", "price_step", "qty_step", mode="before")
    @classmethod
    def must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Value must be positive")
        return v


class MarketStateResponse(BaseModel):
    state: str


class OrderBookResponse(BaseModel):
    symbol: str
    bids: list[list[int]]
    asks: list[list[int]]


class TradeResponse(BaseModel):
    trade_id: str
    symbol: str
    price: int
    quantity: int
    buy_order_id: str
    sell_order_id: str
    time: float


class CommLogResponse(BaseModel):
    timestamp: float
    direction: str
    client_id: str
    message_type: str
    summary: str
    fix_raw: str


class ClientCountResponse(BaseModel):
    count: int


# --- App factory ---


def create_app(
    engine: MatchingEngine | None = None,
    ws_server: ExchangeWSServer | None = None,
) -> FastAPI:
    """Create the FastAPI app with admin endpoints.

    If engine/ws_server are not provided, they are created.
    The ws_server and engine are stored on app.state for access in endpoints.
    """
    if engine is None:
        engine = MatchingEngine()
    if ws_server is None:
        ws_server = ExchangeWSServer(engine=engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start the WS server for clients
        await ws_server.start()
        yield
        await ws_server.stop()

    app = FastAPI(title="Exchange Admin API", lifespan=lifespan)
    app.state.engine = engine
    app.state.ws_server = ws_server

    # CORS for admin panel
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Market control ---

    @app.post("/api/market/start", response_model=MarketStateResponse)
    async def start_market():
        engine.config.open_market()
        return MarketStateResponse(state=engine.config.market_state.value)

    @app.post("/api/market/stop", response_model=MarketStateResponse)
    async def stop_market():
        engine.config.close_market()
        return MarketStateResponse(state=engine.config.market_state.value)

    @app.get("/api/market/state", response_model=MarketStateResponse)
    async def get_market_state():
        return MarketStateResponse(state=engine.config.market_state.value)

    # --- Stock config ---

    @app.get("/api/stocks", response_model=list[StockConfigResponse])
    async def list_stocks():
        return [
            StockConfigResponse(
                symbol=s.symbol, floor=s.floor, ceiling=s.ceiling,
                price_step=s.price_step, qty_step=s.qty_step,
            )
            for s in engine.config.stocks.values()
        ]

    @app.get("/api/stocks/{symbol}", response_model=StockConfigResponse)
    async def get_stock(symbol: str):
        config = engine.config.get_stock(symbol.upper())
        if config is None:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": f"Unknown symbol: {symbol}"})
        return StockConfigResponse(
            symbol=config.symbol, floor=config.floor, ceiling=config.ceiling,
            price_step=config.price_step, qty_step=config.qty_step,
        )

    @app.put("/api/stocks/{symbol}", response_model=StockConfigResponse)
    async def update_stock(symbol: str, body: StockConfigUpdate):
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=400, content={"detail": "No fields to update"})

        updated = engine.update_stock_config(symbol.upper(), **updates)
        if updated is None:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": f"Unknown symbol: {symbol}"})

        return StockConfigResponse(
            symbol=updated.symbol, floor=updated.floor, ceiling=updated.ceiling,
            price_step=updated.price_step, qty_step=updated.qty_step,
        )

    # --- Order book ---

    @app.get("/api/orderbook/{symbol}", response_model=OrderBookResponse)
    async def get_orderbook(symbol: str):
        book = engine.get_order_book(symbol.upper())
        if book is None:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": f"Unknown symbol: {symbol}"})
        return OrderBookResponse(
            symbol=book.symbol,
            bids=[list(b) for b in book.bids()],
            asks=[list(a) for a in book.asks()],
        )

    # --- Trades ---

    @app.get("/api/trades", response_model=list[TradeResponse])
    async def get_trades(symbol: str | None = None):
        trades = engine.get_trades(symbol.upper() if symbol else None)
        return [
            TradeResponse(
                trade_id=t.trade_id, symbol=t.symbol, price=t.price,
                quantity=t.quantity, buy_order_id=t.buy_order_id,
                sell_order_id=t.sell_order_id, time=t.timestamp,
            )
            for t in trades
        ]

    # --- Communication logs ---

    @app.get("/api/logs", response_model=list[CommLogResponse])
    async def get_logs(limit: int = 100):
        logs = ws_server.comm_logs
        return [
            CommLogResponse(
                timestamp=l.timestamp, direction=l.direction,
                client_id=l.client_id, message_type=l.message_type,
                summary=l.summary, fix_raw=l.fix_raw,
            )
            for l in logs[-limit:]
        ]

    # --- Client count ---

    @app.get("/api/clients", response_model=ClientCountResponse)
    async def get_client_count():
        return ClientCountResponse(count=ws_server.client_count)

    # --- Admin WebSocket ---

    @app.websocket("/ws/admin")
    async def admin_websocket(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                data = _get_admin_state(engine, ws_server)
                await ws.send_text(json.dumps(data))
                await asyncio.sleep(0.5)
        except (WebSocketDisconnect, Exception):
            pass

    return app


def _get_admin_state(engine: MatchingEngine, ws_server: ExchangeWSServer) -> dict:
    """Build a full admin state snapshot."""
    books = {}
    for symbol, book in engine.get_all_books().items():
        books[symbol] = {
            "bids": book.bids(),
            "asks": book.asks(),
        }
    trades = [
        {
            "trade_id": t.trade_id,
            "symbol": t.symbol,
            "price": t.price,
            "quantity": t.quantity,
            "buy_order_id": t.buy_order_id,
            "sell_order_id": t.sell_order_id,
            "time": t.timestamp,
        }
        for t in engine.get_trades()
    ]
    logs = [
        {
            "timestamp": l.timestamp,
            "direction": l.direction,
            "client_id": l.client_id,
            "message_type": l.message_type,
            "summary": l.summary,
            "fix_raw": l.fix_raw,
        }
        for l in ws_server.comm_logs[-100:]
    ]
    return {
        "type": "admin_state",
        "market_state": engine.config.market_state.value,
        "stocks": {
            s.symbol: {
                "floor": s.floor, "ceiling": s.ceiling,
                "price_step": s.price_step, "qty_step": s.qty_step,
            }
            for s in engine.config.stocks.values()
        },
        "books": books,
        "trades": trades,
        "logs": logs,
        "client_count": ws_server.client_count,
    }
