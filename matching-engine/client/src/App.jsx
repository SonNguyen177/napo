import useWebSocket from "./hooks/useWebSocket";
import OrderEntry from "./components/OrderEntry";
import MarketData from "./components/MarketData";
import TradeView from "./components/TradeView";
import PriceChart from "./components/PriceChart";
import "./App.css";

function App() {
  const { connected, snapshots, orderBooks, trades, execReports, sendOrder } =
    useWebSocket();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Exchange Client</h1>
        <span className={`status ${connected ? "connected" : "disconnected"}`}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </header>
      <div className="app-layout">
        <aside className="left-panel">
          <OrderEntry
            sendOrder={sendOrder}
            execReports={execReports}
            snapshots={snapshots}
          />
        </aside>
        <main className="right-panel">
          <MarketData orderBooks={orderBooks} snapshots={snapshots} />
          <TradeView trades={trades} />
          <PriceChart trades={trades} />
        </main>
      </div>
    </div>
  );
}

export default App;
