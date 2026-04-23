# Bug List — Module `engine` (matching-engine/exchange/engine)

> Nguồn: Edge Case Hunter review trên toàn bộ file Python trong `matching-engine/exchange/engine/src/engine/`.
> Severity được chọn cấp CAO hơn khi nghi ngờ giữa 2 cấp.

---

## ECH-ENGINE-001
- [x] Fixed
- **Fix-summary:** Đổi `_match` từ LIFO sang FIFO: `resting = queue[0]` (thay cho `queue[-1]`) và `queue.popleft()` (thay cho `queue.pop()`) trong `order_book.py`. Thêm regression test `tests/unit/test_ech_engine_001_fifo.py` (bid FIFO + ask FIFO) — fail trước fix, pass sau fix; test cũ `test_time_priority_at_same_price` (baseline đang fail) cũng pass. 3 failure còn lại trong `test_order_book.py` là pre-existing (bug `fill_price` khác, ngoài phạm vi).
- **Severity:** P0 Blocker
- **Module / Location:** `matching-engine/exchange/engine/src/engine/order_book.py:157-213` (kết hợp `matching-engine/exchange/engine/src/engine/order_book.py:215-220`)
- **Description:** Matching engine vi phạm nguyên tắc **price-time priority (FIFO)** – chọn lệnh resting MỚI NHẤT (LIFO) thay vì cũ nhất ở cùng một mức giá.
- **Root cause:** `_add_to_book` dùng `deque.append(order)` (thêm vào phải), còn `_match` đọc `resting = queue[-1]` và xoá bằng `queue.pop()` – cả hai đều thao tác ở đầu phải của deque. Kết quả: lệnh mới nhất match trước.
- **Impact:** Core invariant "price-time priority" trong CLAUDE.md bị phá vỡ. Người đặt lệnh trước không được ưu tiên → không công bằng, trade history phản ánh sai chronology; toàn bộ ý nghĩa của một matching engine (fairness) bị vô hiệu.
- **Reproduction:**
  1. `POST /api/market/start`.
  2. Client A gửi BUY LIMIT qty=100, price=25000 trên ACB.
  3. Client B gửi BUY LIMIT qty=100, price=25000 trên ACB (muộn hơn).
  4. Client C gửi SELL MARKET qty=100 ACB.
  5. Quan sát trade: lệnh của B (mới hơn) fill trước A (cũ hơn). Expect A fill trước.
- **Evidence:**
  ```python
  # order_book.py:162-199 (trích)
  queue = opposite[best_price]
  while incoming.leaves_qty > 0 and queue:
      resting = queue[-1]                 # BUG: lấy lệnh mới nhất
      ...
      if resting.leaves_qty == 0:
          queue.pop()                     # BUG: xoá lệnh mới nhất
  # order_book.py:220
  book[order.price].append(order)         # append vào phải ⇒ newest ở phải
  ```
- **Suggested fix:** Đổi sang FIFO: `resting = queue[0]` và `queue.popleft()`.
- **Source:** ECH

---

## ECH-ENGINE-002
- [ ] Fixed
- **Severity:** P0 Blocker
- **Module / Location:** `matching-engine/exchange/engine/src/engine/ws_server.py:124-147` (kết hợp `matching-engine/exchange/engine/src/engine/matching.py:80-94`)
- **Description:** DoS – bất kỳ client WS nào cũng có thể giết process engine bằng cách gửi `quantity` âm hoặc bằng 0.
- **Root cause:** `_handle_new_order` cast `quantity = int(data["quantity"])` không kiểm tra dấu. `MatchingEngine.submit_order` sau đó gọi `os._exit(1)` khi `order.quantity <= 0` (envelope guard). Không có validation ở ranh giới WS.
- **Impact:** Engine crash toàn bộ → tất cả state in-RAM mất (order books, trades, stock config đã edit, comm logs). Không có auth, không có rate-limit → một client độc hại giết cả sàn.
- **Reproduction:**
  1. `POST /api/market/start`.
  2. Mở WS `ws://localhost:8765`.
  3. Gửi `{"type":"new_order","cl_ord_id":"X","symbol":"ACB","side":"BUY","ord_type":"LIMIT","price":25000,"quantity":-1}`.
  4. Engine process exit code 1; admin UI mất kết nối, toàn bộ books trống sau restart.
