import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { validateOrderForm } from "../../src/lib/validateOrderForm.js";

const jsxPath = path.resolve(
  import.meta.dirname,
  "../../src/components/OrderEntry.jsx"
);
const source = fs.readFileSync(jsxPath, "utf8");

function extractInput(name) {
  const re = new RegExp(`<input[^>]*\\bname="${name}"[^>]*/?>`, "s");
  return source.match(re)?.[0];
}

// ECH-CLIENT-003: LIMIT with price="-1" bypasses the truthy guard.
// parseInt("-1") === -1 → engine.submit_order sees price<0 → os._exit(1).
// Guard MUST reject negative/zero price for LIMIT orders.
test('ECH-CLIENT-003: LIMIT price "-1" must be rejected', () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "-1",
    quantity: "100",
  };
  assert.equal(
    validateOrderForm(form),
    false,
    'LIMIT price "-1" must not pass validation (would kill engine)'
  );
});

test('ECH-CLIENT-003: LIMIT price "0" must be rejected', () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "0",
    quantity: "100",
  };
  assert.equal(
    validateOrderForm(form),
    false,
    'LIMIT price "0" must not pass validation'
  );
});

test('ECH-CLIENT-003: LIMIT price "abc" must be rejected', () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "abc",
    quantity: "100",
  };
  assert.equal(
    validateOrderForm(form),
    false,
    "non-numeric price must not pass validation"
  );
});

test("ECH-CLIENT-003: price input declares min='1' so browser blocks negatives", () => {
  const input = extractInput("price");
  assert.ok(input, "price input not found in OrderEntry.jsx");
  assert.match(
    input,
    /\bmin=["']1["']/,
    'price input must declare min="1" (defense-in-depth for ECH-CLIENT-003)'
  );
});

test("ECH-CLIENT-003: price input declares step='1' to block fractional entries", () => {
  const input = extractInput("price");
  assert.ok(input, "price input not found in OrderEntry.jsx");
  assert.match(
    input,
    /\bstep=["']1["']/,
    'price input must declare step="1" (defense-in-depth for ECH-CLIENT-003)'
  );
});

test("ECH-CLIENT-003: MARKET with negative price is still allowed (price ignored)", () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "MARKET",
    price: "-1",
    quantity: "100",
  };
  assert.equal(
    validateOrderForm(form),
    true,
    "MARKET ignores price field entirely"
  );
});
