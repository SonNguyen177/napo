# Kiến trúc tổng quan — Exchange Matching Engine

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NAPO Matching Engine                          │
│                    (Hackathon — in-memory, no DB)                    │
└─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────┐          ┌─────────────────────────────────────────────────────────────────┐
  │     Admin UI         │          │                        ENGINE PROCESS (Port 8000 + 8765)         │
  │    (Port 3001)       │          │                                                                   │
  │                      │          │  ┌─────────────────────────────────────────────────────────────┐ │
  │  MarketControl       │ HTTP     │  │  api.py (FastAPI)                                           │ │
  │  StockConfig         ├─────────►│  │  REST: /api/market/*, /api/stocks*, /api/trades, /api/logs  │ │
  │  OrderBookView       │ /api/*   │  │  WS:   /ws/admin  → push admin_state mỗi 0.5s (server-only) │ │
  │  TradeHistory        │          │  └────────────────┬────────────────────────────────────────────┘ │
  │  CommLogs            │◄─────────┤                   │ đọc/ghi                                       │
  │  ClientCount         │ WS push  │  ┌────────────────▼────────────────────────────────────────────┐ │
  │                      │ 0.5s     │  │  matching.py — MatchingEngine                               │ │
  │  hooks/              │          │  │  • Kiểm market state (OPEN/CLOSED)                          │ │
  │  useAdminWebSocket   │          │  │  • Route order → đúng OrderBook theo symbol                 │ │
  │  useAdminApi         │          │  │  • _trades: list[Trade]  ← nguồn sự thật lịch sử trade      │ │
  └─────────────────────┘          │  │  • _books:  dict[symbol → OrderBook]                         │ │
                                    │  └────────────────┬────────────────────────────────────────────┘ │
                                    │                   │ validate + match                               │
                                    │  ┌────────────────▼────────────────────────────────────────────┐ │
                                    │  │  order_book.py — OrderBook (1 instance per symbol)          │ │
                                    │  │  • validate_order(): floor/ceiling/price_step/qty_step       │ │
                                    │  │  • process_order(): price-time priority matching             │ │
                                    │  │  • bids/asks: dict[int_price, deque[Order]]                 │ │
                                    │  │  • Trả về: MatchResult(trades, exec_reports, book_updates)  │ │
                                    │  └─────────────────────────────────────────────────────────────┘ │
                                    │                                                                   │
                                    │  ┌─────────────────────────────────────────────────────────────┐ │
                                    │  │  ws_server.py — ExchangeWSServer (Port 8765)                │ │
                                    │  │  • Nhận JSON: new_order, subscribe                          │ │
                                    │  │  • Gửi đến client đặt lệnh: execution_report                │ │
                                    │  │  • Broadcast tất cả client: trade, market_update            │ │
                                    │  │  • On connect: market_snapshot (per symbol)                 │ │
                                    │  └────────────────▲────────────────────────────────────────────┘ │
                                    │                   │ WS JSON                                        │
                                    └───────────────────┼───────────────────────────────────────────────┘
                                                        │ Port 8765
                                    ┌───────────────────┴───────────────────┐
                                    │                                        │
                              ┌─────┴──────────────┐          ┌─────────────┴──────────────┐
                              │    Client UI tab 1   │          │    Client UI tab 2           │
                              │      (Port 5173)     │          │      (Port 5173)             │
                              │                      │          │                              │
                              │  OrderEntry          │          │  OrderEntry                  │
                              │  MarketData          │          │  MarketData                  │
                              │  TradeView           │          │  TradeView                   │
                              │  PriceChart          │          │  PriceChart                  │
                              │                      │          │                              │
                              │  hooks/useWebSocket  │          │  hooks/useWebSocket          │
                              └──────────────────────┘          └──────────────────────────────┘
```

---

## Vai trò từng component

### Engine (Backend) — trái tim hệ thống

| Module | Vai trò |
|---|---|
| `main.py` | Entry point — tạo **đúng 1** `MatchingEngine` + **1** `ExchangeWSServer`, nối chúng vào FastAPI, chạy uvicorn |
| `api.py` | REST cho Admin + WS `/ws/admin` push snapshot 0.5s một chiều |
| `ws_server.py` | WebSocket `:8765` cho Client — nhận order vào, phân phát kết quả ra |
| `matching.py` | Điều phối: check market state, route order đúng symbol, lưu trade history |
| `order_book.py` | Matching thực sự: price-time priority, validate, fill, trả kết quả |
| `config.py` | Cấu hình stock (floor/ceiling/step) + market state (OPEN/CLOSED) |
| `models.py` | Data types: `Order`, `Trade`, `ExecutionReport`, enums |
| `fix_codec.py` | Mã hóa FIX 4.4 **chỉ để hiển thị log** — wire thực vẫn là JSON |

### Admin UI (:3001) — bảng điều khiển

- Kết nối **HTTP** để ra lệnh (start/stop market, sửa stock config)
- Kết nối **WS** để nhận snapshot toàn hệ mỗi 0.5s (chỉ nghe, không gửi)
- Quan sát: order books, trades, FIX comm logs, số client

### Client UI (:5173) — màn hình trader

- Kết nối **duy nhất 1 WS** tới `:8765`, không dùng REST
- Gửi: `new_order` (LIMIT/MARKET) hoặc `subscribe`
- Nhận: `execution_report` (riêng lệnh của mình), `trade` + `market_update` (broadcast cho tất cả)

---

## Luồng đặt lệnh (happy path)

```
Client UI
  │ {type:"new_order", symbol:"ACB", side:"BUY", price:20100, qty:100}
  ▼
ws_server.py (_handle_new_order)
  │ symbol.upper() → submit_order(order)
  ▼
matching.py (MatchingEngine.submit_order)
  │ check is_open() → route tới OrderBook["ACB"]
  ▼
order_book.py (validate_order → process_order)
  │ fill nếu có lệnh đối ứng → MatchResult
  ▼
ws_server.py (xử lý kết quả)
  ├─► execution_report  →  chỉ client đặt lệnh
  ├─► trade             →  broadcast tất cả client
  └─► market_update     →  broadcast tất cả client
                                │
                          api.py (0.5s sau)
                                │ snapshot admin_state
                                ▼
                           Admin UI cập nhật
```

---

**Điểm quan trọng nhất:** Chỉ có **1 process engine** giữ toàn bộ state trong RAM. Restart = mất hết. Không DB, không queue, không cache — thiết kế cố ý cho hackathon demo.