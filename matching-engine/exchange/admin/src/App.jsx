import { useState } from "react";
import useAdminApi from "./hooks/useAdminApi";
import useAdminWebSocket from "./hooks/useAdminWebSocket";
import { runMarketAction } from "./lib/marketControlActions";
import MarketControl from "./components/MarketControl";
import StockConfig from "./components/StockConfig";
import OrderBookView from "./components/OrderBookView";
import TradeHistory from "./components/TradeHistory";
import CommLogs from "./components/CommLogs";
import ClientCount from "./components/ClientCount";
import "./App.css";

function App() {
  const { connected, state } = useAdminWebSocket();
  const api = useAdminApi();
  const [errorMsg, setErrorMsg] = useState("");

  const handleStart = async () => {
    const result = await runMarketAction(() => api.startMarket());
    setErrorMsg(result.ok ? "" : result.error);
  };

  const handleStop = async () => {
    const result = await runMarketAction(() => api.stopMarket());
    setErrorMsg(result.ok ? "" : result.error);
  };

  const handleSaveStock = async (symbol, data) => {
    await api.updateStock(symbol, data);
  };

  return (
    <div className="admin-app">
      <header className="admin-header">
        <h1>Exchange Admin</h1>
        <span className={`status ${connected ? "connected" : "disconnected"}`}>
          {connected ? "Live" : "Disconnected"}
        </span>
      </header>

      <div className="admin-layout">
        {errorMsg && (
          <div className="error-text" role="alert">
            {errorMsg}
          </div>
        )}

        <div className="top-row">
          <MarketControl
            marketState={state?.market_state}
            onStart={handleStart}
            onStop={handleStop}
          />
          <ClientCount count={state?.client_count} />
        </div>

        <StockConfig stocks={state?.stocks} onSave={handleSaveStock} />

        <OrderBookView books={state?.books} stocks={state?.stocks} />

        <div className="bottom-row">
          <TradeHistory trades={state?.trades} />
          <CommLogs logs={state?.logs} />
        </div>
      </div>
    </div>
  );
}

export default App;
