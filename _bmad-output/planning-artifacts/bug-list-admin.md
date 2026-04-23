# Bug List — Admin Module

Module: `matching-engine/exchange/admin` (Vite + React 19 Admin UI).
Source chính: `ECH` (Edge Case Hunter path tracing) — bổ sung các path rẽ nhánh / boundary không có guard trong diff.

---

## ECH-ADMIN-001

- [x] Fixed
- **Severity**: P0 Blocker
- **Module**: `admin/StockConfig`
- **Location**: `matching-engine/exchange/admin/src/components/StockConfig.jsx:26-34`
- **Fix-summary**: Added pure helper `src/lib/validateStockConfig.js` enforcing `floor>0`, `ceiling>0`, `ceiling>floor`, `price_step>0`, `qty_step>0`. `StockRow.handleSave` now runs the guard first and shows a human-readable error inline instead of POSTing the bad payload — engine no longer self-destructs on `ceiling<=floor`. Coverage: `matching-engine/exchange/admin/test/unit/validateStockConfig.test.js` (6 cases) via `node --test`; added `npm test` script.
- **Description**: Form Save stock config không validate mối quan hệ giữa các field (`ceiling > floor`, `price_step > 0`, `qty_step > 0`, `(ceiling-floor) % price_step == 0`). Chỉ `parseInt(...) || 0` ở onChange (line 45-47). User nhập `ceiling <= floor` (ví dụ floor=20000, ceiling=15000) rồi Save → gửi PUT `/api/stocks/{symbol}` với payload hợp lệ với `StockConfigUpdate` (chỉ kiểm `> 0`) → server accept và `book.config` bị cập nhật.
- **Root cause**: Không có client-side invariant guard; không có server-side guard trong `update_stock_config`. Admin UI là điểm cuối cùng có thể chặn ceiling<=floor trước khi engine self-destruct.
- **Impact**: Order kế tiếp rơi vào `MatchingEngine.submit_order` → envelope check `ceiling <= floor` → `os._exit(1)`. Engine chết, mất toàn bộ state RAM (books, trades, configs do Admin vừa sửa, comm logs). Demo vỡ, client UI mất WS, phải `./startall.sh` lại.
- **Reproduction**:
  1. `./startall.sh`
  2. Mở Admin UI `http://localhost:3001`, Start Market
  3. Edit stock `ACB`, đổi `ceiling` = 10000 (nhỏ hơn floor 20000), bấm Save — request trả 200.
  4. Từ Client UI đặt bất kỳ lệnh LIMIT/MARKET nào cho `ACB`.
  5. Engine process exit code 1, Admin UI chuyển Disconnected, client WS đóng.
- **Evidence**:

```jsx
// StockConfig.jsx:26-34
const handleSave = async () => {
  try {
    await onSave(symbol, form);      // form có thể chứa ceiling <= floor
    setEditing(false);
    setError("");
  } catch (e) {
    setError(e.message);
  }
};
```

- **Suggested fix**: Thêm validate trước `onSave`: nếu `form.ceiling <= form.floor` hoặc `form.price_step <= 0` hoặc `form.qty_step <= 0` → `setError("Ceiling must be greater than floor")` và return. Lý tưởng: cũng sửa server-side `update_stock_config` để từ chối, nhưng ở scope admin UI đủ để bảo vệ demo.
- **Source**: ECH

---

## ECH-ADMIN-002

