import { useMemo } from "react";

const SYMBOLS = ["ACB", "FPT", "VCK"];

function OrderBookTable({ symbol, book, snapshot, highLow }) {
  const bids = book?.bids || [];
  const asks = book?.asks || [];
  const floor = snapshot?.floor;
  const ceiling = snapshot?.ceiling;
  const marketState = snapshot?.market_state || "CLOSED";

  // Show up to 8 levels each side
  const displayAsks = asks.slice(0, 8).reverse();
  const displayBids = bids.slice(0, 8);

  return (
    <div className="order-book-card">
      <div className="book-header">
        <h3>{symbol}</h3>
        <span className={`market-state ${marketState.toLowerCase()}`}>
          {marketState}
        </span>
      </div>
      {floor != null && (
        <div className="price-range">
          Floor: {floor.toLocaleString()} | Ceiling: {ceiling.toLocaleString()}
        </div>
      )}
      {highLow && (
        <div className="high-low">
          <span className="hl-high">H: {highLow.high.toLocaleString()}</span>
          <span className="hl-low">L: {highLow.low.toLocaleString()}</span>
          <span className="hl-last">Last: {highLow.last.toLocaleString()}</span>
        </div>
      )}
      <table className="book-table">
        <thead>
          <tr>
            <th>Qty</th>
            <th>Price</th>
            <th>Price</th>
            <th>Qty</th>
          </tr>
          <tr className="sub-header">
            <th colSpan="2">Bids</th>
            <th colSpan="2">Asks</th>
          </tr>
        </thead>
        <tbody>
          {(() => {
            const maxRows = Math.max(displayBids.length, displayAsks.length, 1);
            const rows = [];
            for (let i = 0; i < maxRows; i++) {
              const bid = displayBids[i];
              const ask = displayAsks.length > 0
                ? displayAsks[displayAsks.length - 1 - (maxRows - 1 - i)]
                : undefined;
              rows.push(
                <tr key={i}>
                  <td className="qty">{bid ? bid[1].toLocaleString() : ""}</td>
                  <td className="price buy">{bid ? bid[0].toLocaleString() : ""}</td>
                  <td className="price sell">{ask ? ask[0].toLocaleString() : ""}</td>
                  <td className="qty">{ask ? ask[1].toLocaleString() : ""}</td>
                </tr>
              );
            }
            return rows;
          })()}
        </tbody>
      </table>
    </div>
  );
}

export default function MarketData({ orderBooks, snapshots, trades }) {
  const highLowMap = useMemo(() => {
    const map = {};
    for (const sym of SYMBOLS) {
      const symTrades = (trades || []).filter((t) => t.symbol === sym);
      if (symTrades.length === 0) continue;
      let high = -Infinity;
      let low = Infinity;
      for (const t of symTrades) {
        if (t.price > high) high = t.price;
        if (t.price < low) low = t.price;
      }
      map[sym] = { high, low, last: symTrades[0].price };
    }
    return map;
  }, [trades]);

  return (
    <div className="market-data">
      <h2>Market Data</h2>
      <div className="book-grid">
        {SYMBOLS.map((symbol) => (
          <OrderBookTable
            key={symbol}
            symbol={symbol}
            book={orderBooks[symbol]}
            snapshot={snapshots[symbol]}
            highLow={highLowMap[symbol]}
          />
        ))}
      </div>
    </div>
  );
}
