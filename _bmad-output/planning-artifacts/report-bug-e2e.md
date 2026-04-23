# Báo cáo Bug — E2E Integration Test

**Dự án:** Matching Engine (client + exchange/admin + exchange/engine)
**Checklist:** `napo/linhktt/brd-order.md`
**Ngày chạy:** 2026-04-23
**Người test:** QA automation (E2E runner)
**File test:** `matching-engine/exchange/engine/tests/e2e_runner.py`, `e2e_extra.py`
**Kết quả log JSON:** `/tmp/e2e_results.json`

---

## 1. Tổng hợp

| Hạng mục | Số lượng |
|---|---|
| Tổng số case đã chạy live (3 hệ thống) | **45** |
| Bổ sung case code-review / model-level | **5** |
| **Tổng case** | **50** |
| PASS | 45 (sau fix P0+P1+P2) / 34 (trước fix) |
| FAIL | 0 (live) + 0 (extra) = **0** |
| Bug đã FIX | **15 / 16** (3 P0 + 4 P1 + 7 P2 + 1 P3 bonus) |
| Bug còn lại | 1 (0 P0, 0 P1, 0 P2, 1 P3) |

### Phân loại Severity

| Severity | Tổng | Đã Fix | Còn lại |
|---|---|---|---|
| **P0 Blocker** | 3 | 3 ✅ | 0 |
| **P1 Critical** | 4 | 4 ✅ | 0 |
| **P2 High** | 7 | 7 ✅ | 0 |
| **P3 Low** | 2 | 1 | 1 |

> **Cập nhật 2026-04-23 (đợt 3):** Đã fix toàn bộ P0+P1+P2. Bonus E2E-013 (P3) được fix kèm do refactor Pydantic `Field(gt=0, le=...)` thay cho validator thủ công `must_be_positive`. Còn lại 1 bug P3 (E2E-017 reject reason không bao gồm chi tiết — mang tính cosmetic).
>
> **E2E runner đạt 45/45 PASS (100%).**

---

## 2. Môi trường & Điều kiện test

- Engine (`exchange/engine`): FastAPI + websockets, port 8000 (admin HTTP + `/ws/admin`) & 8765 (client WS)
- Admin UI (`exchange/admin`): không test trực tiếp qua UI, test qua REST `http://localhost:8000/api/*` và `ws://localhost:8000/ws/admin` (cùng kênh UI đang dùng)
- Client (`client`): không test trực tiếp qua UI React, test qua `ws://localhost:8765` (cùng kênh UI đang dùng)
- Stock mặc định: ACB (floor=20000, ceiling=30000, step=100, qty_step=100), FPT (50000–75000, step=500, qty_step=100), VCK (10000–15000, step=100, qty_step=100)
- Không trigger các input có thể crash engine (`price<0`, `qty<=0`, `ceiling<=floor`) bằng lệnh thật — các case này được flag từ code review.

---

## 3. Danh sách Bug

---

### E2E-001 — Trade price dùng giá TAKER thay vì MAKER

- [x] Fixed (commit local, 2026-04-23) — `order_book.py::_match` đổi `fill_price = incoming.price if incoming.price else best_price` → `fill_price = best_price` (luôn dùng giá của maker). Verified bằng E2E-005, E2E-008 (PASS) và unit test `test_price_improvement`, `test_price_priority_over_time`, `test_multiple_fills_across_levels` (xanh trở lại).
- **Severity:** P1 Critical
- **Description:** Khi lệnh taker là LIMIT có giá khác giá resting (maker), trade được book với giá của taker thay vì maker. Vi phạm quy tắc matching engine tiêu chuẩn "Trade price = resting order's price" (checklist DANH MỤC 1).
- **Reproduction:**
  1. Market OPEN. Đặt SELL LIMIT 25200 qty 100 (resting/maker) cho ACB.
  2. Đặt BUY LIMIT 25500 qty 100 (taker).
  3. Quan sát `trade.price` trong broadcast.
  4. Thực tế: `trade.price = 25500` (taker). Kỳ vọng: `25200` (maker).
- **Case liên quan:** E2E-005, E2E-008
- **Suggested fix:** Tại `exchange/engine/src/engine/order_book.py`, dòng 166, thay `fill_price = incoming.price if incoming.price else best_price` bằng `fill_price = best_price` để luôn dùng giá của lệnh resting (maker).

---

