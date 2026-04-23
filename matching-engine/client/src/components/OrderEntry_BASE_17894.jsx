import { useState, useRef, useCallback, useEffect } from "react";

const SYMBOLS = ["ACB", "FPT", "VCK"];
const SIDES = ["BUY", "SELL"];
const ORD_TYPES = ["LIMIT", "MARKET"];

export default function OrderEntry({ sendOrder, execReports, snapshots }) {
  const [form, setForm] = useState({
    account: "",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "",
    quantity: "",
  });

  const [autoGen, setAutoGen] = useState(false);
  const [autoInterval, setAutoInterval] = useState(1000);
  const autoRef = useRef(null);
  const orderCounter = useRef(0);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.account || !form.quantity) return;
    if (form.ord_type === "LIMIT" && !form.price) return;

    orderCounter.current += 1;
    sendOrder({
      cl_ord_id: `${form.account}-${Date.now()}-${orderCounter.current}`,
      account: form.account,
      symbol: form.symbol,
      side: form.side,
      ord_type: form.ord_type,
      price: form.ord_type === "MARKET" ? 0 : parseInt(form.price),
      quantity: parseInt(form.quantity),
    });
  };

  const generateRandomOrder = useCallback(() => {
    const symbol = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
    const side = Math.random() > 0.5 ? "BUY" : "SELL";
    const snap = snapshots[symbol];
    if (!snap) return;

    const floor = snap.floor;
    const ceiling = snap.ceiling;
    const step = snap.price_step;
    const steps = Math.floor((ceiling - floor) / step);
    const price = floor + Math.floor(Math.random() * (steps + 1)) * step;

    const qtySteps = Math.floor(Math.random() * 5) + 1;
    const quantity = qtySteps * snap.qty_step;

    orderCounter.current += 1;
    sendOrder({
      cl_ord_id: `AUTO-${Date.now()}-${orderCounter.current}`,
      account: "AUTO",
      symbol,
      side,
      ord_type: "LIMIT",
      price,
      quantity,
    });
  }, [sendOrder, snapshots]);

  useEffect(() => {
    if (autoGen) {
      autoRef.current = setInterval(generateRandomOrder, autoInterval);
    } else {
      clearInterval(autoRef.current);
    }
    return () => clearInterval(autoRef.current);
  }, [autoGen, autoInterval, generateRandomOrder]);

  const recentReports = execReports.slice(0, 8);

  return (
    <div className="order-entry">
      <h2>Order Entry</h2>
      <form onSubmit={handleSubmit} className="order-form">
        <div className="form-row">
          <label>Account</label>
          <input
            name="account"
            value={form.account}
            onChange={handleChange}
            placeholder="Account name"
          />
        </div>
        <div className="form-row">
          <label>Symbol</label>
          <select name="symbol" value={form.symbol} onChange={handleChange}>
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Side</label>
          <select name="side" value={form.side} onChange={handleChange}>
            {SIDES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Type</label>
          <select name="ord_type" value={form.ord_type} onChange={handleChange}>
            {ORD_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        {form.ord_type === "LIMIT" && (
          <div className="form-row">
            <label>Price (VND)</label>
            <input
              name="price"
              type="number"
              value={form.price}
              onChange={handleChange}
              placeholder="e.g. 55000"
            />
          </div>
        )}
        <div className="form-row">
          <label>Quantity</label>
          <input
            name="quantity"
            type="number"
            value={form.quantity}
            onChange={handleChange}
            placeholder="e.g. 100"
          />
        </div>
        <button type="submit" className="btn btn-primary">Place Order</button>
      </form>

      <div className="auto-gen">
        <h3>Auto Order Generator</h3>
        <div className="form-row">
          <label>Interval (ms)</label>
          <input
            type="number"
            value={autoInterval}
            onChange={(e) => setAutoInterval(Math.max(100, parseInt(e.target.value) || 1000))}
            min="100"
          />
        </div>
        <button
          className={`btn ${autoGen ? "btn-danger" : "btn-success"}`}
          onClick={() => setAutoGen(!autoGen)}
        >
          {autoGen ? "Stop Auto" : "Start Auto"}
        </button>
      </div>

      <div className="exec-reports">
        <h3>Execution Reports</h3>
        <table>
          <thead>
            <tr>
              <th>ClOrdID</th>
              <th>Symbol</th>
              <th>Side</th>
              <th>Status</th>
              <th>Filled</th>
              <th>Price</th>
            </tr>
          </thead>
          <tbody>
            {recentReports.map((er, i) => (
              <tr key={i} className={`er-${er.exec_type.toLowerCase()}`}>
                <td title={er.cl_ord_id}>{er.cl_ord_id.slice(-12)}</td>
                <td>{er.symbol}</td>
                <td className={er.side === "BUY" ? "buy" : "sell"}>{er.side}</td>
                <td>{er.exec_type}</td>
                <td>{er.cum_qty}/{er.quantity}</td>
                <td>{er.last_px > 0 ? er.last_px.toLocaleString() : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
