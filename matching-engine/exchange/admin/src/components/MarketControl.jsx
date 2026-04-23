export default function MarketControl({ marketState, onStart, onStop }) {
  const isOpen = marketState === "OPEN";

  return (
    <div className="card market-control">
      <h2>Market Control</h2>
      <div className="control-row">
        <span className={`state-badge ${isOpen ? "open" : "closed"}`}>
          {marketState || "UNKNOWN"}
        </span>
        <div className="control-buttons">
          <button
            className="btn btn-success"
            onClick={onStart}
            disabled={isOpen}
          >
            Start Market
          </button>
          <button
            className="btn btn-danger"
            onClick={onStop}
            disabled={!isOpen}
          >
            Stop Market
          </button>
        </div>
      </div>
    </div>
  );
}
