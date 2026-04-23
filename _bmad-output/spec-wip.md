---
title: 'Session high/low realtime per stock on Client UI'
type: 'feature'
created: '2026-04-23'
status: 'draft'
context:
  - '_bmad-output/architecture.md'
  - '_bmad-output/data-model.md'
  - 'matching-engine/CLAUDE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Client UI không hiển thị giá cao nhất / thấp nhất theo phiên cho từng mã. Trader không thấy được biên độ giao dịch realtime, chart hiện tại chỉ show giá trade theo thời gian.

**Approach:** Engine tính `session_high` / `session_low` từ `engine._trades` khi build `market_snapshot` (seed cho client vào trễ / reconnect). Client tự cập nhật delta trên mỗi `trade` event đã broadcast sẵn. Hiển thị kế tiêu đề từng symbol trong `MarketData.jsx`.

## Boundaries & Constraints

**Always:**
- Chỉ đọc `engine._trades` — KHÔNG thêm state mới trong `OrderBook` hay `MatchingEngine`.
- Không đụng matching path (`process_order`, `_match`, `submit_order`). Không đổi broadcast model.
- Symbol key uppercase như mọi entry point khác (data-model.md §Order).
- Snapshot field mới là optional / nullable — empty trades → `null`, không throw.
- Client seed từ snapshot rồi delta update; `trade` event vẫn là nguồn realtime.

**Ask First:**
- Nếu muốn reset high/low khi Admin `open_market` / `close_market` (hiện `_trades` không clear giữa các phiên — sẽ là quyết định policy).
- Nếu muốn thêm field khác (open price, change %, volume) vào cùng iteration này.

**Never:**
- Không persist gì ra DB / file (architecture.md §Persistence).
- Không thêm REST endpoint mới cho high/low (admin đã có `/api/trades` nếu cần).
- Không re-validate resting orders khi đổi floor/ceiling (CLAUDE.md §Invariants).
- Không gây `os._exit(1)` — tránh mọi path có thể trigger `price<0` / `qty<=0` / `ceiling<=floor` check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Snapshot khi chưa có trade nào | `engine._trades` rỗng cho symbol X | `session_high=null`, `session_low=null` trong `market_snapshot` của X | Client hiển thị "—" |
| Snapshot sau vài trade | Trades [20100, 20200, 20000] cho ACB | `session_high=20200`, `session_low=20000` | N/A |
| Trade mới cao hơn high hiện tại | Client đang có `high=20200`, nhận `trade` price=20300 | `high` update thành 20300 | N/A |
| Trade mới bằng high/low hiện tại | `high=20200`, nhận `trade` price=20200 | `high` giữ 20200 (dùng `>=` không cần thiết) | N/A |
| Client reconnect | Socket drop → auto-reconnect 2s → nhận snapshot mới | Reseed `highLow[symbol]` từ snapshot, không giữ state cũ | N/A |
| Symbol chưa có trade nào (MARKET chưa mở) | Snapshot với `session_high=null` | Client render "—" thay vì `NaN` / `0` | N/A |

</frozen-after-approval>

## Code Map

- `matching-engine/exchange/engine/src/engine/ws_server.py` -- `_build_market_snapshot` — nơi thêm `session_high/low` vào payload (đã có `engine.get_trades(symbol)` handy).
- `matching-engine/exchange/engine/src/engine/matching.py` -- `get_trades(symbol)` — dùng sẵn, không sửa.
- `matching-engine/exchange/engine/tests/test_ws.py` -- nơi add test snapshot có 2 field mới.
- `matching-engine/client/src/hooks/useWebSocket.js` -- Add state `highLow`, xử lý trong handler `market_snapshot` + `trade`.
- `matching-engine/client/src/components/MarketData.jsx` -- Render `High: ... / Low: ...` trong header symbol.

## Tasks & Acceptance

**Execution:**
- [ ] `exchange/engine/src/engine/ws_server.py` -- Trong `_build_market_snapshot`, compute `prices=[t.price for t in self.engine.get_trades(symbol)]`; thêm `session_high = max(prices) if prices else None`, `session_low = min(prices) if prices else None` vào dict trả về. -- Seed cho client vào trễ / reconnect.
- [ ] `exchange/engine/tests/test_ws.py` -- Thêm test: (a) snapshot khi không có trade → `session_high/low = None`; (b) sau vài trade → `session_high = max`, `session_low = min`. -- Lock invariant.
- [ ] `client/src/hooks/useWebSocket.js` -- Thêm `highLow` state (`{ [symbol]: { high, low } }`). Trong `market_snapshot` handler, seed từ `session_high/low`. Trong `trade` handler, `high = Math.max(cur?.high ?? trade.price, trade.price)`, `low = Math.min(cur?.low ?? trade.price, trade.price)`. Expose qua return value. -- Delta + seed.
- [ ] `client/src/components/MarketData.jsx` -- Nhận `highLow` prop (hoặc đọc từ hook). Render "High: X / Low: Y" cạnh tên symbol; nếu `null` → "—". -- UI.

**Acceptance Criteria:**
- Given engine vừa khởi động, market OPEN, chưa có trade, when client connect và nhận snapshot, then UI hiển thị "High: — / Low: —" cho mọi symbol.
- Given đã có 3 trade cho ACB tại giá 20100, 20200, 20000, when client **mới** connect và nhận snapshot, then UI hiển thị "High: 20200 / Low: 20000".
- Given client đang hiển thị "High: 20200 / Low: 20000", when nhận `trade` với price=20300, then UI update thành "High: 20300 / Low: 20000" không cần reload.
- Given 2 tab client đang mở cùng lúc, when tab A đặt lệnh match tạo trade mới, then cả tab A và B đều thấy high/low update cùng lúc (qua `_broadcast_json_all`).
- Given pytest suite hiện tại, when chạy `uv run pytest` trong `exchange/engine/`, then toàn bộ test cũ pass + test mới pass.

## Verification

**Commands:**
- `cd matching-engine/exchange/engine && uv run pytest` -- expected: tất cả test pass, bao gồm 2 test mới trong `test_ws.py`.
- `cd matching-engine && ./startall.sh` (hoặc `.\startall.ps1`) -- expected: 3 service lên, không crash.

**Manual checks:**
- Mở Admin (3001) → Start Market. Mở 2 tab Client (5173). Verify high/low hiển thị "—" ban đầu.
- Đặt lệnh match nhau ở ACB tại 20100 × 100 → cả 2 tab thấy "High: 20100 / Low: 20100".
- Đặt thêm trade ở 20200, rồi 20000 → cả 2 tab thấy "High: 20200 / Low: 20000".
- Close tab 1, mở lại → tab mới hiển thị đúng "High: 20200 / Low: 20000" (seed từ snapshot).
- Restart engine → high/low reset về "—" (đúng design, no persistence).