### E2E-002 — Time priority bị ngược: LIFO thay vì FIFO

- [x] Fixed (commit local, 2026-04-23) — `order_book.py::_match` đổi `queue[-1]` → `queue[0]` và `queue.pop()` → `queue.popleft()`. Verified bằng E2E-006 (PASS) và unit test `test_time_priority_at_same_price` (xanh trở lại).
- **Severity:** P1 Critical
- **Description:** Khi hai lệnh cùng giá (cùng price level), lệnh **đặt sau** được khớp trước, vi phạm quy tắc "Lệnh đặt trước > Lệnh đặt sau" (checklist DANH MỤC 1).
- **Reproduction:**
  1. Market OPEN.
  2. Đặt SELL LIMIT 25300 qty 100, `account=FIRST` (lệnh 1).
  3. Sau 150 ms, đặt SELL LIMIT 25300 qty 100, `account=SECOND` (lệnh 2).
  4. Đặt BUY LIMIT 25300 qty 100.
  5. Quan sát lệnh nào được FILLED. Thực tế: `SECOND`. Kỳ vọng: `FIRST`.
- **Case liên quan:** E2E-006
- **Suggested fix:** Tại `exchange/engine/src/engine/order_book.py`, dòng 164 (`resting = queue[-1]`) và dòng 199 (`queue.pop()`), đổi sang `queue[0]` và `queue.popleft()` để duyệt từ đầu deque (lệnh cũ nhất).

---

### E2E-003 — Admin chấp nhận `ceiling <= floor`, engine sẽ crash ở lệnh kế tiếp

- [x] Fixed (commit local, 2026-04-23) — `api.py::update_stock` validate `ceiling > floor` và `ceiling - floor >= price_step` TRƯỚC khi apply; verified bằng E2E-041 (PASS).
- **Severity:** P0 Blocker
- **Description:** `PUT /api/stocks/{symbol}` chỉ kiểm tra từng trường `> 0` nhưng **không** kiểm tra `ceiling > floor`. Sau khi ceiling<=floor được chấp nhận, chỉ cần 1 lệnh tiếp theo tới đúng symbol là engine gọi `os._exit(1)` — toàn bộ sàn sập. Data corruption/DoS.
- **Reproduction:**
  1. `PUT /api/stocks/ACB` với body `{"ceiling": 10000}` (trong khi `floor=20000`). Server trả `200 OK`.
  2. Gửi 1 lệnh bất kỳ cho ACB qua WS.
  3. Engine log FATAL `degenerate price range` và exit(1). Cả 3 service rơi khỏi orchestration.
- **Case liên quan:** E2E-041; xác nhận theo ghi chú trong `CLAUDE.md`.
- **Suggested fix:** Tại `exchange/engine/src/engine/api.py::update_stock`, **sau khi** merge `updates` với state hiện tại, validate `new_ceiling > new_floor` **và** `new_ceiling - new_floor >= price_step`; reject 400 nếu không thỏa.

---

### E2E-004 — Client có thể crash engine bằng `price < 0` hoặc `quantity <= 0`

- [x] Fixed (commit local, 2026-04-23) — `ws_server.py::_handle_new_order` reject `price<0`/`qty<=0` bằng `{type:'error'}` trước khi tạo Order; verified bằng `tests/e2e_p0_verify.py` (engine vẫn OPEN sau 3 lệnh bẩn).
- **Severity:** P0 Blocker
- **Description:** Lệnh gửi qua WS với `price < 0` hoặc `quantity <= 0` **không** được validate ở tầng WS/Order. Tới `MatchingEngine.submit_order` thì gặp envelope guard và gọi `os._exit(1)`. Bất kỳ client nào gửi 1 message JSON cũng kill được toàn bộ engine.
- **Reproduction (chỉ theory, không chạy live để tránh down engine):**
  ```json
  {"type":"new_order","cl_ord_id":"X","account":"A","symbol":"ACB",
   "side":"BUY","ord_type":"LIMIT","price":-1,"quantity":100}
  ```
  → Engine process `exit(1)`.
- **Case liên quan:** suy ra từ `matching.py:80-95` + `ws_server.py:124-147`.
- **Suggested fix:** Tại `exchange/engine/src/engine/ws_server.py::_handle_new_order`, reject sớm bằng `execution_report` nếu `price < 0`, `quantity <= 0`. Tốt hơn: biến 3 envelope guard trong `matching.py` thành reject mềm thay vì `os._exit`. Kết hợp với validation ở client UI (`OrderEntry.jsx`) thêm `min="0"` (qty) và cảnh báo khi `price<floor`.