- [x] Fixed
- **Severity**: P1 Critical
- **Module**: `admin/CommLogs`
- **Location**: `matching-engine/exchange/admin/src/components/CommLogs.jsx:4,11,38-64`
- **Fix-summary**: Added pure helper `src/lib/commLogIdentity.js` with `getLogKey(log)` (stable composite of `timestamp|direction|client_id|message_type|summary`) and `findExpandedLog(display, expandedKey)`. `CommLogs.jsx` replaces index-based `expanded` with `expandedKey`, and reads `fix_raw` from the log resolved by key — so when logs shift after a 0.5s tick, the expanded row still tracks the log the user originally clicked (or collapses if that log has been evicted past the 100-row window). Coverage: `matching-engine/exchange/admin/test/unit/commLogIdentity.test.js` (6 cases, including the shift-after-prepend repro) via `node --test`.
- **Description**: `expanded` state lưu chỉ số index trong mảng `display` (line 43 `setExpanded(expanded === i ? null : i)`). Mỗi 0.5s WS push lại full `logs`, `useAdminWebSocket` ghi đè toàn bộ state → `display = filtered.slice(-100).reverse()` có thể đổi thứ tự / chèn log mới ở đầu. Row tại index `i` giờ là log khác, nhưng `expanded === i` vẫn true → `log.fix_raw` hiển thị thuộc về log MỚI, không phải log user đã click.
- **Root cause**: Expanded dùng index làm identity; logs không có client-stable ID (server gửi theo thứ tự time, không gắn id).
- **Impact**: User xem raw FIX của log cũ, tick sau đột nhiên nhảy sang raw FIX của log mới hoàn toàn. Gây hiểu nhầm nghiêm trọng khi debug FIX trace, đặc biệt lúc tải cao (auto-generator client flood logs).
- **Reproduction**:
  1. Mở Admin + Client, Start Market.
  2. Từ Client bật auto-generator (hoặc gửi nhiều lệnh liên tục).
  3. Trong Admin → CommLogs, click expand một dòng `D` (NewOrderSingle).
  4. Giữ nguyên, chờ vài tick 0.5s.
  5. Dòng raw FIX bên dưới thay đổi nội dung mặc dù user không click.
- **Evidence**:

```jsx
// CommLogs.jsx:11, 43, 56
const display = filtered.slice(-100).reverse();
...
onClick={() => setExpanded(expanded === i ? null : i)}
...
{expanded === i && log.fix_raw && (
  <tr key={`${i}-fix`} className="fix-row">
    <td colSpan="5"><code className="fix-raw">{log.fix_raw}</code></td>
  </tr>
)}
```

- **Suggested fix**: Dùng composite id thay vì index, ví dụ `setExpanded(\`${log.timestamp}-${log.client_id}-${log.message_type}-${log.summary}\`)`, hoặc track `expandedLog` object và so sánh ref.
- **Source**: ECH

---

## ECH-ADMIN-003

- [x] Fixed
- **Severity**: P1 Critical
- **Module**: `admin/CommLogs`
- **Location**: `matching-engine/exchange/admin/src/components/CommLogs.jsx:38-64`
- **Fix-summary**: Imported `Fragment` from `react` and replaced the `<>...</>` shorthand inside `display.map` with `<Fragment key={`${key}-${i}`}>…</Fragment>`, dropping the now-redundant `key` props on the inner `<tr>`s. List reconciliation now has a stable, unique key at the top-level item, so prepended logs per 0.5s tick no longer reuse wrong DOM rows and React stops emitting the "unique key prop" warning. Coverage: `matching-engine/exchange/admin/test/unit/commLogsFragmentKey.test.js` (3 source-level assertions) via `node --test`.
- **Description**: Ở `display.map((log, i) => (<>...</>))` dùng Fragment shorthand `<>...</>` bọc 2 `<tr>` nhưng không (và không thể) gán `key` trên shorthand fragment. Key duy nhất là trên `<tr>` con (`key={i}`, `key={\`${i}-fix\`}`). Khi số lượng row ở cấp map thay đổi giữa các render (ví dụ expanded chuyển từ i=3 sang i=5 → render thêm fix row ở i=5, bỏ ở i=3), React reconciler không có key ổn định ở cấp fragment → DOM mount/unmount không đều, state con (nếu sau này thêm input) bị reset, và console spam warning.
- **Root cause**: Fragment shorthand không nhận prop `key`; phải dùng `<React.Fragment key={...}>`.
- **Impact**: React dev warning mỗi render. Nặng hơn: khi logs prepend mỗi tick, reconciliation reuse DOM sai hàng → flash visual, scroll jitter ở `table-scroll`.
- **Reproduction**:
  1. Mở DevTools console trong Admin UI.
  2. Start Market + auto-generator từ client.
  3. Quan sát console → hàng loạt warning "Each child in a list should have a unique 'key' prop" (hoặc key trùng `i`).
  4. Scroll logs thấy hàng nhấp nháy/nhảy chỗ khi tick mới đến.