- **Evidence:**
  ```python
  # ws_server.py:130
  quantity = int(data["quantity"])     # int(-1) = -1, không bị chặn
  # matching.py:84-87
  if order.quantity <= 0:
      sys.stderr.write(...)
      os._exit(1)                      # giết toàn bộ process
  ```
- **Suggested fix:** Trong `_handle_new_order`, reject sớm với message `error` nếu `quantity <= 0` hoặc `price < 0`; hoặc thay `os._exit(1)` ở engine bằng reject có cấu trúc.
- **Source:** ECH

---

## ECH-ENGINE-003
- [ ] Fixed
- **Severity:** P0 Blocker
- **Module / Location:** `matching-engine/exchange/engine/src/engine/ws_server.py:124-147` (kết hợp `matching-engine/exchange/engine/src/engine/matching.py:80-83`)
- **Description:** DoS – client gửi `price` âm cũng giết engine (cùng pattern với qty âm).
- **Root cause:** `int(data.get("price", 0))` chấp nhận số âm; envelope guard `if order.price < 0` ở engine gọi `os._exit(1)`.
- **Impact:** Crash engine, mất toàn bộ state. Chỉ cần market mở và một symbol hợp lệ → khai thác được.
- **Reproduction:**
  1. `POST /api/market/start`.
  2. Gửi WS `{"type":"new_order","cl_ord_id":"Y","symbol":"ACB","side":"BUY","ord_type":"LIMIT","price":-1,"quantity":100}`.
  3. Engine exit 1.
- **Evidence:**
  ```python
  # ws_server.py:129
  price = int(data.get("price", 0))    # không chặn <0
  # matching.py:80-83
  if order.price < 0:
      sys.stderr.write(...)
      os._exit(1)
  ```
- **Suggested fix:** Validate `price >= 0` tại `_handle_new_order` và trả error JSON; không để đến envelope guard.
- **Source:** ECH

---

## ECH-ENGINE-004
- [ ] Fixed
- **Severity:** P0 Blocker
- **Module / Location:** `matching-engine/exchange/engine/src/engine/api.py:29-40` và `matching-engine/exchange/engine/src/engine/matching.py:115-133` (trigger ở `matching.py:88-94`)
- **Description:** Admin DoS – `PUT /api/stocks/{symbol}` cho phép set `ceiling <= floor`; order tiếp theo đụng envelope guard và giết engine.
- **Root cause:** `StockConfigUpdate.must_be_positive` chỉ kiểm `v > 0`, không kiểm ràng buộc cross-field. `update_stock_config` setattr từng field không check quan hệ. Envelope guard ở `submit_order` (`ceiling <= floor`) gọi `os._exit(1)`.
- **Impact:** Bất cứ ai có quyền gọi admin API (không có auth) đều có thể làm sập toàn bộ sàn. CLAUDE.md đã note biết lỗi này nhưng chưa fix.
- **Reproduction:**
  1. `PUT /api/stocks/ACB` body `{"ceiling": 10, "floor": 5000}` (gọi thứ tự này để ceiling=10 < floor hiện tại 20000, rồi floor=5000 vẫn > ceiling).
  2. `POST /api/market/start`.
  3. Submit bất kỳ order nào cho ACB → engine exit 1.
- **Evidence:**
  ```python
  # api.py:35-40
  @field_validator("floor", "ceiling", "price_step", "qty_step", mode="before")
  def must_be_positive(cls, v):
      if v is not None and v <= 0:
          raise ValueError("Value must be positive")
      return v                             # KHÔNG kiểm ceiling>floor
  # matching.py:115-133: update_stock_config setattr không kiểm chéo
  # matching.py:88-94: envelope kill process
  ```