---

### E2E-005 — `Order.fill()` không guard terminal state (FILLED/CANCELLED)

- [x] Fixed (commit local, 2026-04-23) — `models.py::Order.fill` raise `ValueError` nếu status ∈ {FILLED, CANCELLED, REJECTED}; verified bằng `tests/e2e_extra.py` (`extra_fill_allowed_after_FILLED=False`).
- **Severity:** P0 Blocker
- **Description:** Gọi `fill()` trên Order đã `FILLED` hoặc `CANCELLED` vẫn cộng thêm `filled_qty` và đổi status. Invariant `filled_qty <= quantity` và `leaves_qty >= 0` bị phá.
- **Reproduction:** (model-level, `e2e_extra.py`)
  ```python
  o = Order(..., quantity=100)
  o.fill(100, 25000)   # status=FILLED
  o.fill(50, 25000)    # expected: raise / no-op. actual: filled=150/100, leaves=-50
  ```
- **Case liên quan:** `[GUARD] extra_fill_allowed_after_FILLED=True, invariant_broken=True`
- **Suggested fix:** Tại `exchange/engine/src/engine/models.py::Order.fill`, đầu hàm thêm guard:
  ```python
  if self.status in (OrdStatus.FILLED, OrdStatus.CANCELLED, OrdStatus.REJECTED):
      raise ValueError(f"Cannot fill order in terminal state {self.status}")
  ```

---

### E2E-006 — `Order.cancel()` không guard terminal state (ghi đè FILLED thành CANCELLED)

- [x] Fixed (bonus cùng E2E-005) — `models.py::Order.cancel` raise `ValueError` nếu status đã terminal; verified `cancel_after_FILLED_allowed=False`.
- **Severity:** P1 Critical
- **Description:** Gọi `cancel()` trên Order đã `FILLED` đổi status sang `CANCELLED` và reset `leaves_qty=0`. Lịch sử trạng thái bị ghi đè.
- **Reproduction:**
  ```python
  o.fill(100, 25000)  # FILLED
  o.cancel()          # status → CANCELLED (sai)
  ```
- **Case liên quan:** `[GUARD] cancel_after_FILLED_allowed=True, status=CANCELLED`
- **Suggested fix:** Tương tự E2E-005, thêm guard ở đầu `Order.cancel`:
  ```python
  if self.status in (OrdStatus.FILLED, OrdStatus.CANCELLED, OrdStatus.REJECTED):
      raise ValueError(f"Cannot cancel order in terminal state {self.status}")
  ```

---

### E2E-007 — Gọi `fill()` sau `cancel()` tạo "ghost fill"

- [x] Fixed (bonus cùng E2E-005) — guard trong `Order.fill` cũng chặn trường hợp này; verified `fill_after_CANCELLED_allowed=False`.
- **Severity:** P1 Critical
- **Description:** Order đã `CANCELLED`, khi bị gọi `fill()` vẫn apply filled và đổi status thành `PARTIALLY_FILLED`. Trường hợp này không xảy ra theo design (cancelled order đã pop khỏi book), nhưng model cho phép → không an toàn.
- **Reproduction:**
  ```python
  o.cancel()        # CANCELLED
  o.fill(50, 25000) # status → PARTIALLY_FILLED, filled=50 (ghost fill)
  ```
- **Case liên quan:** `[GUARD] fill_after_CANCELLED_allowed=True`
- **Suggested fix:** Giống E2E-005 (guard ở `fill()`). Fix 1 nơi giải quyết cả E2E-005 và E2E-007.

---

### E2E-008 — Không validate Account (rỗng / whitespace / ký tự đặc biệt)

