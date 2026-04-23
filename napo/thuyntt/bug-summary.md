# Bug Summary — E2E Integration Test
**Ngày:** 2026-04-23 · **Tổng:** 15 bug (đã loại E2E-007 trùng E2E-005) · **Fixed:** 0 / 15

> E2E-007 bị loại: "fill() after CANCELLED" dùng cùng guard fix với E2E-005 — report gốc ghi rõ "Fix 1 nơi giải quyết cả E2E-005 và E2E-007".

---

| ID | Severity | Module | File Location | Description | Suggested Fix |
|---|---|---|---|---|---|
| E2E-001 | P1 Critical | OrderBook | `exchange/engine/src/engine/order_book.py:166` | Trade price dùng giá taker thay vì maker — vi phạm quy tắc "fill price = resting order's price" | Đổi `fill_price = incoming.price if incoming.price else best_price` → `fill_price = best_price` |
| E2E-002 | P1 Critical | OrderBook | `exchange/engine/src/engine/order_book.py:164,199` | Time priority bị ngược: LIFO thay vì FIFO — lệnh đặt sau được khớp trước | Đổi `queue[-1]` → `queue[0]` và `queue.pop()` → `queue.popleft()` |
| E2E-003 | P0 Blocker | Admin API | `exchange/engine/src/engine/api.py` (`update_stock`) | `PUT /api/stocks/{symbol}` chấp nhận `ceiling <= floor`; lệnh kế tiếp trigger `os._exit(1)` — toàn sàn sập | Sau merge updates, validate `new_ceiling > new_floor` và `new_ceiling - new_floor >= price_step`; reject 400 nếu sai |
| E2E-004 | P0 Blocker | WS Server / MatchingEngine | `exchange/engine/src/engine/ws_server.py:124-147`, `matching.py:80-95` | Lệnh WS với `price < 0` hoặc `quantity <= 0` không bị chặn sớm; tới engine guard → `os._exit(1)` | Validate và reject bằng `execution_report` tại `_handle_new_order` trước khi vào engine; cân nhắc chuyển guard thành reject mềm |
| E2E-005 | P0 Blocker | Order Model | `exchange/engine/src/engine/models.py` (`Order.fill`, `Order.cancel`) | `fill()` trên Order đã FILLED/CANCELLED vẫn cộng `filled_qty`; phá invariant `leaves_qty >= 0` (đồng thời che phủ E2E-007: fill-after-cancel) | Thêm guard đầu `fill()`: `if self.status in (FILLED, CANCELLED, REJECTED): raise ValueError(...)` |
| E2E-006 | P1 Critical | Order Model | `exchange/engine/src/engine/models.py` (`Order.cancel`) | `cancel()` trên Order đã FILLED ghi đè status thành CANCELLED — mất lịch sử trạng thái | Thêm guard đầu `cancel()`: `if self.status in (FILLED, CANCELLED, REJECTED): raise ValueError(...)` |
| E2E-008 | P2 High | WS Server | `exchange/engine/src/engine/ws_server.py` (`_handle_new_order`) | Account rỗng / whitespace / ký tự đặc biệt được chấp nhận và lệnh vẫn khớp | Validate `account` bằng `re.fullmatch(r"[A-Za-z0-9_-]+", account)` trước khi tạo Order; đồng bộ `OrderEntry.jsx` |
| E2E-009 | P2 High | WS Server | `exchange/engine/src/engine/ws_server.py` (`_handle_new_order`) | `quantity=100.5` bị truncate im lặng thành `100` thay vì reject | Kiểm tra `isinstance(q, int) and not isinstance(q, bool)` hoặc dùng Pydantic model cho WS payload |
| E2E-010 | P2 High | WS Server | `exchange/engine/src/engine/ws_server.py` (`_handle_client`) | Trùng `cl_ord_id` trong cùng session không bị reject — có thể sinh double order | Giữ `set` các `cl_ord_id` per-connection; trùng → `execution_report REJECTED reason="Duplicate cl_ord_id"` |
| E2E-011 | P2 High | Admin API | `exchange/engine/src/engine/api.py` (`StockConfigUpdate`) | `price_step=99999999999999999999` được chấp nhận — mọi lệnh sau bị REJECTED, symbol đóng băng | Thêm upper bound `Field(le=1_000_000_000)` cho các field của `StockConfigUpdate`; validate ở `StockConfig.jsx` |
| E2E-012 | P2 High | Admin API | `exchange/engine/src/engine/api.py` (`update_stock`) | `ceiling - floor < price_step` được chấp nhận — không price nào align, symbol đóng băng | Validate `(new_ceiling - new_floor) >= new_price_step` trong `update_stock`; reject 400 |
| E2E-013 | P3 Low | Admin API | `exchange/engine/src/engine/api.py` (`update_stock` validator) | `PUT` với `{"floor":"abc"}` trả `500` thay vì `422` | Đảm bảo Pydantic v2 trả 422 cho kiểu sai; wrap validator với try/except để chuẩn hóa mã lỗi |
| E2E-014 | P2 High | Client UI | `client/src/components/OrderEntry.jsx` | Không validate `price < 0`, `price < floor`, `qty <= 0` tại UI — người dùng gửi thẳng, engine crash (E2E-004) | Thêm `min="0"` trên input, check `price > 0 && price % price_step === 0` và `qty > 0 && qty % qty_step === 0` trước `sendOrder` |
| E2E-015 | P2 High | Admin UI | `exchange/admin/src/components/StockConfig.jsx` | Không validate `ceiling > floor` và `gap >= price_step` trước khi Save — góp phần E2E-003, E2E-012 | Trong `handleSave`, check `form.ceiling > form.floor` và `(form.ceiling - form.floor) >= form.price_step`; báo lỗi qua `setError` |
| E2E-016 | P2 High | Client UI | `client/src/components/OrderEntry.jsx` | Không disable Place Order khi market CLOSED — auto-gen dồn hàng trăm REJECTED, bloat log | Truyền `market_state` từ snapshot; disable nút + Auto khi `CLOSED`; hiển thị banner |