- **Suggested fix:** Trong `update_stock_config` (không chỉ Pydantic, vì có thể update một field tại một thời điểm), sau khi apply cập nhật, kiểm `stock.ceiling > stock.floor`, `stock.price_step > 0`, `stock.qty_step > 0`, `(stock.ceiling - stock.floor) % stock.price_step == 0`; nếu vi phạm → rollback và trả lỗi.
- **Source:** ECH

---

## ECH-ENGINE-005
- [ ] Fixed
- **Severity:** P1 Critical
- **Module / Location:** `matching-engine/exchange/engine/src/engine/ws_server.py:124-147`
- **Description:** `_handle_new_order` chỉ catch `KeyError, ValueError`. Nếu client gửi price/quantity là mảng hoặc object (JSON list/dict), `int()` ném `TypeError` không được catch → exception bubble ra `_handle_client`, đóng kết nối client ngay lập tức.
- **Root cause:** Tuple except thiếu `TypeError` (và các exception khác như `AttributeError` nếu `data["side"]` là số không có `.upper()`).
- **Impact:** Client bị kick khỏi WS khi gửi payload sai kiểu dù chỉ do lập trình sai phía client. Trải nghiệm tệ; khó debug; có thể bị lợi dụng để gây disconnection flood.
- **Reproduction:**
  1. Mở WS `ws://localhost:8765`.
  2. Gửi `{"type":"new_order","cl_ord_id":"Z","symbol":"ACB","side":"BUY","ord_type":"LIMIT","price":[1,2],"quantity":100}`.
  3. Kết nối WS bị đóng (1011 hoặc abrupt close) mà không có execution report hay message error rõ ràng.
- **Evidence:**
  ```python
  # ws_server.py:126-147
  try:
      side = Side(data["side"].upper())
      ...
      price = int(data.get("price", 0))          # TypeError nếu price là list
      quantity = int(data["quantity"])
      ...
  except (KeyError, ValueError) as e:            # KHÔNG có TypeError
      ...
  ```
- **Suggested fix:** Thêm `TypeError` vào tuple except (và `AttributeError` cho trường hợp `side`/`symbol` không phải string), hoặc dùng `except Exception as e:` và trả về error JSON thay vì để bubble.
- **Source:** ECH

---

## ECH-ENGINE-006
- [ ] Fixed
- **Severity:** P1 Critical
- **Module / Location:** `matching-engine/exchange/engine/src/engine/ws_server.py:129-130`
- **Description:** `int(...)` âm thầm truncate float → lệnh `price=20199.99` biến thành `20199`, `quantity=100.7` biến thành `100`. Không validate integer chính xác ở ranh giới WS.
- **Root cause:** `int(1.99) == 1` trong Python, không raise. JSON number có thể là float.
- **Impact:** Giá/số lượng bị biến dạng âm thầm. Trade sai giá (1 VND/step của ACB là 100, nhưng 20199 có thể vẫn fail validate_price và reject – tuy vậy nếu client gửi 20100.99 thì trở thành 20100 lọt qua validate và trade ở giá sai). Client không biết có truncate.
- **Reproduction:**
  1. Gửi `{"type":"new_order","cl_ord_id":"T","symbol":"ACB","side":"BUY","ord_type":"LIMIT","price":20100.99,"quantity":100}`.
  2. Server xử lý như price=20100; trade (nếu match) ở 20100 thay vì reject.
- **Evidence:**
  ```python
  # ws_server.py:129-130
  price = int(data.get("price", 0))
  quantity = int(data["quantity"])
  ```
- **Suggested fix:** Kiểm `isinstance(data["quantity"], int)` / `isinstance(data["price"], int)` (không phải bool, không phải float); nếu không đúng → reject với message rõ ràng. Có thể dùng `if not isinstance(v, int) or isinstance(v, bool): raise ValueError(...)`.
- **Source:** ECH

