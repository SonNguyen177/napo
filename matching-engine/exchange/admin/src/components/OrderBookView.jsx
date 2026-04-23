const SYMBOLS = ["ACB", "FPT", "VCK"];

function BookCard({ symbol, book }) {
  const bids = book?.bids || [];
  const asks = book?.asks || [];
  const maxRows = Math.max(bids.length, asks.length, 1);

  return (
    <div className="book-card">
      <h3>{symbol}</h3>
      <table className="book-table">
        <thead>
          <tr>
            <th>Bid Qty</th>
            <th>Bid Price</th>
            <th>Ask Price</th>
            <th>Ask Qty</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: Math.min(maxRows, 10) }, (_, i) => {
            const bid = bids[i];
            const ask = asks[i];
            return (
              <tr key={i}>
                <td className="qty">{bid ? bid[1].toLocaleString() : ""}</td>
                <td className="price buy">{bid ? bid[0].toLocaleString() : ""}</td>
                <td className="price sell">{ask ? ask[0].toLocaleString() : ""}</td>
                <td className="qty">{ask ? ask[1].toLocaleString() : ""}</td>
              </tr>
            );
          })}
          {maxRows === 0 && (
            <tr>
              <td colSpan="4" className="empty">Empty book</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function OrderBookView({ books }) {
  return (
    <div className="card order-book-view">
      <h2>Order Books</h2>
      <div className="books-grid">
        {SYMBOLS.map((symbol) => (
          <BookCard key={symbol} symbol={symbol} book={books?.[symbol]} />
        ))}
      </div>
    </div>
  );
}
