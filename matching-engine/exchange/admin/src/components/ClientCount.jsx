export default function ClientCount({ count }) {
  return (
    <div className="card client-count">
      <h2>Connected Clients</h2>
      <div className="count-display">
        <span className="count-number">{count ?? 0}</span>
        <span className="count-label">clients</span>
      </div>
    </div>
  );
}
