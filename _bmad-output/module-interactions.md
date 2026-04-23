# Module Interactions

## Cross-process (FE / Admin / BE)

| caller | callee | method / endpoint / function | purpose |
|---|---|---|---|
| Client UI (`client/src/hooks/useWebSocket.js`) | Engine client WS (`ws_server.ExchangeWSServer._handle_client`) | `new WebSocket("ws://localhost:8765")` → JSON `{type:"new_order"\|"subscribe"}` | Đặt lệnh, yêu cầu lại snapshot |
| Engine client WS | Client UI | JSON push: `market_snapshot`, `market_update`, `trade`, `execution_report`, `error` | Cập nhật state order book + fill |
| Admin UI (`admin/src/hooks/useAdminApi.js`) | FastAPI (`engine/api.py`) | `POST /api/market/start`, `POST /api/market/stop`, `GET /api/market/state` | Đổi `ExchangeConfig.market_state` |
| Admin UI | FastAPI | `GET /api/stocks`, `GET /api/stocks/{symbol}`, `PUT /api/stocks/{symbol}` | Đọc/sửa `StockConfig` |
| Admin UI | FastAPI | `GET /api/orderbook/{symbol}`, `GET /api/trades?symbol=…`, `GET /api/logs?limit=…`, `GET /api/clients` | Đọc snapshot lẻ (không dùng nhiều vì WS đã cover) |
| Admin UI (`admin/src/hooks/useAdminWebSocket.js`) | FastAPI (`api.admin_websocket`) | `new WebSocket("ws://localhost:8000/ws/admin")` | Nhận `admin_state` push 0.5s |

## Nội bộ engine

| caller | callee | method / function | purpose |
|---|---|---|---|
| `engine/main.py::main` | `engine.matching.MatchingEngine()` | ctor | Tạo instance engine duy nhất |
| `engine/main.py::main` | `engine.ws_server.ExchangeWSServer(engine=...)` | ctor | Bind engine vào WS server (cùng reference) |
| `engine/main.py::main` | `engine.api.create_app(engine, ws_server)` | factory | Tạo FastAPI app, gắn `app.state.engine` & `app.state.ws_server` |
| FastAPI lifespan | `ExchangeWSServer.start()` | `websockets.serve(_handle_client, host, 8765)` | Mở port client WS |
| `ExchangeWSServer._handle_client` | `_build_market_snapshot()` → `engine.get_all_books()`, `engine.get_trades(symbol)`, `engine.config.get_stock(symbol)` | đọc state | Gửi snapshot mới connect |
| `ExchangeWSServer._handle_new_order` | `MatchingEngine.submit_order(order)` | core dispatch | Nhận `MatchResult` |
| `MatchingEngine.submit_order` | `ExchangeConfig.is_open()` | precondition | Reject nếu CLOSED |
| `MatchingEngine.submit_order` | `OrderBook.process_order(order)` | match | Sinh trades / exec reports / book updates |
| `OrderBook.process_order` | `StockConfig.validate_price/validate_quantity` | validate | Reject nếu vi phạm floor/ceiling/step |
| `OrderBook._match` | `Order.fill(qty, price)` | state mutation | Cập nhật `leaves_qty`, `status`, `avg_px` |
| `MatchingEngine.submit_order` | `self._trades.extend(result.trades)` | accumulate | Là nguồn duy nhất cho `get_trades` |
| `ExchangeWSServer._handle_new_order` | `_send_json(ws, er)` / `_broadcast_json_all(data)` | fanout | Gửi báo cáo về client đặt lệnh và broadcast trade/book_update |
| `ExchangeWSServer._handle_new_order` | `fix_codec.encode_new_order_single / encode_execution_report / fix_to_human` | log | Render FIX human-readable cho CommLog |
| FastAPI `admin_websocket` | `_get_admin_state(engine, ws_server)` | snapshot | Build object, `send_text` mỗi 0.5s |
| FastAPI `/api/stocks/{symbol}` PUT | `MatchingEngine.update_stock_config(symbol.upper(), **updates)` | mutation | Sửa `StockConfig` + rebind `book.config` |
| FastAPI `/api/market/*` | `ExchangeConfig.open_market() / close_market()` | flip | Đổi `market_state` |

## Integration point dễ lỗi

- **Engine & WS server phải share cùng instance `MatchingEngine`.** `create_app` có nhánh mặc định `engine = MatchingEngine()` và `ws_server = ExchangeWSServer(engine=engine)` — nếu ai đó tạo `create_app()` không truyền `engine` đã có sẵn ở `main.py`, sẽ có 2 engine song song (HTTP đọc engine A, WS ghi engine B) → demo vỡ. `main.py` truyền đủ; cẩn trọng khi viết test/tool ngoài.
- **Symbol normalization.** `_handle_new_order` gọi `data["symbol"].upper()`; HTTP handler cũng `.upper()`. Nếu thêm entry point mới (ví dụ CLI) mà quên upper → `engine._books.get` trả None → reject "Unknown symbol".
- **Validation boundary kép.** Pydantic `StockConfigUpdate` chỉ kiểm `> 0`; `MatchingEngine.update_stock_config` không check logic (ví dụ `ceiling <= floor`). Nhưng khi order kế tiếp tới, `MatchingEngine.submit_order` kiểm `ceiling <= floor` → `os._exit(1)` làm chết engine. Admin sửa config cẩu thả có thể kill engine.
- **Resting order không revalidate sau khi config đổi.** Nếu Admin hạ `ceiling` dưới price của order đang resting, order cũ vẫn nằm đó; chỉ order mới bị reject.
- **Broadcast tới tất cả client.** `_broadcast_json_all` gửi toàn bộ `execution_report` của resting counter-party cho mọi socket (vì server không track ai sở hữu order). Client hook lưu execReports ≤100 không filter theo account → mỗi UI thấy báo cáo của người khác. Đừng suy ra rằng chỉ owner thấy fill.
- **Deque bounded cho CommLog.** `_comm_logs = deque(maxlen=1000)`. Auto-generator bên Client có thể vượt 1000 entry rất nhanh; admin logs panel chỉ có data gần nhất. Không phải bug — design choice. Đừng đổi thành list unbounded.
- **State sync Admin UI.** `useAdminWebSocket` ghi đè `state` mỗi tick. Component đọc `state?.market_state` — nếu socket disconnect giữa chừng, `state` giữ giá trị cũ cho đến khi reconnect + nhận message mới (có thể hiển thị info lỗi thời, bù lại bằng badge `Disconnected`).
- **Cross-module price fallback.** `_match`: `fill_price = incoming.price if incoming.price else best_price`. Với MARKET order (`price=0`) sẽ lấy `best_price` của level đối diện. Sửa logic này dễ gây lệch trade price.
- **Engine fatal exit.** `matching.submit_order` gọi `os._exit(1)` trên 3 tình huống envelope (price<0, qty<=0, ceiling<=floor). Test phải tránh trigger — gọi trực tiếp `OrderBook.process_order` nếu cần test invariant mà không sập engine.
- **FastAPI error response pattern.** Các endpoint `/api/stocks/{symbol}`, `/api/orderbook/{symbol}` trả `JSONResponse(status_code=404, content={"detail": ...})` thay vì `raise HTTPException`. Nếu code client check `resp.ok` kèm `data.detail` thì fine (`useAdminApi` đang làm vậy), nhưng request validation của FastAPI khác sẽ không đồng nhất format.
- **CORS `allow_origins=["*"]`.** Không hạn chế origin — chỉ dùng trong hackathon local. Đừng deploy public mà giữ nguyên.
