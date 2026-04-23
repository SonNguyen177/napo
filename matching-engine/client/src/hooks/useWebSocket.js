import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = "ws://localhost:8765";
const RECONNECT_DELAY = 2000;

export default function useWebSocket() {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [snapshots, setSnapshots] = useState({});
  const [orderBooks, setOrderBooks] = useState({});
  const [trades, setTrades] = useState([]);
  const [execReports, setExecReports] = useState([]);
  const reconnectTimer = useRef(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;

      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        if (wsRef.current.readyState === WebSocket.OPEN ||
            wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close();
        }
        wsRef.current = null;
      }

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!cancelled) setConnected(true);
      };

      ws.onclose = () => {
        if (!cancelled) {
          setConnected(false);
          wsRef.current = null;
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
        }
      };

      ws.onerror = () => {};

      ws.onmessage = (event) => {
        if (cancelled) return;
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case "market_snapshot":
            setSnapshots((prev) => ({ ...prev, [msg.symbol]: msg }));
            setOrderBooks((prev) => ({
              ...prev,
              [msg.symbol]: { bids: msg.bids, asks: msg.asks },
            }));
            break;

          case "market_update":
            setOrderBooks((prev) => {
              const book = prev[msg.symbol] || { bids: [], asks: [] };
              const side = msg.side === "BUY" ? "bids" : "asks";
              let levels = [...book[side]];

              const idx = levels.findIndex(([p]) => p === msg.price);
              if (msg.quantity === 0) {
                if (idx >= 0) levels.splice(idx, 1);
              } else if (idx >= 0) {
                levels[idx] = [msg.price, msg.quantity];
              } else {
                levels.push([msg.price, msg.quantity]);
              }

              if (side === "bids") {
                levels.sort((a, b) => b[0] - a[0]);
              } else {
                levels.sort((a, b) => a[0] - b[0]);
              }

              return {
                ...prev,
                [msg.symbol]: { ...book, [side]: levels },
              };
            });
            break;

          case "trade":
            setTrades((prev) => [msg, ...prev].slice(0, 200));
            break;

          case "execution_report":
            setExecReports((prev) => [msg, ...prev].slice(0, 100));
            break;

          case "error":
            console.error("Server error:", msg.message);
            break;

          default:
            break;
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        }
        wsRef.current = null;
      }
    };
  }, []);

  const sendOrder = useCallback((order) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "new_order", ...order }));
    }
  }, []);

  return {
    connected,
    snapshots,
    orderBooks,
    trades,
    execReports,
    sendOrder,
  };
}
