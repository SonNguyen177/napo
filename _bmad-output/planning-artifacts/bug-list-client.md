# Bug List — Module `client` (Exchange Client UI)

Module path: `matching-engine/client`
Review method: Edge Case Hunter (path enumeration, unhandled boundaries only)
Source tag: `ECH`

---

## ECH-CLIENT-001

- **ID**: ECH-CLIENT-001
- **Fixed**: [x]
- **Fix-summary**: Extract guard logic sang `src/lib/validateOrderForm.js`; thay falsy-check `!form.quantity` bằng `parseInt` + `Number.isFinite(qty) && qty > 0`. Chuỗi `"0"` giờ bị reject tại client trước khi gửi server. Unit test `test/unit/validateOrderForm.test.mjs` cover 6 case (qty="0", empty account, empty qty, empty price LIMIT, MARKET empty price ok, happy path).
- **Severity**: P0 Blocker
- **Module**: `client / OrderEntry`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:26-41`
- **Description**: Form submit chỉ check `!form.quantity` (falsy string). Chuỗi `"0"` là truthy → pass guard → `parseInt("0") = 0` được gửi lên server.
- **Root cause**: Falsy-check trên chuỗi không bắt được `"0"`; thiếu validation numeric `> 0` phía client.
- **Impact**: Server `MatchingEngine.submit_order` có check `qty <= 0 → os._exit(1)`. Một order từ UI có thể kill toàn bộ engine, mất sạch state RAM (order books, trades, configs). Bất kỳ user nào cũng trigger được.
- **Reproduction**:
  1. Mở Client UI, đợi `Connected`.
  2. Nhập Account="x", Symbol=FPT, Type=LIMIT, Price=55000, Quantity=`0`.
  3. Click Place Order.
  4. Quan sát process engine bị exit (PID trong `.run/` chết).
- **Evidence**:
  ```jsx
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.account || !form.quantity) return;           // "0" truthy → pass
    if (form.ord_type === "LIMIT" && !form.price) return;
    ...
    sendOrder({
      ...
      price: form.ord_type === "MARKET" ? 0 : parseInt(form.price),
      quantity: parseInt(form.quantity),                   // = 0 → server os._exit(1)
    });
  };
  ```
- **Suggested fix**: Parse trước khi guard: `const qty = parseInt(form.quantity, 10); if (!Number.isFinite(qty) || qty <= 0) return;` (áp dụng tương tự cho price khi LIMIT).
- **Source**: ECH

---

## ECH-CLIENT-002

- **ID**: ECH-CLIENT-002
- **Fixed**: [ ]
- **Severity**: P0 Blocker
- **Module**: `client / OrderEntry`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:26-41`
- **Description**: Input `type="number"` cho phép giá trị âm. `parseInt("-100") = -100`; guard `!form.quantity` cho chuỗi `"-100"` qua (truthy).
- **Root cause**: Không validate dấu; `<input min>` chỉ set `min="100"` cho autoInterval, không có min cho quantity/price.
- **Impact**: Gửi `qty = -100` → server `submit_order` thấy `qty <= 0` → `os._exit(1)` → engine chết, mất toàn bộ state.
- **Reproduction**:
  1. Nhập Quantity=`-100`, Type=LIMIT, Price=55000, Account="x".
  2. Place Order.
  3. Engine process exit.
- **Evidence**:
  ```jsx
  <input name="quantity" type="number" value={form.quantity} onChange={handleChange} />
  // không có min; parseInt("-100") = -100 được gửi thẳng
  ```
- **Suggested fix**: Ngoài check `qty > 0` như ECH-CLIENT-001, thêm `min="1"` và `step` vào input để browser block giá trị âm/thập phân.
- **Source**: ECH

---

## ECH-CLIENT-003

