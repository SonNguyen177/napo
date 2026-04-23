import { useState, useCallback } from "react";

const API_BASE = "http://localhost:8000/api";

export default function useAdminApi() {
  const [loading, setLoading] = useState(false);

  const api = useCallback(async (path, options = {}) => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }
      return data;
    } finally {
      setLoading(false);
    }
  }, []);

  const startMarket = useCallback(() => api("/market/start", { method: "POST" }), [api]);
  const stopMarket = useCallback(() => api("/market/stop", { method: "POST" }), [api]);
  const getMarketState = useCallback(() => api("/market/state"), [api]);
  const getStocks = useCallback(() => api("/stocks"), [api]);
  const getStock = useCallback((symbol) => api(`/stocks/${symbol}`), [api]);
  const updateStock = useCallback(
    (symbol, data) => api(`/stocks/${symbol}`, { method: "PUT", body: JSON.stringify(data) }),
    [api]
  );
  const getOrderBook = useCallback((symbol) => api(`/orderbook/${symbol}`), [api]);
  const getTrades = useCallback((symbol) => api(`/trades${symbol ? `?symbol=${symbol}` : ""}`), [api]);
  const getLogs = useCallback((limit = 100) => api(`/logs?limit=${limit}`), [api]);
  const getClientCount = useCallback(() => api("/clients"), [api]);

  return {
    loading,
    startMarket,
    stopMarket,
    getMarketState,
    getStocks,
    getStock,
    updateStock,
    getOrderBook,
    getTrades,
    getLogs,
    getClientCount,
  };
}
