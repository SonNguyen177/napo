import { test } from "node:test";
import assert from "node:assert/strict";

import { validateStockConfig } from "../../src/lib/validateStockConfig.js";

const ok = { floor: 20000, ceiling: 30000, price_step: 100, qty_step: 100 };

test("returns null when all fields are valid", () => {
  assert.equal(validateStockConfig(ok), null);
});

test("rejects ceiling equal to floor (ECH-ADMIN-001 repro)", () => {
  const err = validateStockConfig({ ...ok, ceiling: ok.floor });
  assert.ok(err, "expected an error message, got null");
  assert.match(err, /ceiling/i);
});

test("rejects ceiling less than floor (ECH-ADMIN-001 repro)", () => {
  const err = validateStockConfig({ ...ok, floor: 20000, ceiling: 15000 });
  assert.ok(err, "expected an error message, got null");
  assert.match(err, /ceiling/i);
});

test("rejects price_step <= 0", () => {
  const zero = validateStockConfig({ ...ok, price_step: 0 });
  assert.ok(zero, "expected error for price_step=0");
  assert.match(zero, /price.?step/i);

  const neg = validateStockConfig({ ...ok, price_step: -5 });
  assert.ok(neg, "expected error for price_step<0");
});

test("rejects qty_step <= 0", () => {
  const zero = validateStockConfig({ ...ok, qty_step: 0 });
  assert.ok(zero, "expected error for qty_step=0");
  assert.match(zero, /qty.?step/i);

  const neg = validateStockConfig({ ...ok, qty_step: -10 });
  assert.ok(neg, "expected error for qty_step<0");
});

test("rejects floor <= 0", () => {
  const err = validateStockConfig({ ...ok, floor: 0 });
  assert.ok(err, "expected error for floor=0");
});