- **ID**: ECH-CLIENT-003
- **Fixed**: [ ]
- **Severity**: P0 Blocker
- **Module**: `client / OrderEntry`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:29,38`
- **Description**: LIMIT order cho phép price âm. `parseInt("-1") = -1`; guard `!form.price` cho `"-1"` qua (truthy). Server kill vì `price < 0`.
- **Root cause**: Thiếu numeric range validation cho price.
- **Impact**: `MatchingEngine.submit_order` envelope-check: `price < 0 → os._exit(1)`. Kill engine.
- **Reproduction**:
  1. Type=LIMIT, Price=`-1`, Quantity=100, Account="x".
  2. Submit.
  3. Engine exit.
- **Evidence**:
  ```jsx
  if (form.ord_type === "LIMIT" && !form.price) return;   // "-1" truthy → pass
  sendOrder({ ..., price: parseInt(form.price), ... });   // = -1 → os._exit(1)
  ```
- **Suggested fix**: `const price = parseInt(form.price, 10); if (form.ord_type === "LIMIT" && (!Number.isFinite(price) || price <= 0)) return;`
- **Source**: ECH

---

## ECH-CLIENT-004

- **ID**: ECH-CLIENT-004
- **Fixed**: [ ]
- **Severity**: P0 Blocker
- **Module**: `client / OrderEntry (auto-gen)`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:43-68`
- **Description**: `generateRandomOrder` dùng `snap.qty_step` và `snap.price_step` trực tiếp; nếu admin (hoặc seed) cho `qty_step = 0`, `quantity = qtySteps * 0 = 0` được gửi lên server.
- **Root cause**: Không guard step=0 trước khi tính qty/price ngẫu nhiên.
- **Impact**: Auto-generator gửi qty=0 → `submit_order` → `os._exit(1)` → engine chết. Auto-gen fire liên tục nên nếu một client bật Auto với symbol xấu, engine chết ngay lần call đầu.
- **Reproduction**:
  1. Qua Admin UI set `qty_step=0` cho FPT (nếu Pydantic cho phép) hoặc giả lập snapshot qty_step=0.
  2. Client bật Start Auto.
  3. Tick đầu tiên kill engine.
- **Evidence**:
  ```jsx
  const qtySteps = Math.floor(Math.random() * 5) + 1;
  const quantity = qtySteps * snap.qty_step;    // 0 nếu qty_step=0
  sendOrder({ ..., quantity });                  // os._exit(1)
  ```
- **Suggested fix**: `if (!snap || !snap.qty_step || !snap.price_step || snap.ceiling <= snap.floor) return;` ở đầu hàm.
- **Source**: ECH

---

## ECH-CLIENT-005

- **ID**: ECH-CLIENT-005
- **Fixed**: [ ]
- **Severity**: P1 Critical
- **Module**: `client / useWebSocket`
- **Location**: `matching-engine/client/src/hooks/useWebSocket.js:128-132`
- **Description**: `sendOrder` drop im lặng khi `readyState !== OPEN`. User click Place Order nhưng không có feedback; order biến mất.
- **Root cause**: Chỉ check-and-send, không trả về status, không push local exec report "REJECTED — disconnected".
- **Impact**: Golden path (đặt order) fail im lặng khi socket CONNECTING/CLOSED → user hiểu nhầm order đã đặt thành công, có thể double-submit khi reconnect.
- **Reproduction**:
  1. Tắt engine (`./stopall.sh`).
  2. UI chuyển sang Disconnected.
  3. Điền form hợp lệ, click Place Order.
  4. Không có error, không có exec report, như chưa làm gì.
- **Evidence**:
  ```js
  const sendOrder = useCallback((order) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "new_order", ...order }));
    }
    // else: silent drop
  }, []);
  ```
- **Suggested fix**: Return boolean và hiển thị toast/inline error ở `handleSubmit`; hoặc đẩy giả exec report `REJECTED / Disconnected` vào state để bảng Execution Reports hiện.
- **Source**: ECH

---

## ECH-CLIENT-006

