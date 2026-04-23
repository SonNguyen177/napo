"""WebSocket server for order entry and market data broadcast."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field

import websockets
from websockets.asyncio.server import Server, ServerConnection

from engine.config import ExchangeConfig
from engine.fix_codec import (
    encode_execution_report,
    encode_new_order_single,
    fix_to_human,
)
from engine.matching import MatchingEngine
from engine.models import ExecType, OrdType, Order, Side


@dataclass
class CommLog:
    """A communication log entry."""
    timestamp: float
    direction: str  # "IN" or "OUT"
    client_id: str
    message_type: str
    summary: str
    fix_raw: str = ""  # human-readable FIX representation


class ExchangeWSServer:
    """WebSocket server handling order entry and market data broadcast."""

    def __init__(
        self,
        engine: MatchingEngine | None = None,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_logs: int = 1000,
    ) -> None:
        self.engine = engine or MatchingEngine()
        self.host = host
        self.port = port
        self._clients: dict[ServerConnection, str] = {}  # ws -> client_id
        self._client_counter = 0
        self._comm_logs: deque[CommLog] = deque(maxlen=max_logs)
        self._server: Server | None = None

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def comm_logs(self) -> list[CommLog]:
        return list(self._comm_logs)

    def _next_client_id(self) -> str:
        self._client_counter += 1
        return f"CLIENT-{self._client_counter}"

    def _log(self, direction: str, client_id: str, msg_type: str, summary: str, fix_raw: str = "") -> None:
        entry = CommLog(
            timestamp=time.time(),
            direction=direction,
            client_id=client_id,
            message_type=msg_type,
            summary=summary,
            fix_raw=fix_raw,
        )
        self._comm_logs.append(entry)

    async def _send_json(self, ws: ServerConnection, data: dict) -> None:
        """Send JSON message to a single client."""
        await ws.send(json.dumps(data))

    async def _broadcast_json(self, data: dict, exclude: ServerConnection | None = None) -> None:
        """Broadcast JSON message to all connected clients."""
        if not self._clients:
            return
        msg = json.dumps(data)
        targets = [ws for ws in self._clients if ws != exclude]
        websockets.broadcast(targets, msg)

    async def _broadcast_json_all(self, data: dict) -> None:
        """Broadcast JSON message to ALL connected clients (no exclusions)."""
        if not self._clients:
            return
        msg = json.dumps(data)
        websockets.broadcast(list(self._clients.keys()), msg)

    def _build_market_snapshot(self) -> list[dict]:
        """Build snapshot data for all stocks."""
        snapshots = []
        for symbol, book in self.engine.get_all_books().items():
            config = self.engine.config.get_stock(symbol)
            trades = self.engine.get_trades(symbol)
            last_trade = None
            if trades:
                t = trades[-1]
                last_trade = {
                    "price": t.price,
                    "quantity": t.quantity,
                    "time": t.timestamp,
                }
            snapshots.append({
                "type": "market_snapshot",
                "symbol": symbol,
                "floor": config.floor,
                "ceiling": config.ceiling,
                "price_step": config.price_step,
                "qty_step": config.qty_step,
                "market_state": self.engine.config.market_state.value,
                "sequence": 0,
                "bids": book.bids(),
                "asks": book.asks(),
                "last_trade": last_trade,
            })
        return snapshots

    async def _handle_new_order(self, ws: ServerConnection, client_id: str, data: dict) -> None:
        """Handle an incoming new_order message."""
        try:
            side = Side(data["side"].upper())
            ord_type = OrdType(data.get("ord_type", "LIMIT").upper())
            price = int(data.get("price", 0))
            quantity = int(data["quantity"])

            order = Order(
                cl_ord_id=data["cl_ord_id"],
                account=data.get("account", ""),
                symbol=data["symbol"].upper(),
                side=side,
                ord_type=ord_type,
                price=price,
                quantity=quantity,
            )
        except (KeyError, ValueError) as e:
            await self._send_json(ws, {
                "type": "error",
                "message": f"Invalid order: {e}",
            })
            self._log("OUT", client_id, "error", f"Invalid order: {e}")
            return

        # Log the incoming order as FIX
        fix_raw = fix_to_human(encode_new_order_single(order))
        self._log("IN", client_id, "new_order",
                  f"{order.side.value} {order.ord_type.value} {order.symbol} "
                  f"qty={order.quantity} px={order.price}",
                  fix_raw)

        # Submit to matching engine
        result = self.engine.submit_order(order)

        # Send execution reports
        for er in result.exec_reports:
            er_data = {
                "type": "execution_report",
                "cl_ord_id": er.cl_ord_id,
                "order_id": er.order_id,
                "exec_id": er.exec_id,
                "exec_type": er.exec_type.value,
                "ord_status": er.ord_status.value,
                "symbol": er.symbol,
                "side": er.side.value,
                "price": er.price,
                "quantity": er.quantity,
                "leaves_qty": er.leaves_qty,
                "cum_qty": er.cum_qty,
                "avg_px": er.avg_px,
                "last_px": er.last_px,
                "last_qty": er.last_qty,
                "reject_reason": er.reject_reason,
            }

            # Send to the ordering client
            if er.cl_ord_id == order.cl_ord_id:
                await self._send_json(ws, er_data)
            else:
                # This is a report for a resting order's owner
                # In a real system we'd track which client owns which order
                # For simplicity, broadcast fill reports for resting orders
                await self._broadcast_json_all(er_data)

            fix_er_raw = fix_to_human(encode_execution_report(er))
            self._log("OUT", client_id, "execution_report",
                      f"{er.exec_type.value} {er.symbol} {er.cl_ord_id} "
                      f"status={er.ord_status.value}",
                      fix_er_raw)

        # Broadcast trades
        for trade in result.trades:
            trade_data = {
                "type": "trade",
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "price": trade.price,
                "quantity": trade.quantity,
                "buy_order_id": trade.buy_order_id,
                "sell_order_id": trade.sell_order_id,
                "time": trade.timestamp,
            }
            await self._broadcast_json_all(trade_data)
            self._log("OUT", "ALL", "trade",
                      f"{trade.symbol} px={trade.price} qty={trade.quantity}")

        # Broadcast book updates
        for update in result.book_updates:
            update_msg = {
                "type": "market_update",
                **update,
            }
            await self._broadcast_json_all(update_msg)

    async def _handle_client(self, ws: ServerConnection) -> None:
        """Handle a single client connection lifecycle."""
        client_id = self._next_client_id()
        self._clients[ws] = client_id
        self._log("IN", client_id, "connect", "Client connected")

        try:
            # Send market snapshot on connect
            for snapshot in self._build_market_snapshot():
                await self._send_json(ws, snapshot)
            self._log("OUT", client_id, "snapshot", "Sent market snapshot")

            # Process messages
            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                except json.JSONDecodeError:
                    await self._send_json(ws, {
                        "type": "error",
                        "message": "Invalid JSON",
                    })
                    continue

                msg_type = data.get("type", "")
                if msg_type == "new_order":
                    await self._handle_new_order(ws, client_id, data)
                elif msg_type == "subscribe":
                    # Re-send snapshot
                    for snapshot in self._build_market_snapshot():
                        await self._send_json(ws, snapshot)
                else:
                    await self._send_json(ws, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })
        finally:
            del self._clients[ws]
            self._log("IN", client_id, "disconnect", "Client disconnected")

    async def start(self) -> Server:
        """Start the WebSocket server. Returns the server instance."""
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
        )
        return self._server

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