- [x] Fixed (2026-04-23) — `ws_server.py::_handle_new_order` trim + regex `^[A-Za-z0-9_-]+$`; reject với `type=error`. UI `OrderEntry.jsx` thêm `validate()` hiển thị lỗi trực tiếp. Verified E2E-015/016/017 (PASS).
- **Severity:** P2 High
- **Description:** Checklist DANH MỤC 2 yêu cầu Account "không rỗng, không whitespace, không ký tự đặc biệt". Engine hiện chấp nhận mọi giá trị, kể cả `""`, `"   "`, `"@#$!<>"`. Lệnh với account bẩn vẫn được khớp.
- **Reproduction:** 3 case E2E-015, E2E-016, E2E-017. Gửi WS `new_order` với `account=""` / `"   "` / `"@#$!<>"` → tất cả trả `FILLED` hoặc `NEW`, không reject.
- **Case liên quan:** E2E-015, E2E-016, E2E-017
- **Suggested fix:** Thêm validate ở `ws_server.py::_handle_new_order` trước khi tạo `Order`:
  ```python
  account = data.get("account", "").strip()
  if not account or not re.fullmatch(r"[A-Za-z0-9_-]+", account):
      return <error/reject>
  ```
  Đồng bộ thêm validate trong `client/src/components/OrderEntry.jsx` (trim + regex) để fail sớm.

---

### E2E-009 — Không validate Quantity là số nguyên (nhận số thập phân)

- [x] Fixed (2026-04-23) — helper `_coerce_int` trong `ws_server.py` reject `float`/`bool`, chỉ chấp nhận `int` (áp dụng cho cả `price` và `quantity`). Verified E2E-022 (PASS).
- **Severity:** P2 High
- **Description:** Checklist yêu cầu "chỉ cho nhập số nguyên dương". Engine hiện dùng `int(data["quantity"])` → `int(100.5) == 100` (truncate im lặng) và được FILLED. Sai dữ liệu gốc của client.
- **Reproduction:** E2E-022. Gửi `{"quantity": 100.5}` → server truncate thành 100, không error. Kỳ vọng REJECTED/error.
- **Case liên quan:** E2E-022
- **Suggested fix:** Ở `ws_server.py::_handle_new_order`, kiểm tra kiểu:
  ```python
  q = data["quantity"]
  if not isinstance(q, int) or isinstance(q, bool):
      <error>
  ```
  hoặc dùng Pydantic model cho JSON WS tương tự phía admin.

---

### E2E-010 — Không phát hiện trùng `cl_ord_id` trong cùng session

- [x] Fixed (2026-04-23) — `ws_server.py::_handle_client` giữ `set[str] seen_cl_ord_ids` theo connection; `_handle_new_order` check trước khi xử lý. Verified E2E-033 (PASS).
- **Severity:** P2 High
- **Description:** Checklist DANH MỤC 2 yêu cầu "hai lệnh cùng đẩy vào từ cùng session → reject lệnh thứ 2". Hiện tại engine chấp nhận cả hai (cùng `cl_ord_id`), có thể sinh double order.
- **Reproduction:** E2E-033. Gửi 2 lệnh cùng `cl_ord_id` từ 1 WS connection → cả hai đều NEW.
- **Case liên quan:** E2E-033
- **Suggested fix:** Ở `ws_server.py::_handle_client`, giữ `set` các `cl_ord_id` đã xử lý theo connection. Trùng → `execution_report REJECTED reason="Duplicate cl_ord_id"` **trước** khi submit vào engine.

---

### E2E-011 — Admin `price_step` nhận giá trị "quá lớn" (19 chữ số 9)

- [x] Fixed (2026-04-23) — `api.py::StockConfigUpdate` refactor sang Pydantic `Field(gt=0, le=_MAX_PRICE)` (1e12 VND cho floor/ceiling, 1e9 cho step). Verified E2E-042 (PASS).
- **Severity:** P2 High
- **Description:** Checklist DANH MỤC 3 yêu cầu "Không được nhập số quá lớn". `PUT /api/stocks/ACB` với `price_step=99999999999999999999` trả `200 OK`. Sau đó không có price nào align → mọi lệnh REJECTED. Ảnh hưởng rõ rệt: sàn cho symbol đó "đóng băng".
- **Reproduction:** E2E-042
- **Case liên quan:** E2E-042
- **Suggested fix:** Thêm upper bound cho các trường của `StockConfigUpdate` trong `api.py` (ví dụ `Field(le=1_000_000_000)` cho mỗi field), đồng thời validate ở UI (`StockConfig.jsx`).

---

### E2E-012 — Admin chấp nhận `ceiling - floor < price_step`