- **ID**: ECH-CLIENT-006
- **Fixed**: [ ]
- **Severity**: P1 Critical
- **Module**: `client / useWebSocket`
- **Location**: `matching-engine/client/src/hooks/useWebSocket.js:51-107`
- **Description**: `JSON.parse(event.data)` không được bọc try/catch. Nếu server (hoặc proxy) gửi frame không phải JSON hợp lệ, handler throw uncaught → mất luôn các nhánh case phía dưới.
- **Root cause**: Thiếu defensive parsing.
- **Impact**: Một frame lỗi có thể làm crash handler của frame đó; nếu server gửi batch ngay sau, chỉ có frame lỗi bị drop nhưng error bubble lên window có thể che các lỗi khác. Với binary frame (trong tương lai) sẽ throw ngay.
- **Reproduction**:
  1. Giả lập server gửi `"not-json"` qua WS (thêm test hook).
  2. Handler throw `SyntaxError` → console.
- **Evidence**:
  ```js
  ws.onmessage = (event) => {
    if (cancelled) return;
    const msg = JSON.parse(event.data);  // no try/catch
    switch (msg.type) { ... }
  };
  ```
- **Suggested fix**: `let msg; try { msg = JSON.parse(event.data); } catch { console.error("bad frame", event.data); return; }`.
- **Source**: ECH

---

## ECH-CLIENT-007

- **ID**: ECH-CLIENT-007
- **Fixed**: [ ]
- **Severity**: P1 Critical
- **Module**: `client / OrderEntry (auto-gen)`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:70-77`
- **Description**: Auto-generator không dừng khi socket disconnect hoặc market `CLOSED`. Interval vẫn firing, `sendOrder` drop im lặng (xem ECH-CLIENT-005) hoặc server reply reject.
- **Root cause**: Effect chỉ phụ thuộc `autoGen, autoInterval, generateRandomOrder`; không consume `connected` hay `market_state`.
- **Impact**: User thấy "Stop Auto" → nghĩ auto đang chạy, thực tế đang bắn order rỗng; server reject spam `_comm_logs` (deque 1000 quay vòng nhanh, khó debug các event quan trọng khác).
- **Reproduction**:
  1. Start Auto trong lúc Connected + market OPEN.
  2. `./stopall.sh` engine.
  3. UI vẫn hiển thị auto đang chạy, nhưng không có exec report mới.
- **Evidence**:
  ```jsx
  useEffect(() => {
    if (autoGen) autoRef.current = setInterval(generateRandomOrder, autoInterval);
    else clearInterval(autoRef.current);
    return () => clearInterval(autoRef.current);
  }, [autoGen, autoInterval, generateRandomOrder]);
  // không theo dõi connected / market_state
  ```
- **Suggested fix**: Truyền `connected` + `snapshots` vào `OrderEntry`; trong interval callback check `connected && snap?.market_state === "OPEN"` trước khi generate.
- **Source**: ECH

---

## ECH-CLIENT-008

- **ID**: ECH-CLIENT-008
- **Fixed**: [ ]
- **Severity**: P1 Critical
- **Module**: `client / MarketData`
- **Location**: `matching-engine/client/src/components/MarketData.jsx:22-26`
- **Description**: Guard `floor != null` chỉ kiểm tra `floor`, nhưng block render gọi `ceiling.toLocaleString()`. Nếu snapshot có `floor` nhưng `ceiling` null/undef → TypeError.
- **Root cause**: Kiểm tra điều kiện 1 biến nhưng dùng 2 biến.
- **Impact**: Lỗi render → toàn panel MarketData crash (nếu không có ErrorBoundary, cả app trắng). Snapshot server hiện set cả hai, nhưng không có defensive layer.
- **Reproduction**:
  1. Inject snapshot `{ floor: 40000, ceiling: null, ... }` (test hoặc server bug).
  2. Component throw `Cannot read properties of null (reading 'toLocaleString')`.
- **Evidence**:
  ```jsx
  {floor != null && (
    <div className="price-range">
      Floor: {floor.toLocaleString()} | Ceiling: {ceiling.toLocaleString()}
    </div>
  )}
  ```
- **Suggested fix**: `{floor != null && ceiling != null && ...}` hoặc `{ceiling?.toLocaleString() ?? "-"}`.
- **Source**: ECH

---

## ECH-CLIENT-009

- **ID**: ECH-CLIENT-009
- **Fixed**: [ ]
- **Severity**: P1 Critical
- **Module**: `client / OrderEntry (exec reports table)`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:177-178`
- **Description**: `er.exec_type.toLowerCase()` và `er.cl_ord_id.slice(-12)` throw nếu field undefined. Không defensive với payload từ server.
- **Root cause**: Truy cập method trực tiếp trên field không guard.
- **Impact**: Một exec report thiếu `exec_type` hoặc `cl_ord_id` sẽ crash render toàn bảng → Order Entry panel chết.
- **Reproduction**:
  1. Inject fake exec report `{ symbol: "FPT", side: "BUY" }` (thiếu exec_type).
  2. React throw trong render.