---

## ECH-ENGINE-007
- [ ] Fixed
- **Severity:** P1 Critical
- **Module / Location:** `matching-engine/exchange/engine/src/engine/matching.py:32-102`
- **Description:** Thứ tự kiểm tra guard ở `submit_order` sai: "market closed" và "unknown symbol" trả reject sạch, nhưng envelope guard (`price<0`, `qty<=0`, `ceiling<=floor`) lại ở SAU unknown-symbol check – trong khi đúng ra envelope là điều kiện **gọi ngay `os._exit`**. Hệ quả: nếu `book` = None (unknown symbol) thì envelope check không chạy, nhưng `book.config.ceiling <= book.config.floor` được access sau khi đã biết book tồn tại. Không có bug sai nghiêm trọng logic ở đây, NHƯNG vấn đề thật: envelope guard (`os._exit(1)`) đặt sau checks hợp lệ khác nghĩa là nếu `ceiling<=floor` xảy ra cho stock có book → mọi order hợp lệ đến cuối cùng đều killed. Thiếu "graceful reject" thay vì self-destruct.
- **Root cause:** Thiết kế dùng `os._exit(1)` làm fail-fast thay vì reject có cấu trúc. Không có path graceful khi state internal bị hỏng do admin config sai.
- **Impact:** Không thể phục hồi: sau khi admin set ceiling<=floor, không cách nào gửi request sửa trước khi order đến – vì chính admin UI push state cũng không chặn. Engine self-destruct → mất tất cả trades/books.
- **Reproduction:** Xem ECH-ENGINE-004.
- **Evidence:**
  ```python
  # matching.py:80-94
  if order.price < 0: ... os._exit(1)
  if order.quantity <= 0: ... os._exit(1)
  if book.config.ceiling <= book.config.floor: ... os._exit(1)
  ```
- **Suggested fix:** Thay `os._exit(1)` bằng reject có `reject_reason` (ví dụ `"Internal: invalid stock config"`) – chỉ log FATAL, không kill process. Kết hợp fix ở ECH-ENGINE-004 để chặn config sai ngay từ API layer.
- **Source:** ECH

---

## ECH-ENGINE-008
- [ ] Fixed
- **Severity:** P1 Critical
- **Module / Location:** `matching-engine/exchange/engine/src/engine/api.py:218-277`
- **Description:** Admin WebSocket loop gọi `engine.get_trades()` mỗi 500ms → trả về `list(self._trades)` (full copy). Với trade history in-RAM không giới hạn, payload tăng tuyến tính theo thời gian chạy; bandwidth/CPU/memory tăng theo `O(N)` mỗi tick.
- **Root cause:** `get_trades()` ở `matching.py:107-110` copy toàn bộ list; `_get_admin_state` không paginate/limit trades; `_trades` không bị bound (xem ECH-ENGINE-014).
- **Impact:** Sau vài giờ chạy auto-generator (tạo hàng ngàn trade/phút), mỗi snapshot admin có thể hàng chục MB, làm UI Admin lag, WS timeout, event loop block do `json.dumps` list lớn.
- **Reproduction:**
  1. Chạy engine, mở market.
  2. Bật client auto-generator flood orders (khoảng 10 trade/sec).
  3. Quan sát memory admin WS payload và độ trễ tick sau 30 phút.
- **Evidence:**
  ```python
  # api.py:232-251 (trích)
  trades = [ {...} for t in engine.get_trades() ]
  return {..., "trades": trades, ...}
  # matching.py:107-110
  def get_trades(self, symbol=None):
      if symbol is None:
          return list(self._trades)       # full copy
  ```
- **Suggested fix:** Giới hạn trade snapshot tới `N` (ví dụ 100) cuối cùng giống `_comm_logs`; hoặc chuyển sang incremental push (chỉ trade mới) thay vì full snapshot mỗi 500ms.
- **Source:** ECH

---