- [x] Fixed (bonus cùng E2E-003) — check `(new_ceiling - new_floor) >= new_price_step` ngay trong `update_stock`; verified bằng `e2e_extra.py` (`gap<step accepted? status=400`).
- **Severity:** P2 High
- **Description:** Checklist DANH MỤC 3 yêu cầu "Giá trần - Giá sàn phải đủ lớn để chứa ít nhất 1 bước giá". Hiện `PUT` với `floor=25000, ceiling=25050, price_step=100` trả `200 OK`. Kết quả: không price nào align → symbol "đóng băng".
- **Reproduction:** `e2e_extra.py` → `[ADMIN] gap<step accepted? status=200`
- **Case liên quan:** extra
- **Suggested fix:** Như E2E-003, trong `update_stock`, validate `(new_ceiling - new_floor) >= new_price_step` và `(new_ceiling - new_floor) % new_price_step == 0` (tùy nghiệp vụ); reject 400.

---

### E2E-013 — Admin trả 500 khi gửi kiểu chữ cho trường int thay vì 422

- [x] Fixed (bonus cùng E2E-011) — bỏ validator thủ công `must_be_positive` mode="before", dùng `Field(gt=0, le=...)` để Pydantic v2 handle coercion lẫn range check đúng → nhận `"abc"` cho int field trả 422. Verified E2E-040 (PASS).
- **Severity:** P3 Low
- **Description:** `PUT /api/stocks/ACB` với `{"floor":"abc"}` trả `500 Internal Server Error` thay vì `400/422` (nghĩa là server báo lỗi validation đúng nhưng sai mã HTTP). Ảnh hưởng client UX: UI hiện thông báo "Server error" thay vì "Invalid format".
- **Reproduction:** E2E-040
- **Case liên quan:** E2E-040
- **Suggested fix:** Đặt `mode="before"` trong validator `must_be_positive` vẫn dùng — nhưng đảm bảo Pydantic v2 xử lý kiểu sai thành 422. Kiểm tra lại thứ tự validator và wrap `update_stock` với try/except để trả 422/400 cho ValidationError (hiện một số nhánh validator chạy trước khi Pydantic coerce xong).

---

### E2E-014 — Client UI không validate `price < 0`, `price < floor`, `qty <= 0`

- [x] Fixed (2026-04-23) — `OrderEntry.jsx` có hàm `validate()` đầy đủ (account regex, qty integer+bội, price floor/ceiling/step). Input thêm `min="1"`, `step="1"`. Hiển thị `formError` trực tiếp.
- **Severity:** P2 High
- **Description:** `client/src/components/OrderEntry.jsx` chỉ check `!form.account || !form.quantity || (ord_type==LIMIT && !form.price)` (empty-string). Người dùng gõ `-100` cho price hoặc qty → submit thẳng → engine crash (xem E2E-004). UI cần là "first line of defense".
- **Reproduction:** Mở `http://localhost:5173`, điền price `-100` → click Place Order → engine tắt.
- **Case liên quan:** E2E-004 (root cause chung)
- **Suggested fix:** Thêm `min="0"` (hoặc `min={snapshots[symbol]?.floor}` cho price) trên các input, thêm client-side check `Number(form.price) > 0 && form.price % price_step === 0` và `quantity > 0 && quantity % qty_step === 0` trước khi gọi `sendOrder`.

---

### E2E-015 — Admin UI không validate `ceiling > floor` trước khi Save

- [x] Fixed (2026-04-23) — `StockConfig.jsx::StockRow` thêm `validateForm()` check: số nguyên dương, `ceiling > floor`, `ceiling - floor >= price_step`; báo lỗi ngay trước khi gọi `onSave`.
- **Severity:** P2 High
- **Description:** `exchange/admin/src/components/StockConfig.jsx` chỉ parse `parseInt(...) || 0` và gọi `onSave` thẳng. Admin có thể Save config sai (ceiling<floor, gap<step, step=0 giả do parseInt), góp phần vào E2E-003 và E2E-012.
- **Reproduction:** Mở admin UI, Edit ACB: ceiling=10000 (trong khi floor=20000), Save → server chấp nhận → sàn chờ crash ở lệnh kế.
- **Case liên quan:** E2E-003, E2E-012 (root cause chung)
- **Suggested fix:** Trong `handleSave` của `StockRow`, check `form.ceiling > form.floor` và `(form.ceiling - form.floor) >= form.price_step` trước khi gọi `onSave`; báo lỗi trực tiếp UI (đã có sẵn `setError`).

---

### E2E-016 — Không có cơ chế chặn đặt lệnh bên client khi market CLOSED (UX)

