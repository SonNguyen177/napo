import { useState } from "react";

const FIELDS = [
  { key: "floor", label: "Floor" },
  { key: "ceiling", label: "Ceiling" },
  { key: "price_step", label: "Price Step" },
  { key: "qty_step", label: "Qty Step" },
];

function StockRow({ symbol, config, onSave }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [error, setError] = useState("");

  const startEdit = () => {
    setForm({
      floor: config.floor,
      ceiling: config.ceiling,
      price_step: config.price_step,
      qty_step: config.qty_step,
    });
    setEditing(true);
    setError("");
  };

  const handleSave = async () => {
    try {
      await onSave(symbol, form);
      setEditing(false);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <tr>
      <td className="symbol">{symbol}</td>
      {FIELDS.map(({ key }) => (
        <td key={key}>
          {editing ? (
            <input
              type="number"
              value={form[key]}
              onChange={(e) =>
                setForm({ ...form, [key]: parseInt(e.target.value) || 0 })
              }
            />
          ) : (
            config[key]?.toLocaleString()
          )}
        </td>
      ))}
      <td>
        {editing ? (
          <div className="edit-actions">
            <button className="btn-sm btn-success" onClick={handleSave}>Save</button>
            <button className="btn-sm btn-muted" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        ) : (
          <button className="btn-sm btn-primary" onClick={startEdit}>Edit</button>
        )}
        {error && <div className="error-text">{error}</div>}
      </td>
    </tr>
  );
}

export default function StockConfig({ stocks, onSave }) {
  if (!stocks) return null;

  const stockList = Object.entries(stocks);

  return (
    <div className="card stock-config">
      <h2>Stock Configuration</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            {FIELDS.map(({ key, label }) => (
              <th key={key}>{label}</th>
            ))}
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {stockList.map(([symbol, config]) => (
            <StockRow
              key={symbol}
              symbol={symbol}
              config={config}
              onSave={onSave}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
