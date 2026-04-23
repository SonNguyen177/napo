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

// ECH-CLIENT-002: <input type="number"> still accepts negative values at the
// DOM layer. validateOrderForm rejects qty<=0 (ECH-CLIENT-001), but the
// browser spinner / paste / keyboard still allows "-100". Defense-in-depth
// requires min="1" and step="1" on the quantity input so the browser blocks
// negative and fractional entries before they ever reach submit handler.
test("ECH-CLIENT-002: quantity input declares min='1' so browser blocks negatives", () => {
  const input = extractInput("quantity");
  assert.ok(input, "quantity input not found in OrderEntry.jsx");
  assert.match(
    input,
    /\bmin=["']1["']/,
    'quantity input must declare min="1" (defense-in-depth for ECH-CLIENT-002)'
  );
});

test("ECH-CLIENT-002: quantity input declares step='1' to block fractional entries", () => {
  const input = extractInput("quantity");
  assert.ok(input, "quantity input not found in OrderEntry.jsx");
  assert.match(
    input,
    /\bstep=["']1["']/,
    'quantity input must declare step="1" (defense-in-depth for ECH-CLIENT-002)'
  );
});

// Regression guard: validateOrderForm also rejects negatives at JS layer.
test("ECH-CLIENT-002: validateOrderForm rejects negative quantity '-100'", () => {
  const form = {
    account: "x",
    symbol: "FPT",
    side: "BUY",
    ord_type: "LIMIT",
    price: "55000",
    quantity: "-100",
  };
  assert.equal(
    validateOrderForm(form),
    false,
    "negative quantity must not pass validation (would kill engine)"
  );
});