- **Evidence**:
  ```jsx
  <tr key={i} className={`er-${er.exec_type.toLowerCase()}`}>
    <td title={er.cl_ord_id}>{er.cl_ord_id.slice(-12)}</td>
  ```
- **Suggested fix**: `er.exec_type?.toLowerCase() ?? "unknown"`, `er.cl_ord_id?.slice(-12) ?? "-"`.
- **Source**: ECH

---

## ECH-CLIENT-010

- **ID**: ECH-CLIENT-010
- **Fixed**: [ ]
- **Severity**: P2 High
- **Module**: `client / useWebSocket`
- **Location**: `matching-engine/client/src/hooks/useWebSocket.js:64-90`
- **Description**: `market_update` không validate `msg.symbol`, `msg.price`, `msg.quantity`, `msg.side`. Nếu `msg.symbol` undef → key `"undefined"` vào state; nếu `msg.side` không phải "BUY"/"SELL" thì fallback về "asks" (silent mis-bucket).
- **Root cause**: Thiếu shape validation.
- **Impact**: State pollution; bug hiển thị khó trace. Nếu server gửi price là string `"55000"`, `findIndex(([p]) => p === msg.price)` luôn false → push level trùng mãi (memory bloat).
- **Reproduction**:
  1. Server gửi `{type:"market_update", symbol:"fpt", side:"UNKNOWN", price:"55000", quantity:100}`.
  2. State chứa `orderBooks["fpt"].asks = [["55000",100], ["55000",100], ...]`.
- **Evidence**:
  ```js
  const side = msg.side === "BUY" ? "bids" : "asks";    // unknown → asks
  const idx = levels.findIndex(([p]) => p === msg.price); // string vs number mismatch
  ```
- **Suggested fix**: Validate + coerce: `if (typeof msg.symbol !== "string") return prev; const price = Number(msg.price); const qty = Number(msg.quantity); if (!["BUY","SELL"].includes(msg.side)) return prev;`.
- **Source**: ECH

---

## ECH-CLIENT-011

