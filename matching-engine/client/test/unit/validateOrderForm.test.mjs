import { test } from "node:test";
import assert from "node:assert/strict";
import { validateOrderForm } from "../../src/lib/validateOrderForm.js";

// ECH-CLIENT-001: quantity="0" bypasses the falsy-only guard.
// parseInt("0") === 0 → engine.submit_order sees qty<=0 → os._exit(1).
// Guard MUST reject qty="0".
test('ECH-CLIENT-001: quantity "0" must be rejected', () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "55000",
    quantity: "0",
  };
  assert.equal(validateOrderForm(form), false,
    'quantity "0" must not pass validation (would kill engine)');
});

test("valid LIMIT order passes validation", () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "55000",
    quantity: "100",
  };
  assert.equal(validateOrderForm(form), true);
});

test("empty account is still rejected", () => {
  const form = {
    account: "",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "55000",
    quantity: "100",
  };
  assert.equal(validateOrderForm(form), false);
});

test("empty quantity is still rejected", () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "55000",
    quantity: "",
  };
  assert.equal(validateOrderForm(form), false);
});

test("LIMIT with empty price is still rejected", () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "",
    quantity: "100",
  };
  assert.equal(validateOrderForm(form), false);
});

test("MARKET with empty price is allowed (price ignored)", () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "MARKET",
    price: "",
    quantity: "100",
  };
  assert.equal(validateOrderForm(form), true);
});