- **Evidence**:

```jsx
// CommLogs.jsx:38-64
{display.map((log, i) => (
  <>
    <tr key={i} className={`log-row ${log.direction.toLowerCase()}`} ...>
      ...
    </tr>
    {expanded === i && log.fix_raw && (
      <tr key={`${i}-fix`} className="fix-row">...</tr>
    )}
  </>
))}
```

- **Suggested fix**: Đổi `<>...</>` thành `<React.Fragment key={\`${log.timestamp}-${i}\`}>...</React.Fragment>`, bỏ `key` ở tr con (hoặc giữ nhưng không còn trùng).
- **Source**: ECH

---

## ECH-ADMIN-004

- [ ] Fixed
- **Severity**: P1 Critical
- **Module**: `admin/App`
- **Location**: `matching-engine/exchange/admin/src/App.jsx:15-25`
- **Description**: `handleStart`, `handleStop` `await api.startMarket()` / `api.stopMarket()` không bọc try/catch. Nếu API trả non-2xx (ví dụ market đã OPEN → `POST /api/market/start` trả 400 từ `api.py`), `useAdminApi.api` throw `new Error(data.detail || "HTTP 400")`. Error bubble thành unhandled promise rejection, không UI feedback. User bấm nút không thấy gì thay đổi (vì polling WS sẽ tự cập nhật khi thành công, nhưng khi thất bại không có tín hiệu).
- **Root cause**: Thiếu error handling ở các entry nhưng `handleSaveStock` cũng bị — tuy nhiên `handleSaveStock` delegate xuống `StockRow` đã có try/catch ở line 26-34 nên ok; `handleStart`/`handleStop` không có downstream catch.
- **Impact**: Silent failure cho thao tác thay đổi market state. User không biết vì sao nút bấm vô tác dụng; phải nhìn Network tab.
- **Reproduction**:
  1. Start Market → OPEN.
  2. Bấm Start Market thêm lần nữa (button vẫn render và giờ disabled khi isOpen=true nên khó trigger — nhưng khi `state?.market_state` là `undefined` lúc mới mở UI, isOpen=false cho cả stop và disabled=!isOpen). Thực tế: restart engine trong khi admin đang mở → Admin disconnected; reconnect, state chưa về kịp → user bấm Stop (không disabled do state=undefined) → API trả 400 "Market is already closed".
  3. Toàn bộ error chỉ log `Uncaught (in promise)`.
- **Evidence**:

```jsx
// App.jsx:15-25
const handleStart = async () => {
  await api.startMarket();                // throw → unhandled rejection
};
const handleStop = async () => {
  await api.stopMarket();
};
```

- **Suggested fix**: Bọc try/catch, lưu `errorMsg` state và render 1 toast/banner: `try { await api.startMarket() } catch (e) { setErrorMsg(e.message) }`.
- **Source**: ECH

---

## ECH-ADMIN-005

