import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { generateAutoOrder } from "../../src/lib/generateAutoOrder.js";

// ECH-CLIENT-004: generateRandomOrder uses snap.qty_step / snap.price_step
// directly. If an admin sets qty_step=0 (or price_step=0, or ceiling<=floor),
// the auto-generator computes quantity=0 (or price=NaN) and ships it to the
// engine, whose submit_order envelope check does os._exit(1) — killing the
// whole engine from a single client auto-tick. The extracted helper MUST
// return null for every unsafe snapshot instead of producing a payload.

const goodSnap = {
  floor: 40000,
  ceiling: 60000,
  price_step: 100,
  qty_step: 100,
};

test("ECH-CLIENT-004: qty_step=0 must short-circuit (return null)", () => {
  const order = generateAutoOrder({
    symbol: "FPT",
    snap: { ...goodSnap, qty_step: 0 },
    random: () => 0.5,
    now: () => 1700000000000,
    counter: 1,
  });
  assert.equal(order, null, "qty_step=0 must abort auto-gen (would kill engine)");
});

test("ECH-CLIENT-004: price_step=0 must short-circuit (return null)", () => {
  const order = generateAutoOrder({
    symbol: "FPT",
    snap: { ...goodSnap, price_step: 0 },
    random: () => 0.5,
    now: () => 1700000000000,
    counter: 1,
  });
  assert.equal(order, null, "price_step=0 would produce NaN price");
});

test("ECH-CLIENT-004: ceiling<=floor must short-circuit (return null)", () => {
  const order = generateAutoOrder({
    symbol: "FPT",
    snap: { ...goodSnap, floor: 50000, ceiling: 40000 },
    random: () => 0.5,
    now: () => 1700000000000,
    counter: 1,
  });
  assert.equal(order, null, "ceiling<=floor kills engine via envelope check");
});

test("ECH-CLIENT-004: missing snap must short-circuit (return null)", () => {
  const order = generateAutoOrder({
    symbol: "FPT",
    snap: undefined,
    random: () => 0.5,
    now: () => 1700000000000,
    counter: 1,
  });
  assert.equal(order, null);
});

test("ECH-CLIENT-004: happy path produces a valid LIMIT order payload", () => {
  const order = generateAutoOrder({
    symbol: "FPT",
    snap: goodSnap,
    random: () => 0.25,
    now: () => 1700000000000,
    counter: 7,
  });
  assert.ok(order, "valid snapshot should produce a payload");
  assert.equal(order.symbol, "FPT");
  assert.equal(order.ord_type, "LIMIT");
  assert.equal(order.account, "AUTO");
  assert.ok(["BUY", "SELL"].includes(order.side));
  assert.ok(Number.isFinite(order.price) && order.price > 0, "price must be finite > 0");
  assert.ok(Number.isFinite(order.quantity) && order.quantity > 0, "quantity must be finite > 0");
  assert.ok(order.price >= goodSnap.floor && order.price <= goodSnap.ceiling,
    "price must stay inside [floor, ceiling]");
  assert.equal(order.price % goodSnap.price_step, 0, "price must be a multiple of price_step");
  assert.equal(order.quantity % goodSnap.qty_step, 0, "quantity must be a multiple of qty_step");
  assert.match(order.cl_ord_id, /^AUTO-/);
});

// Regression guard: generateRandomOrder inside OrderEntry.jsx must delegate to
// the extracted helper (or at least import it) so the guard is actually wired.
test("ECH-CLIENT-004: OrderEntry.jsx imports generateAutoOrder helper", () => {
  const jsxPath = path.resolve(
    import.meta.dirname,
    "../../src/components/OrderEntry.jsx"
  );
  const source = fs.readFileSync(jsxPath, "utf8");
  assert.match(
    source,
    /from\s+["'][^"']*generateAutoOrder[^"']*["']/,
    "OrderEntry.jsx must import generateAutoOrder so the guard is wired"
  );
});
