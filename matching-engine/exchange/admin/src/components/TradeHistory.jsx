import { useState } from "react";

export default function TradeHistory({ trades }) {
  const [filter, setFilter] = useState("ALL");
  const allTrades = trades || [];
  const filtered =
    filter === "ALL" ? allTrades : allTrades.filter((t) => t.symbol === filter);
  const display = filtered.slice(-50).reverse();

  return (
    <div className="card trade-history">
      <div className="card-header">
        <h2>Trade History ({filtered.length})</h2>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="ALL">All</option>
          <option value="ACB">ACB</option>
          <option value="FPT">FPT</option>
          <option value="VCK">VCK</option>
        </select>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Time</th>
              <th>Symbol</th>
              <th>Price</th>
              <th>Qty</th>
              <th>Buy Order</th>
              <th>Sell Order</th>
            </tr>
          </thead>
          <tbody>
            {display.map((t, i) => (
              <tr key={i}>
                <td>{t.trade_id}</td>
                <td>{new Date(t.time * 1000).toLocaleTimeString()}</td>
                <td>{t.symbol}</td>
                <td className="price">{t.price.toLocaleString()}</td>
                <td>{t.quantity.toLocaleString()}</td>
                <td title={t.buy_order_id}>{t.buy_order_id.slice(-10)}</td>
                <td title={t.sell_order_id}>{t.sell_order_id.slice(-10)}</td>
              </tr>
            ))}
            {display.length === 0 && (
              <tr>
                <td colSpan="7" className="empty">No trades</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