- [ ] Fixed
- **Severity**: P1 Critical
- **Module**: `admin/OrderBookView`
- **Location**: `matching-engine/exchange/admin/src/components/OrderBookView.jsx:1,44-54`
- **Description**: `SYMBOLS = ["ACB", "FPT", "VCK"]` hardcode. Nếu `DEFAULT_STOCKS` thay đổi (hoặc ai đó bổ sung stock vào `ExchangeConfig.stocks` qua code), OrderBookView không hiển thị book mới — dù `StockConfig` (line 72) render dynamic từ `state?.stocks`. Nếu server thay symbol (rename ACB → ACV), panel sẽ hiển thị "Empty book" cho symbol cũ.
- **Root cause**: Duplicate source of truth — component giữ list tĩnh thay vì đọc `Object.keys(books ?? {})` hoặc `Object.keys(stocks ?? {})`.
- **Impact**: Trader / ops không thấy order book của stock đang live; giao dịch vẫn chạy nhưng Admin mù. Inconsistency giữa `StockConfig` (dynamic) và `OrderBookView` (static) gây hiểu nhầm.
- **Reproduction**:
  1. Thêm entry vào `DEFAULT_STOCKS` ở `exchange/engine/src/engine/config.py` (ví dụ `"HPG"`) → restart engine.
  2. StockConfig panel hiển thị 4 stocks.
  3. OrderBookView vẫn chỉ 3 card (ACB/FPT/VCK), không có HPG.
- **Evidence**:

```jsx
// OrderBookView.jsx:1, 49-51
const SYMBOLS = ["ACB", "FPT", "VCK"];
...
{SYMBOLS.map((symbol) => (
  <BookCard key={symbol} symbol={symbol} book={books?.[symbol]} />
))}
```

- **Suggested fix**: `const symbols = Object.keys(books ?? {});` rồi map. Không dùng hằng.
- **Source**: ECH

---

## ECH-ADMIN-006

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/useAdminWebSocket`
- **Location**: `matching-engine/exchange/admin/src/hooks/useAdminWebSocket.js:51-57`
- **Description**: `onmessage` gọi thẳng `JSON.parse(event.data)` không try/catch. Nếu server gửi binary frame (sai hook), hoặc JSON malformed (ví dụ nửa chừng mất kết nối), handler throw → exception trong event callback → không reach `setState` → state cũ đông cứng. WebSocket vẫn OPEN, nên onclose không fire, connected vẫn true → UI Live nhưng dữ liệu đứng.
- **Root cause**: Thiếu try/catch bao quanh parse + dispatch.
- **Impact**: Admin hiển thị trạng thái cũ vô thời hạn, không ai nhận ra. Không có cách phục hồi nếu không force reload.
- **Reproduction**:
  1. Intercept WS (ví dụ Chrome DevTools → Network → WS, dùng override) hoặc chèn tạm `raise` trong `_get_admin_state` giả lập frame rỗng.
  2. Socket vẫn OPEN, client nhận frame non-JSON → UI giữ state cũ.
- **Evidence**:

```jsx
// useAdminWebSocket.js:51-57
ws.onmessage = (event) => {
  if (cancelled) return;
  const msg = JSON.parse(event.data);      // throws on bad payload
  if (msg.type === "admin_state") {
    setState(msg);
  }
};
```

- **Suggested fix**: `try { const msg = JSON.parse(event.data); if (msg?.type === "admin_state") setState(msg); } catch (err) { console.warn("bad admin frame", err); }`.
- **Source**: ECH

---

## ECH-ADMIN-007

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/useAdminApi`
- **Location**: `matching-engine/exchange/admin/src/hooks/useAdminApi.js:29,31,34`
- **Description**: `symbol` được nhúng thẳng vào URL template `\`/stocks/${symbol}\`` mà không `encodeURIComponent`. Nếu symbol chứa ký tự đặc biệt (space, `/`, `?`, `#`, unicode), URL bị malformed hoặc path bị split sai. Admin UI hiện chỉ có symbol do server cung cấp (ACB/FPT/VCK), nhưng nếu server thêm symbol có space / slash, request sẽ 404 hoặc hit endpoint khác.
- **Root cause**: Không encode path parameter.
- **Impact**: Admin không thao tác được với stock có ký tự không an toàn. Ít nguy hiểm nhưng là tech debt.
- **Reproduction**:
  1. Thêm stock `"A B"` vào `DEFAULT_STOCKS` (giả định).
  2. Edit stock, bấm Save → request URL `/api/stocks/A B` → fetch encode thành `A%20B` (browser tự handle phần path, nhưng kết quả có thể khác kỳ vọng nếu có `#`, `?`, `%`).
  3. Thực tế: ký tự `?` hoặc `#` sẽ bị parse là query/fragment, request sai hoàn toàn.