- [x] Fixed (2026-04-23) — (a) Thêm broadcast `{type:"market_state"}` từ `api.py::start_market`/`stop_market` qua `ws_server.broadcast_market_state`. (b) `useWebSocket.js` capture state từ snapshot + message mới. (c) `OrderEntry.jsx` disable Place Order và Auto-gen khi `marketState !== "OPEN"`, hiển thị banner "Phiên đang CLOSED". (d) Header app hiển thị trạng thái "Market: OPEN/CLOSED".
- **Severity:** P2 High
- **Description:** Engine đã reject khi `CLOSED`, nhưng client UI (`OrderEntry.jsx`) vẫn cho nhấn Place Order và hiển thị REJECTED sau đó. UX kém; hoặc user có thể auto-gen dồn hàng trăm REJECTED. (Log bloat: thấy rõ khi auto-gen được bật.)
- **Reproduction:** Stop market → client vẫn gửi đầy đủ; execReports liên tục hiển thị REJECTED.
- **Case liên quan:** quan sát chung, không thấy trong test runner.
- **Suggested fix:** Truyền `market_state` từ snapshot/update xuống `OrderEntry.jsx`; disable nút Place Order + Auto khi `CLOSED` và hiển thị banner.

---

## 4. Phụ lục — Các case PASS đáng chú ý

Các case sau đã PASS — nghiệp vụ quan trọng hoạt động đúng:

- **Price priority** (price level priority): BUY khớp ask thấp nhất **về mặt level** (nhưng sai fill_price — xem E2E-001).
- **MARKET trên book rỗng → CANCELLED** (E2E-007 trong runner).
- **Invariant `filled_qty + leaves_qty == quantity`** giữ đúng sau partial fill ở runtime (E2E-009, E2E-010 runner — khác với E2E-005 ở đây, không vi phạm khi chưa rơi vào terminal).
- **Market closed reject trước matching** với reason `"Market is closed"` (E2E-014 runner).
- **Validate price floor/ceiling/step** và **qty_step** trong engine (E2E-024/25/26/27/28).
- **Unknown/blank symbol** bị reject (E2E-030/31/32).
- **Admin pydantic `must_be_positive`** chặn float 0/âm cho int field (E2E-038/39).
- **Admin WS snapshot push 0.5s** cập nhật bids/trades/logs realtime (E2E-043/44/45).

---

## 5. Quy trình đề xuất tiếp theo

### 5.1 Đã hoàn thành

**Đợt 1 (2026-04-23 P0):**
- ✅ Fix 3 bug P0 (E2E-003, E2E-004, E2E-005).
- ✅ Bonus fix cùng root cause: E2E-006 (P1), E2E-007 (P1), E2E-012 (P2).

**Đợt 2 (2026-04-23 P1):**
- ✅ Fix 2 bug P1 còn lại (E2E-001 fill_price maker, E2E-002 FIFO).
- ✅ Unit test: **116 pass / 0 fail** (trước: 112/4 — 4 fail là chính 2 P1 này).
- ✅ E2E runner: **39/45 PASS** (trước đợt 1: 34/45, trước đợt 2: 36/45).

**Đợt 3 (2026-04-23 P2):**
- ✅ Fix 6 bug P2 trực tiếp (E2E-008, E2E-009, E2E-010, E2E-011, E2E-014, E2E-015, E2E-016).
- ✅ Bonus fix P3 (E2E-013) cùng refactor Pydantic.
- ✅ Unit test: **116 pass / 0 fail**.
- ✅ E2E runner: **45/45 PASS — 100%**.
- ✅ ESLint client + admin: **clean**.

### 5.2 Bug còn lại

| Bug | Severity | Ghi chú |
|---|---|---|
| (không có E2E ID) — Client UI không revalidate khi stock config đổi realtime | P3 Low | Cosmetic; resting orders trên engine cũng không revalidate theo thiết kế (`CLAUDE.md`). Không ảnh hưởng trade logic. |

### 5.3 Regression

Sau mỗi đợt fix:
```bash
cd matching-engine/exchange/engine
uv run pytest                           # unit
uv run python tests/e2e_runner.py       # integration 3 hệ thống
uv run python tests/e2e_extra.py        # model-level guards + admin gap
uv run python tests/e2e_p0_verify.py    # P0-specific (price<0, qty<=0)
```

---

_File này được sinh bởi E2E automation runner. Dev có thể reproduce bằng 2 script trong `matching-engine/exchange/engine/tests/`._
