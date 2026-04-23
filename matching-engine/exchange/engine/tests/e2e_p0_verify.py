"""Verify E2E-004 fix: client cannot crash engine via price<0 / qty<=0."""

from __future__ import annotations

import asyncio
import json
import websockets
import httpx

WS_URL = "ws://localhost:8765"
ADMIN = "http://localhost:8000"


async def main():
    # Ensure market open
    async with httpx.AsyncClient() as hc:
        await hc.post(f"{ADMIN}/api/market/start")

    # 1. Send price=-1 — must be rejected with error, not crash engine
    async with websockets.connect(WS_URL) as ws:
        # drain snapshot
        try:
            while True:
                await asyncio.wait_for(ws.recv(), timeout=0.2)
        except asyncio.TimeoutError:
            pass

        await ws.send(json.dumps({
            "type": "new_order", "cl_ord_id": "P0-NEG-PRICE",
            "account": "A", "symbol": "ACB", "side": "BUY",
            "ord_type": "LIMIT", "price": -1, "quantity": 100,
        }))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
        ok_price = msg.get("type") == "error" and "price" in msg.get("message", "").lower()
        print(f"[P0-A] price=-1 → {msg}, ok={ok_price}")

        # 2. Send quantity=0
        await ws.send(json.dumps({
            "type": "new_order", "cl_ord_id": "P0-ZERO-QTY",
            "account": "A", "symbol": "ACB", "side": "BUY",
            "ord_type": "LIMIT", "price": 25000, "quantity": 0,
        }))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
        ok_qty = msg.get("type") == "error" and "quantity" in msg.get("message", "").lower()
        print(f"[P0-B] qty=0 → {msg}, ok={ok_qty}")

        # 3. Send quantity=-100
        await ws.send(json.dumps({
            "type": "new_order", "cl_ord_id": "P0-NEG-QTY",
            "account": "A", "symbol": "ACB", "side": "BUY",
            "ord_type": "LIMIT", "price": 25000, "quantity": -100,
        }))
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
        ok_neg_qty = msg.get("type") == "error" and "quantity" in msg.get("message", "").lower()
        print(f"[P0-C] qty=-100 → {msg}, ok={ok_neg_qty}")

    # 4. Engine still alive?
    async with httpx.AsyncClient() as hc:
        r = await hc.get(f"{ADMIN}/api/market/state")
        alive = r.status_code == 200
        print(f"[P0-D] engine still alive? {alive} state={r.json()}")

    print(f"\nALL P0-verify: {all([ok_price, ok_qty, ok_neg_qty, alive])}")


if __name__ == "__main__":
    asyncio.run(main())