- **Evidence**:

```jsx
// useAdminApi.js:29-35
const getStock = useCallback((symbol) => api(`/stocks/${symbol}`), [api]);
const updateStock = useCallback(
  (symbol, data) => api(`/stocks/${symbol}`, { method: "PUT", body: JSON.stringify(data) }),
  [api]
);
const getOrderBook = useCallback((symbol) => api(`/orderbook/${symbol}`), [api]);
const getTrades = useCallback((symbol) => api(`/trades${symbol ? `?symbol=${symbol}` : ""}`), [api]);
```

- **Suggested fix**: Dùng `encodeURIComponent(symbol)` ở cả 4 helper (`getStock`, `updateStock`, `getOrderBook`, `getTrades`).
- **Source**: ECH

---

## ECH-ADMIN-008

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/StockConfig`
- **Location**: `matching-engine/exchange/admin/src/components/StockConfig.jsx:43-48`
- **Description**: `onChange` dùng `parseInt(e.target.value) || 0`. Trường hợp user xóa input → `e.target.value === ""` → `parseInt("") === NaN` → `|| 0` → form field thành 0. Nếu user bấm Save ngay → payload gửi `floor: 0, ...`. `StockConfigUpdate` Pydantic kiểm `> 0` sẽ reject (422), nhưng nếu validation đó thả ra trong tương lai, 0 sẽ làm `validate_price` cho phép mọi giá (step check `(p - 0) % price_step == 0` nếu step=100 thì chỉ price bội 100, nhưng floor=0 nghĩa là không có giá sàn).
- **Root cause**: Fallback 0 im lặng làm mất tín hiệu "user đang clear input". Không phân biệt undefined / 0.
- **Impact**: UX kém (không báo lỗi giá trị rỗng), phụ thuộc server validation bảo vệ. Nếu server cho qua thì invariant sàn/trần broken.
- **Reproduction**:
  1. Edit ACB, xóa ô `floor` trống.
  2. Save → server 422.
  3. Error hiển thị "422 Unprocessable Entity" thay vì "Floor must be positive".
- **Evidence**:

```jsx
// StockConfig.jsx:43-48
<input
  type="number"
  value={form[key]}
  onChange={(e) =>
    setForm({ ...form, [key]: parseInt(e.target.value) || 0 })
  }
/>
```

- **Suggested fix**: Giữ string trong state, chỉ parse khi Save; hoặc dùng `Number.isNaN(n) ? "" : n` và thêm disabled Save nếu bất kỳ field rỗng / ≤ 0.
- **Source**: ECH

---

## ECH-ADMIN-009

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/TradeHistory`
- **Location**: `matching-engine/exchange/admin/src/components/TradeHistory.jsx:37-44`
- **Description**: Các field `t.time`, `t.price`, `t.quantity`, `t.buy_order_id`, `t.sell_order_id` được gọi method (`.toLocaleString()`, `.slice(-10)`, `new Date(t.time * 1000)`) mà không guard undefined/null. Nếu server (hoặc future schema) thiếu field hoặc set null, toàn bộ render throw → "Something went wrong" ở toàn bộ component tree không có ErrorBoundary.
- **Root cause**: Không có defensive coding cho field WS outbound; phụ thuộc contract server.
- **Impact**: Một trade dị thường có thể crash cả panel TradeHistory (và vì App không có ErrorBoundary, hỏng toàn UI).
- **Reproduction**:
  1. Gây một trade có `buy_order_id = null` (ví dụ qua debug breakpoint trong `MatchingEngine._trades.append(...)`).
  2. Tick 0.5s đến → `t.buy_order_id.slice(-10)` throw `TypeError: Cannot read properties of null`.
  3. React StrictMode log error, component crash.
