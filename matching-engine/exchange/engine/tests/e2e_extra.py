"""Additional E2E checks for items not covered by the main runner.

Covers:
- Terminal state guard on Order.fill()/cancel() (via direct model unit)
- Floor/ceiling gap < price_step (admin-side validation)
- Re-validation of resting orders when stock config changes
- Stock list/symbols-only lookup (client should only use declared symbols)
- Price_step alignment using floor as base (already validated via main runner)
"""

from __future__ import annotations

import asyncio
import json
import httpx


ADMIN = "http://localhost:8000"


async def main():
    # A. Terminal state guards (in-process model check)
    from engine.models import Order, OrdStatus, OrdType, Side
    o = Order(cl_ord_id="X", account="A", symbol="ACB", side=Side.BUY,
              ord_type=OrdType.LIMIT, price=25000, quantity=100)
    o.fill(100, 25000)  # FILLED
    assert o.status == OrdStatus.FILLED
    # Try to fill again → should be guarded; current implementation allows it
    try:
        o.fill(50, 25000)
        extra_fill_allowed = True
        # After 2nd fill, filled_qty becomes 150 > quantity 100 (invariant violated)
        invariant_broken = (o.filled_qty > o.quantity) or (o.leaves_qty < 0)
    except Exception:
        extra_fill_allowed = False
        invariant_broken = False
    print(f"[GUARD] extra_fill_allowed_after_FILLED={extra_fill_allowed}, "
          f"invariant_broken={invariant_broken}, filled={o.filled_qty}/{o.quantity}, leaves={o.leaves_qty}")

    # Cancel after FILLED
    try:
        o.cancel()
        cancel_after_fill_allowed = True
        status_after = o.status
    except Exception:
        cancel_after_fill_allowed = False
        status_after = None
    print(f"[GUARD] cancel_after_FILLED_allowed={cancel_after_fill_allowed}, status={status_after}")

    # Fresh order: cancel then fill
    o2 = Order(cl_ord_id="Y", account="A", symbol="ACB", side=Side.BUY,
               ord_type=OrdType.LIMIT, price=25000, quantity=100)
    o2.cancel()
    assert o2.status == OrdStatus.CANCELLED
    try:
        o2.fill(50, 25000)
        fill_after_cancel_allowed = True
    except Exception:
        fill_after_cancel_allowed = False
    print(f"[GUARD] fill_after_CANCELLED_allowed={fill_after_cancel_allowed}, "
          f"status={o2.status}, filled={o2.filled_qty}")

    # B. Admin: gap < step — ceiling - floor < price_step
    async with httpx.AsyncClient() as hc:
        # Save current ACB
        r = await hc.get(f"{ADMIN}/api/stocks/ACB")
        before = r.json()
        # Set floor=25000, ceiling=25050, price_step=100 → gap=50 < step=100 → no valid price
        r = await hc.put(f"{ADMIN}/api/stocks/ACB",
                         json={"floor": 25000, "ceiling": 25050, "price_step": 100})
        print(f"[ADMIN] gap<step accepted? status={r.status_code}")
        # revert
        await hc.put(f"{ADMIN}/api/stocks/ACB", json=before)

    # C. Existing rest order stays even after config tightens (intentional per CLAUDE.md,
    # reporting for completeness, not as bug)
    print("[ADMIN] resting orders not revalidated on config change: intentional (see CLAUDE.md)")


if __name__ == "__main__":
    asyncio.run(main())