- **ID**: ECH-CLIENT-011
- **Fixed**: [ ]
- **Severity**: P2 High
- **Module**: `client / OrderEntry`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:38-40`
- **Description**: `parseInt("100.5") = 100` và `parseInt("1e2") = 1`. User nhập thập phân/khoa học thấy form submit thành công nhưng order thật không khớp giá trị nhập.
- **Root cause**: Dùng `parseInt` thay vì parse + validate integer.
- **Impact**: Wrong-amount order được gửi. Nếu vi phạm `price_step`/`qty_step` server sẽ reject với exec report; user khó hiểu vì sao.
- **Reproduction**:
  1. Quantity=`100.5`, submit.
  2. Exec report hiển thị `quantity=100` thay vì 100.5.
- **Evidence**:
  ```jsx
  quantity: parseInt(form.quantity),
  price: form.ord_type === "MARKET" ? 0 : parseInt(form.price),
  ```
- **Suggested fix**: `const n = Number(form.quantity); if (!Number.isInteger(n)) return;` hoặc thêm `step="1"` cho input + `pattern`.
- **Source**: ECH

---

## ECH-CLIENT-012

- **ID**: ECH-CLIENT-012
- **Fixed**: [ ]
- **Severity**: P2 High
- **Module**: `client / useWebSocket`
- **Location**: `matching-engine/client/src/hooks/useWebSocket.js:115-124`
- **Description**: Cleanup chỉ `ws.close()` khi `readyState === OPEN`. Nếu unmount xảy ra trong lúc socket đang `CONNECTING`, socket không được close → browser để nó mở, sau đó onopen/onmessage đã bị null ra, không reconnect path → orphan socket.
- **Root cause**: Missing `CONNECTING` branch.
- **Impact**: Rò socket qua Fast Refresh / StrictMode double-mount; tăng connection count ở engine (`/api/clients`), gây nhiễu test/log.
- **Reproduction**:
  1. Bật DevTools → slow 3G throttling.
  2. Mở/đóng tab nhanh khi WS chưa lên.
  3. Quan sát `/api/clients` trên admin cho thấy connection vẫn tồn tại tạm thời.
- **Evidence**:
  ```js
  if (wsRef.current.readyState === WebSocket.OPEN) {
    wsRef.current.close();
  }
  ```
- **Suggested fix**: `if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) wsRef.current.close();`.
- **Source**: ECH

---

## ECH-CLIENT-013

- **ID**: ECH-CLIENT-013
- **Fixed**: [ ]
- **Severity**: P2 High
- **Module**: `client / OrderEntry (auto-gen)`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:52-53`
- **Description**: `steps = Math.floor((ceiling - floor) / step)`. Nếu `step = 0` → `Infinity` → `price = floor + Math.floor(Math.random()*(Infinity+1))*step = NaN`. Nếu `ceiling < floor` (admin cho phép theo CLAUDE.md invariant), `steps` âm → price lệch miền.
- **Root cause**: Không guard mẫu số và range.
- **Impact**: Gửi `price: NaN` → JSON.stringify → `"price":null` → server Pydantic reject. Nếu `ceiling <= floor`, server submit_order envelope check giết engine (`ceiling <= floor → os._exit(1)`).
- **Reproduction**:
  1. Admin set ceiling=40000, floor=50000 cho FPT (CLAUDE.md xác nhận chấp nhận).
  2. Client Start Auto.
  3. Order đầu tiên tới server → os._exit.
- **Evidence**:
  ```jsx
  const steps = Math.floor((ceiling - floor) / step);
  const price = floor + Math.floor(Math.random() * (steps + 1)) * step;
  ```
- **Suggested fix**: Combined với ECH-CLIENT-004: `if (!snap || !step || step<=0 || ceiling<=floor || !snap.qty_step) return;`.
- **Source**: ECH

---

## ECH-CLIENT-014

