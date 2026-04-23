# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Hackathon project — a simplified stock exchange matching engine. Most everything lives under `matching-engine/`. Detailed architecture/data-model/flow notes live in `_bmad-output/`; read those when context is missing.

## Commands

All paths below are relative to `matching-engine/` unless noted.

```bash
# First-time setup (per service)
cd exchange/engine && uv sync && cd ../..
cd exchange/admin  && npm install && cd ../..
cd client          && npm install && cd ..

# Start full stack (logs/PIDs in matching-engine/.run/)
./startall.sh                              # macOS/Linux
.\startall.ps1                             # Windows PowerShell
./stopall.sh   # or .\stopall.ps1          # kill via PID files

# Run a single service (when debugging)
cd exchange/engine && uv run python -m engine.main      # engine: HTTP+admin WS :8000, client WS :8765
cd exchange/admin  && npm run dev                       # admin UI :3001
cd client          && npm run dev                       # client UI :5173

# Tests (engine only — UIs have no tests, just `npm run lint`)
cd exchange/engine && uv run pytest                     # full suite
cd exchange/engine && uv run pytest tests/test_matching.py
cd exchange/engine && uv run pytest tests/test_order_book.py::test_name_here
# pytest-asyncio is in `auto` mode (see pyproject.toml) — async test funcs don't need a marker.

# Smoke check
curl http://localhost:8000/api/market/state             # {"state":"CLOSED"} on fresh start
curl -X POST http://localhost:8000/api/market/start
```

## Architecture

**3 processes, no persistence.** Engine holds all state in RAM (order books, trades, configs, comm logs). Restart = wipe — including any stock config edits made through Admin.

```
Client UI (:5173) ──WS JSON :8765─────────┐
                                          ▼
Admin UI (:3001) ──HTTP :8000/api──▶ Engine process
                  ──WS :8000/ws/admin──▶ (MatchingEngine + ExchangeWSServer, single instance)
```

- **Engine** (`exchange/engine/src/engine/`, Python 3.14 + uv, FastAPI + `websockets` + `simplefix`)
  - `main.py` is the only entry point that wires it correctly: builds **one** `MatchingEngine`, **one** `ExchangeWSServer(engine=...)`, then passes both into `create_app(engine, ws_server)`. FastAPI lifespan calls `ws_server.start()` / `.stop()`.
  - `matching.py::MatchingEngine` — routes orders by symbol, holds `_books: dict[str, OrderBook]` and `_trades: list[Trade]` (single source of truth for trade history, read by REST + WS snapshot + admin telemetry).
  - `order_book.py::OrderBook` — price-time priority. Bids/asks are `dict[int_price, deque[Order]]`. Counters per book.
  - `api.py` — REST `/api/market/*`, `/api/stocks*`, `/api/orderbook/{symbol}`, `/api/trades`, `/api/logs`, `/api/clients` + `/ws/admin` push (snapshot every 0.5s, server→client only).
  - `ws_server.py` — client WebSocket on `:8765`. Inbound JSON `new_order` / `subscribe`. Outbound: `market_snapshot` (per symbol on connect), `market_update`, `trade`, `execution_report`, `error`.
  - `fix_codec.py` — encodes FIX 4.4 **only for `CommLog` rendering**. The wire is JSON; FIX is for human-readable admin logs.
- **Admin UI** (`exchange/admin/`, React 19 + Vite, plain hooks — no Redux/Zustand). `useAdminWebSocket` overwrites a single `state` object every tick; components read with optional chaining.
- **Client UI** (`client/`, React 19 + Vite + recharts). One WS to `:8765`, no REST. `useWebSocket` patches `orderBooks[symbol]` per `market_update` (delete level on qty=0, else upsert + re-sort). Caps: `trades` ≤ 200, `execReports` ≤ 100.

## Invariants — DO NOT BREAK

- **Single engine + single ws_server instance.** Always wire via `main.py`'s pattern. If you call `create_app()` with no args (e.g. in a script or new test), it builds a *fresh* `MatchingEngine` and you'll have two parallel engines (HTTP reads A, WS writes B). The existing `tests/test_api.py` shows the correct fixture pattern.
- **Symbol must be `.upper()` at every entry point.** `engine._books` keys are uppercase. Both `_handle_new_order` and HTTP handlers normalize. New entry points (CLI, scripts) must do the same or `engine._books.get(symbol)` returns None → "Unknown symbol" rejection.
- **Market-closed reject comes first.** `submit_order` returns a `REJECTED` exec report with reason `"Market is closed"` if `engine.config.is_open()` is False — before any matching logic.
- **Engine self-destructs on bad envelope.** `MatchingEngine.submit_order` calls `os._exit(1)` if `price < 0`, `qty <= 0`, or `ceiling <= floor`. Tests must avoid these inputs (or call `OrderBook.process_order` directly to bypass the envelope check). Note that **Admin can lower `ceiling` below `floor` via `PUT /api/stocks/{symbol}`** — `StockConfigUpdate` only enforces `> 0`. The next order kills the engine. If you tighten validation, do it in `update_stock_config`, not just Pydantic.
- **All orders go through `OrderBook.validate_order`** (floor/ceiling, `price_step`, `qty_step`) before matching. LIMIT validates price; MARKET only validates qty. `fill_price = incoming.price if incoming.price else best_price` — MARKET (price=0) takes opposite best price. Don't change this without updating tests.
- **Resting orders are NOT revalidated when stock config changes.** `update_stock_config` rebinds `book.config = stock`; existing orders on the book stay even if they violate new floor/ceiling. Only new orders see the new rules.
- **Broadcast model: `_broadcast_json_all` for every `trade` and `market_update`** so all clients see the same event order. Execution reports for the *submitting* order go only to that socket (matched by `cl_ord_id`); exec reports for the *resting counter-party* are broadcast (server doesn't track ownership). Don't assume only the owner sees a fill.
- **`_comm_logs = deque(maxlen=1000)`** — keep it bounded. Auto-generator on the client can flood it; that's expected, not a leak.
- **`OrderBook.config` is a reference** to `ExchangeConfig.stocks[symbol]`, so admin edits propagate without touching the book. The explicit reassignment in `update_stock_config` is belt-and-suspenders.

## Test gotchas

- pytest-asyncio is in `asyncio_mode = "auto"` — `async def test_*` runs without `@pytest.mark.asyncio`.
- `httpx` is the dev dep used by `test_api.py` for FastAPI `TestClient`/async client; that's why it's in `[dependency-groups].dev`, not project deps.
- For order-book invariant tests, prefer `OrderBook.process_order` directly over `MatchingEngine.submit_order` to avoid the `os._exit(1)` envelope checks.

## Things that are intentional (don't "fix")

- `allow_origins=["*"]` CORS — local hackathon only, not deploy-ready.
- No auth anywhere — anyone on the port can place orders or flip the market.
- `JSONResponse(status_code=404, ...)` instead of `raise HTTPException` in some endpoints — mixed style, but `useAdminApi` already handles both.
- No DB / queue / cache / file storage by design. Don't add one without discussing — it changes the demo story.