- **Evidence**:

```jsx
// TradeHistory.jsx:37-44
<td>{t.trade_id}</td>
<td>{new Date(t.time * 1000).toLocaleTimeString()}</td>
<td>{t.symbol}</td>
<td className="price">{t.price.toLocaleString()}</td>
<td>{t.quantity.toLocaleString()}</td>
<td title={t.buy_order_id}>{t.buy_order_id.slice(-10)}</td>
<td title={t.sell_order_id}>{t.sell_order_id.slice(-10)}</td>
```

- **Suggested fix**: `t.price?.toLocaleString() ?? ""`, `t.buy_order_id?.slice(-10) ?? ""`, kiểm `Number.isFinite(t.time)` trước khi format date.
- **Source**: ECH

---

## ECH-ADMIN-010

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/CommLogs`
- **Location**: `matching-engine/exchange/admin/src/components/CommLogs.jsx:42,46,52-54`
- **Description**: `log.direction.toLowerCase()`, `log.message_type`, `log.summary`, `log.client_id`, `log.timestamp` không guard. Cùng pattern như ECH-ADMIN-009. Đặc biệt `log.direction` dùng cả lowercase làm className, nếu `undefined` sẽ throw trước khi render dòng. Một frame WS thiếu field → crash panel.
- **Root cause**: Thiếu optional chain / default.
- **Impact**: Panel comm logs chết dẫn theo cả Admin UI (không ErrorBoundary).
- **Reproduction**: Giả lập frame có `direction: null` → `null.toLowerCase()` → TypeError.
- **Evidence**:

```jsx
// CommLogs.jsx:42, 46
className={`log-row ${log.direction.toLowerCase()}`}
...
<td>{new Date(log.timestamp * 1000).toLocaleTimeString()}</td>
```

- **Suggested fix**: `${(log.direction ?? "").toLowerCase()}`, kiểm `Number.isFinite(log.timestamp)` trước khi `new Date`.
- **Source**: ECH

---

## ECH-ADMIN-011

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/OrderBookView`
- **Location**: `matching-engine/exchange/admin/src/components/OrderBookView.jsx:6,33-37`
- **Description**: Nhánh `maxRows === 0` ở line 33 không bao giờ true vì `maxRows = Math.max(bids.length, asks.length, 1)` (line 6) đảm bảo tối thiểu bằng 1. Kết quả: khi book rỗng (bids=[], asks=[]), bảng render 1 row với 4 cell rỗng thay vì "Empty book".
- **Root cause**: `Math.max(..., 1)` cần cho `Array.from({length: maxRows})` để render tối thiểu 1 row skeleton, nhưng cùng giá trị lại dùng cho check empty → dead branch.
- **Impact**: UX: book rỗng nhìn như chưa load (một hàng trắng) thay vì nhãn rõ "Empty book". Không crash, không data loss.
- **Reproduction**:
  1. Start Market, không đặt lệnh nào cho ACB.
  2. OrderBookView → card ACB hiển thị 1 hàng trống không chữ.
- **Evidence**:

```jsx
// OrderBookView.jsx:6, 21, 33-37
const maxRows = Math.max(bids.length, asks.length, 1);
...
{Array.from({ length: Math.min(maxRows, 10) }, (_, i) => { ... })}
{maxRows === 0 && (    // unreachable
  <tr><td colSpan="4" className="empty">Empty book</td></tr>
)}
```

- **Suggested fix**: Đổi điều kiện thành `bids.length === 0 && asks.length === 0`, và sửa `maxRows = Math.max(bids.length, asks.length)` rồi `Array.from({length: Math.min(maxRows, 10)})` (length 0 render không row → message empty hoạt động).
- **Source**: ECH

