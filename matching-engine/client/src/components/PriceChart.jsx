import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const SYMBOLS = ["ACB", "FPT", "VCK"];
const COLORS = { ACB: "#2196F3", FPT: "#4CAF50", VCK: "#FF9800" };

export default function PriceChart({ trades }) {
  const [selectedSymbol, setSelectedSymbol] = useState("ALL");

  const chartData = useMemo(() => {
    const filtered =
      selectedSymbol === "ALL"
        ? trades
        : trades.filter((t) => t.symbol === selectedSymbol);

    // Reverse so oldest first (trades are stored newest-first)
    return [...filtered]
      .reverse()
      .slice(-100)
      .map((t) => ({
        time: new Date(t.time * 1000).toLocaleTimeString(),
        price: t.price,
        symbol: t.symbol,
      }));
  }, [trades, selectedSymbol]);

  return (
    <div className="price-chart">
      <div className="chart-header">
        <h2>Price Chart</h2>
        <select
          value={selectedSymbol}
          onChange={(e) => setSelectedSymbol(e.target.value)}
        >
          <option value="ALL">All Symbols</option>
          {SYMBOLS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      {chartData.length === 0 ? (
        <div className="empty">No trade data yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid #444" }}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke={
                selectedSymbol === "ALL" ? "#8884d8" : COLORS[selectedSymbol]
              }
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