## ECH-ENGINE-009
- [ ] Fixed
- **Severity:** P1 Critical
- **Module / Location:** `matching-engine/exchange/engine/src/engine/order_book.py:115-121`
- **Description:** MARKET order không match được (không có liquidity ở phía đối diện) bị cancel nhưng `reject_reason` rỗng → client không biết vì sao lệnh biến mất.
- **Root cause:** `order.cancel()` + `_make_exec_report(order, ExecType.CANCELLED)` mặc định `reject_reason=""`. Không truyền lý do.
- **Impact:** UX kém: client thấy lệnh CANCELLED nhưng không có thông tin. Log FIX không có `TAG_TEXT` (58) → debug khó.
- **Reproduction:**
  1. Mở market khi book ACB trống.
  2. Submit MARKET BUY qty=100 ACB.
  3. Execution report CANCELLED, `reject_reason=""`.
- **Evidence:**
  ```python
  # order_book.py:116-121
  if order.ord_type == OrdType.MARKET:
      order.cancel()
      result.exec_reports.append(self._make_exec_report(
          order, ExecType.CANCELLED,
      ))                                   # không có reject_reason
  ```
- **Suggested fix:** Truyền `reject_reason="No liquidity on opposite side"` (hoặc "Partially filled market order, remainder cancelled: no liquidity" nếu `filled_qty > 0`).
- **Source:** ECH

---

## ECH-ENGINE-010
- [ ] Fixed
- **Severity:** P2 High
- **Module / Location:** `matching-engine/exchange/engine/src/engine/matching.py:39-53` và `matching-engine/exchange/engine/src/engine/matching.py:60-74`
- **Description:** Exec-ID bị trùng cho mọi reject "market closed" (`"EXEC-REJ-MARKET-CLOSED"`) và mọi reject "unknown symbol" (`"EXEC-REJ-UNKNOWN-SYM"`). Vi phạm ràng buộc FIX `ExecID` (tag 17) phải duy nhất.
- **Root cause:** Hai chuỗi literal hard-code; không gọi counter.
- **Impact:** Log FIX không thể phân biệt các reject events; admin UI hiện nhiều hàng có cùng `exec_id` → khó debug & audit không hợp lệ theo chuẩn FIX 4.4.
- **Reproduction:**
  1. Không start market.
  2. Gửi 3 lệnh liên tiếp qua WS.
  3. Cả 3 exec report có `exec_id = "EXEC-REJ-MARKET-CLOSED"`.
- **Evidence:**
  ```python
  # matching.py:42-43
  exec_id="EXEC-REJ-MARKET-CLOSED",
  # matching.py:63-64
  exec_id="EXEC-REJ-UNKNOWN-SYM",
  ```
- **Suggested fix:** Sinh exec_id duy nhất qua counter cấp engine (`itertools.count`) hoặc UUID. Ví dụ: `exec_id=f"EXEC-REJ-{next(self._reject_counter)}"`.
- **Source:** ECH

---

## ECH-ENGINE-011
- [ ] Fixed
- **Severity:** P2 High
- **Module / Location:** `matching-engine/exchange/engine/src/engine/api.py:218-227`
- **Description:** Admin WS handler bắt `except (WebSocketDisconnect, Exception): pass` → nuốt mọi lỗi (JSON encode fail, network fail, internal bug) mà không log.
- **Root cause:** Thiết kế "silently swallow" để tránh crash, nhưng không có `logger.exception(...)`.
- **Impact:** Khi state corrupt (ví dụ Trade có field `None`) hoặc engine ném exception, admin UI mất dữ liệu mà không dev nào biết → observability bằng 0.
- **Reproduction:** Khó tạo repro cố ý, nhưng bất kỳ raise nào từ `_get_admin_state` đều biến mất.
- **Evidence:**
  ```python
  # api.py:220-227
  try:
      while True:
          data = _get_admin_state(engine, ws_server)
          await ws.send_text(json.dumps(data))
          await asyncio.sleep(0.5)
  except (WebSocketDisconnect, Exception):
      pass
  ```
