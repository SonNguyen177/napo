export default function TradeView({ trades }) {
  const recent = trades.slice(0, 20);

  return (
    <div className="trade-view">
      <h2>Recent Trades</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Symbol</th>
            <th>Price</th>
            <th>Qty</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((t, i) => (
            <tr key={i}>
              <td>{new Date(t.time * 1000).toLocaleTimeString()}</td>
              <td>{t.symbol}</td>
              <td className="price">{t.price.toLocaleString()}</td>
              <td>{t.quantity.toLocaleString()}</td>
            </tr>
          ))}
          {recent.length === 0 && (
            <tr>
              <td colSpan="4" className="empty">No trades yet</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