- **ID**: ECH-CLIENT-014
- **Fixed**: [ ]
- **Severity**: P2 High
- **Module**: `client / OrderEntry`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:22-24`
- **Description**: `handleChange` ghi thẳng vào `form.symbol`/`form.side`/`form.ord_type` từ `e.target.value`. Với `<select>` hardcoded hợp lệ, nhưng không có validation — nếu ai đó mở DevTools sửa option value, form submit value ngoài enum server.
- **Root cause**: Trust-on-DOM; thiếu whitelist.
- **Impact**: Lower severity vì DevTools tampering là self-inflicted, nhưng nếu thêm custom symbol cho hackathon (seed file thay đổi), user có thể gửi symbol không tồn tại → server trả "Unknown symbol" reject; không crash nhưng flow sai.
- **Reproduction**:
  1. DevTools → edit `<option value="ACB">` thành `"xxx"`.
  2. Select → submit → server reject.
- **Evidence**:
  ```jsx
  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };
  ```
- **Suggested fix**: Whitelist khi set: `if (name === "symbol" && !SYMBOLS.includes(value)) return;`.
- **Source**: ECH

---

## ECH-CLIENT-015

- **ID**: ECH-CLIENT-015
- **Fixed**: [ ]
- **Severity**: P2 High
- **Module**: `client / TradeView`
- **Location**: `matching-engine/client/src/components/TradeView.jsx:19-22`
- **Description**: `new Date(t.time * 1000).toLocaleTimeString()` giả định `t.time` là number (epoch seconds). Nếu undef → `NaN` → "Invalid Date". `t.price.toLocaleString()` và `t.quantity.toLocaleString()` throw nếu field undef.
- **Root cause**: Không defensive với shape trade message.
- **Impact**: Một trade thiếu field → crash toàn TradeView. Giờ server luôn set đủ, nhưng brittle với thay đổi schema.
- **Reproduction**: Inject `{symbol:"FPT"}` vào state trades.
- **Evidence**:
  ```jsx
  <td>{new Date(t.time * 1000).toLocaleTimeString()}</td>
  <td className="price">{t.price.toLocaleString()}</td>
  <td>{t.quantity.toLocaleString()}</td>
  ```
- **Suggested fix**: Optional chaining + fallback: `{t.price?.toLocaleString?.() ?? "-"}`.
- **Source**: ECH

---

## ECH-CLIENT-016

- **ID**: ECH-CLIENT-016
- **Fixed**: [ ]
- **Severity**: P3 Low
- **Module**: `client / TradeView`
- **Location**: `matching-engine/client/src/components/TradeView.jsx:17-18`
- **Description**: `key={i}` với danh sách prepend (trades newest-first). Mỗi trade mới đẩy tất cả index → React remount mọi row thay vì chỉ insert.
- **Root cause**: Dùng array index làm key.
- **Impact**: Cosmetic/perf — row transition nhấp nháy; không sai dữ liệu.
- **Reproduction**: Bật Auto, quan sát React DevTools Highlight Updates → toàn bảng nháy mỗi tick.
- **Evidence**:
  ```jsx
  {recent.map((t, i) => (
    <tr key={i}>...
  ```
- **Suggested fix**: Nếu trade có `trade_id` dùng làm key; fallback `key={\`${t.time}-${t.symbol}-${t.price}-${t.quantity}\`}`.
- **Source**: ECH

---

## ECH-CLIENT-017

- **ID**: ECH-CLIENT-017
- **Fixed**: [ ]
- **Severity**: P3 Low
- **Module**: `client / OrderEntry`
- **Location**: `matching-engine/client/src/components/OrderEntry.jsx:28,33`
- **Description**: Guard `!form.account` không trim. Chuỗi `" "` (chỉ whitespace) là truthy → pass → `cl_ord_id = " -1712...-1"`.
- **Root cause**: Thiếu `.trim()`.
- **Impact**: Cosmetic/debug — ID lạ, audit log khó đọc. Không ảnh hưởng matching.
- **Reproduction**: Account=` ` (space), Quantity=100, submit.
- **Evidence**:
  ```jsx
  if (!form.account || !form.quantity) return;
  ...
  cl_ord_id: `${form.account}-${Date.now()}-${orderCounter.current}`,
  ```
- **Suggested fix**: `if (!form.account.trim() || ...) return;` và `cl_ord_id` dùng `form.account.trim()`.
- **Source**: ECH

---

## Tag index

- P0: ECH-CLIENT-001, ECH-CLIENT-002, ECH-CLIENT-003, ECH-CLIENT-004
- P1: ECH-CLIENT-005, ECH-CLIENT-006, ECH-CLIENT-007, ECH-CLIENT-008, ECH-CLIENT-009
- P2: ECH-CLIENT-010, ECH-CLIENT-011, ECH-CLIENT-012, ECH-CLIENT-013, ECH-CLIENT-014, ECH-CLIENT-015
- P3: ECH-CLIENT-016, ECH-CLIENT-017