- **Suggested fix:** Tách `WebSocketDisconnect` (pass) khỏi `Exception` (log). Ví dụ: `except WebSocketDisconnect: pass` + `except Exception: logger.exception("admin ws")`.
- **Source:** ECH

---

## ECH-ENGINE-012
- [ ] Fixed
- **Severity:** P2 High
- **Module / Location:** `matching-engine/exchange/engine/src/engine/ws_server.py:258-272`
- **Description:** `ExchangeWSServer.start()` không kiểm tra đã start trước đó. Gọi 2 lần → `self._server` bị ghi đè; instance cũ mất tham chiếu nhưng vẫn bind port 8765 cho đến khi GC + close.
- **Root cause:** Không có guard `if self._server is not None`.
- **Impact:** Nếu lifespan lifecycle bị trigger 2 lần (ví dụ reload) → socket leak, có thể "address already in use" khi restart; orphaned `Server` task vẫn chạy.
- **Reproduction:** Gọi `await ws_server.start()` hai lần trong cùng event loop.
- **Evidence:**
  ```python
  # ws_server.py:259-265
  async def start(self):
      self._server = await websockets.serve(   # ghi đè không check
          self._handle_client, self.host, self.port,
      )
      return self._server
  ```
- **Suggested fix:**
  ```python
  if self._server is not None:
      raise RuntimeError("WS server already started")
  ```
- **Source:** ECH

---

## ECH-ENGINE-013
- [ ] Fixed
- **Severity:** P2 High
- **Module / Location:** `matching-engine/exchange/engine/src/engine/api.py:198-208`
- **Description:** `GET /api/logs?limit=<n>` không validate `limit`. `limit=-1` trả về `logs[1:]` (tất cả trừ đầu); `limit=0` trả về `logs[:]` = tất cả log; `limit=-1000` → `logs[1000:]` (có thể rỗng) — hành vi không trực giác do Python slicing.
- **Root cause:** `logs[-limit:]` không biên kiểm.
- **Impact:** Client gửi giá trị âm nhận dữ liệu "lạ" mà không hiểu; potential information leak (gửi `limit=0` để lấy hết log thay vì 100 mặc định). Không có bảo mật nhưng API hợp đồng không rõ.
- **Reproduction:**
  1. `curl "http://localhost:8000/api/logs?limit=0"` → trả về tất cả logs (không phải 0 bản ghi).
  2. `curl "http://localhost:8000/api/logs?limit=-1"` → trả về tất cả trừ bản ghi đầu tiên.
- **Evidence:**
  ```python
  # api.py:198-208
  @app.get("/api/logs", ...)
  async def get_logs(limit: int = 100):
      logs = ws_server.comm_logs
      return [... for l in logs[-limit:]]
  ```
- **Suggested fix:** Clamp `limit = max(0, min(limit, len(logs)))` rồi `logs[-limit:] if limit else []`; hoặc raise 400 cho limit âm.
- **Source:** ECH

---

## ECH-ENGINE-014
- [ ] Fixed
- **Severity:** P2 High
- **Module / Location:** `matching-engine/exchange/engine/src/engine/matching.py:26` (khởi tạo `_trades: list`)
- **Description:** `_trades` là list không giới hạn kích thước. Không rotate/truncate. Với hackathon auto-generator (hàng trăm trade/phút) → memory tăng tuyến tính, không reclaim trừ khi restart process.
- **Root cause:** Không có `maxlen` (không như `_comm_logs` dùng `deque(maxlen=1000)`).
- **Impact:** Long-running demo chạy ngày dài có thể OOM; admin WS snapshot (ECH-ENGINE-008) cũng phình theo.
- **Reproduction:** Bật auto-generator 1 giờ → `len(engine._trades)` hàng chục ngàn.
- **Evidence:**
  ```python
  # matching.py:26
  self._trades: list[Trade] = []
  # matching.py:100
  self._trades.extend(result.trades)
  ```