---

## ECH-ADMIN-012

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/useAdminApi`
- **Location**: `matching-engine/exchange/admin/src/hooks/useAdminApi.js:8-23`
- **Description**: `await resp.json()` chạy trước khi check `resp.ok`. Nếu server trả 500 với body HTML (FastAPI default `Internal Server Error` HTML khi có exception chưa handle), `resp.json()` throw `SyntaxError: Unexpected token '<'` và error đó bubble lên. User không thấy `detail` của response mà thấy lỗi parse.
- **Root cause**: Thứ tự parse/check không bảo vệ trường hợp body non-JSON.
- **Impact**: Error message không giúp debug; có thể nhầm là client-side bug.
- **Reproduction**:
  1. Chèn `raise RuntimeError` vào `api.market_start` để mô phỏng.
  2. Admin bấm Start → console error "SyntaxError" thay vì "Internal Server Error".
- **Evidence**:

```jsx
// useAdminApi.js:12-19
const resp = await fetch(`${API_BASE}${path}`, { ... });
const data = await resp.json();             // throws on non-JSON body
if (!resp.ok) {
  throw new Error(data.detail || `HTTP ${resp.status}`);
}
```

- **Suggested fix**: `const text = await resp.text(); let data = null; try { data = JSON.parse(text); } catch {} if (!resp.ok) throw new Error(data?.detail ?? text ?? \`HTTP ${resp.status}\`);`.
- **Source**: ECH

---

## ECH-ADMIN-013

- [ ] Fixed
- **Severity**: P2 High
- **Module**: `admin/StockConfig`
- **Location**: `matching-engine/exchange/admin/src/components/StockConfig.jsx:69-70`
- **Description**: `if (!stocks) return null;` — guard khi `state?.stocks` undefined. Nhưng nếu `stocks = {}` (server trả object rỗng vì reset config), `!stocks` là false → render bảng rỗng không có row, cũng không có thông điệp "No stocks configured". UX mơ hồ.
- **Root cause**: Guard chỉ bắt undefined/null, không bắt empty object.
- **Impact**: User thấy bảng trống không hiểu tại sao.
- **Reproduction**: Giả lập server trả `stocks: {}` → Admin hiển thị header bảng mà không có row.
- **Evidence**:

```jsx
// StockConfig.jsx:69-72
export default function StockConfig({ stocks, onSave }) {
  if (!stocks) return null;
  const stockList = Object.entries(stocks);
```

- **Suggested fix**: `if (!stocks || Object.keys(stocks).length === 0) return <div className="card">No stocks configured</div>;`.
- **Source**: ECH

---

## ECH-ADMIN-014

- [ ] Fixed
- **Severity**: P3 Low
- **Module**: `admin/useAdminWebSocket`
- **Location**: `matching-engine/exchange/admin/src/hooks/useAdminWebSocket.js:4,38-45`
- **Description**: `RECONNECT_DELAY = 2000` cố định. Khi server down lâu, client vẫn spam mỗi 2s → log server/network ồn ào, tốn battery trên máy thật.
- **Root cause**: Không có exponential backoff / max attempts.
- **Impact**: Minor. Chỉ ảnh hưởng DevEx khi server chủ ý down.
- **Reproduction**: `./stopall.sh`, mở Admin → network tab spam WS handshake mỗi 2s.
- **Evidence**:

```jsx
// useAdminWebSocket.js:4, 42-44
const RECONNECT_DELAY = 2000;
...
reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
```

- **Suggested fix**: Exponential backoff `Math.min(30000, 1000 * 2 ** attempts)`, hoặc chấp nhận giữ nguyên và document là hackathon-only.
- **Source**: ECH

---

## ECH-ADMIN-015

- [ ] Fixed
- **Severity**: P3 Low
- **Module**: `admin/TradeHistory`
- **Location**: `matching-engine/exchange/admin/src/components/TradeHistory.jsx:12,13`
- **Description**: Header hiển thị `Trade History ({filtered.length})` — là số đã filter, không phải tổng trade. Người xem dễ hiểu nhầm "50 trades total" trong khi filtered theo `ACB` ra 50, còn tổng có thể 500.
- **Root cause**: Label không rõ nghĩa là "filtered count".
- **Impact**: UX mơ hồ, không mất dữ liệu.
- **Reproduction**: Gây 300 trade, filter `ACB` → header `Trade History (100)` nhưng thực có 300.
- **Evidence**:

```jsx
// TradeHistory.jsx:13
<h2>Trade History ({filtered.length})</h2>
```

- **Suggested fix**: `<h2>Trade History ({filtered.length}/{allTrades.length})</h2>` hoặc "Showing X of Y".
- **Source**: ECH

---

## ECH-ADMIN-016

- [ ] Fixed
- **Severity**: P3 Low
- **Module**: `admin/CommLogs`
- **Location**: `matching-engine/exchange/admin/src/components/CommLogs.jsx:13`
- **Description**: `messageTypes = [...new Set(allLogs.map((l) => l.message_type))]` được tính lại mỗi render (mỗi 0.5s tick vì parent truyền logs mới). Với maxlen 1000 chi phí không đáng kể, nhưng là lãng phí.
- **Root cause**: Không memoize.
- **Impact**: Micro-perf; không quan sát được.
- **Reproduction**: React Profiler sẽ thấy `CommLogs` render mỗi 500ms, allocate Set mới.
- **Evidence**:

```jsx
// CommLogs.jsx:13
const messageTypes = [...new Set(allLogs.map((l) => l.message_type))];
```

- **Suggested fix**: `const messageTypes = useMemo(() => [...new Set(allLogs.map(l => l.message_type))], [allLogs]);`.
- **Source**: ECH

---

## ECH-ADMIN-017

- [ ] Fixed
- **Severity**: P3 Low
- **Module**: `admin/TradeHistory`
- **Location**: `matching-engine/exchange/admin/src/components/TradeHistory.jsx:35-36`
- **Description**: `key={i}` cho trade row thay vì `t.trade_id` (mỗi trade có ID duy nhất kiểu `TRD-{symbol}-{n}`). Khi trades update mỗi tick, React reconciler reuse DOM theo index → có thể diff sai cell nếu item đầu thay đổi.
- **Root cause**: Không dùng stable identifier.
- **Impact**: Reconciliation không tối ưu, nhấp nháy nhẹ khi nhiều trade; không data corruption.
- **Reproduction**: Nhiều trade dồn dập vào list → React Profiler cho thấy commit time cao hơn mức cần.
- **Evidence**:

```jsx
// TradeHistory.jsx:35-36
{display.map((t, i) => (
  <tr key={i}>
```

- **Suggested fix**: `<tr key={t.trade_id}>`.
- **Source**: ECH

---

## Tag index

- **P0 (1)**: ECH-ADMIN-001
- **P1 (4)**: ECH-ADMIN-002, ECH-ADMIN-003, ECH-ADMIN-004, ECH-ADMIN-005
- **P2 (8)**: ECH-ADMIN-006, ECH-ADMIN-007, ECH-ADMIN-008, ECH-ADMIN-009, ECH-ADMIN-010, ECH-ADMIN-011, ECH-ADMIN-012, ECH-ADMIN-013
- **P3 (4)**: ECH-ADMIN-014, ECH-ADMIN-015, ECH-ADMIN-016, ECH-ADMIN-017
- **By module**:
  - `admin/StockConfig`: 001, 008, 013
  - `admin/CommLogs`: 002, 003, 010, 016
  - `admin/App`: 004
  - `admin/OrderBookView`: 005, 011
  - `admin/TradeHistory`: 009, 015, 017
  - `admin/useAdminWebSocket`: 006, 014
  - `admin/useAdminApi`: 007, 012