- **Suggested fix:** Đổi sang `deque(maxlen=N)` (ví dụ 10_000) – đồng bộ với pattern `_comm_logs`.
- **Source:** ECH

---

## ECH-ENGINE-015
- [ ] Fixed
- **Severity:** P2 High
- **Module / Location:** `matching-engine/exchange/engine/src/engine/api.py:184-194`
- **Description:** `GET /api/trades?symbol=<x>` với symbol không tồn tại trả về 200 OK + list rỗng, không 404. Không khớp hợp đồng với các endpoint khác (`/api/stocks/{symbol}`, `/api/orderbook/{symbol}` đều trả 404 nếu unknown).
- **Root cause:** `engine.get_trades(symbol.upper())` filter in-memory, rỗng nếu không có trade cho symbol đó — không phân biệt "symbol không tồn tại" vs "symbol có nhưng chưa trade".
- **Impact:** Client không thể phát hiện typo (`XYZZ` → list rỗng thay vì 404). Inconsistent API.
- **Reproduction:** `curl http://localhost:8000/api/trades?symbol=XYZZ` → `[]` + 200.
- **Evidence:**
  ```python
  # api.py:184-194
  async def get_trades(symbol: str | None = None):
      trades = engine.get_trades(symbol.upper() if symbol else None)
      return [ TradeResponse(...) for t in trades ]   # không check exists
  ```
- **Suggested fix:** Nếu `symbol is not None` và `engine.config.get_stock(symbol.upper()) is None` → return 404.
- **Source:** ECH

---

## ECH-ENGINE-016
- [ ] Fixed
- **Severity:** P3 Low
- **Module / Location:** `matching-engine/exchange/engine/src/engine/order_book.py:95-110`
- **Description:** Order ID được cấp trước khi validate. Lệnh bị reject vẫn tiêu thụ `ORD-<SYM>-N` → counter tăng nhảy cóc, gây nhầm lẫn khi audit.
- **Root cause:** `order.order_id = self._next_order_id()` ở dòng 100 chạy trước `validate_order()` ở dòng 103.
- **Impact:** Chỉ là cosmetic; audit log có gap (ORD-ACB-1, ORD-ACB-3 nếu #2 bị reject), dễ làm debug nhầm là "mất dữ liệu".
- **Reproduction:** Gửi 1 order invalid → counter tăng; order hợp lệ tiếp theo có ID = 2 nhưng trong log FIX không thấy order 1.
- **Evidence:**
  ```python
  # order_book.py:99-109
  order.order_id = self._next_order_id()    # cấp trước
  err = self.validate_order(order)
  if err:
      order.reject()
      ...                                    # reject rồi nhưng ID đã tiêu
  ```
- **Suggested fix:** Chỉ gán `order_id` sau khi validate pass.
- **Source:** ECH

---

## Tag Index

| ID | Severity | File |
|---|---|---|
| ECH-ENGINE-001 | P0 | order_book.py |
| ECH-ENGINE-002 | P0 | ws_server.py + matching.py |
| ECH-ENGINE-003 | P0 | ws_server.py + matching.py |
| ECH-ENGINE-004 | P0 | api.py + matching.py |
| ECH-ENGINE-005 | P1 | ws_server.py |
| ECH-ENGINE-006 | P1 | ws_server.py |
| ECH-ENGINE-007 | P1 | matching.py |
| ECH-ENGINE-008 | P1 | api.py + matching.py |
| ECH-ENGINE-009 | P1 | order_book.py |
| ECH-ENGINE-010 | P2 | matching.py |
| ECH-ENGINE-011 | P2 | api.py |
| ECH-ENGINE-012 | P2 | ws_server.py |
| ECH-ENGINE-013 | P2 | api.py |
| ECH-ENGINE-014 | P2 | matching.py |
| ECH-ENGINE-015 | P2 | api.py |
| ECH-ENGINE-016 | P3 | order_book.py |

**Summary:** P0: 4, P1: 5, P2: 6, P3: 1
