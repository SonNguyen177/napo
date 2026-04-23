import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { getBookSymbols } from "../../src/lib/getBookSymbols.js";

describe("getBookSymbols — ECH-ADMIN-005", () => {
  it("returns [] when both books and stocks are missing", () => {
    assert.deepEqual(getBookSymbols(undefined, undefined), []);
    assert.deepEqual(getBookSymbols(null, null), []);
  });

  it("reads symbols from books keys", () => {
    const books = { ACB: { bids: [], asks: [] }, FPT: { bids: [], asks: [] } };
    assert.deepEqual(getBookSymbols(books, undefined), ["ACB", "FPT"]);
  });

  it("falls back to stocks keys when books is empty", () => {
    // Engine booted but no orders placed yet: books may be {} while stocks is populated.
    const stocks = { ACB: {}, FPT: {}, VCK: {} };
    assert.deepEqual(getBookSymbols({}, stocks), ["ACB", "FPT", "VCK"]);
  });

  it("unions books and stocks so admin-added symbols appear even before orders", () => {
    // Regression: server adds HPG to DEFAULT_STOCKS but no orders yet → book key absent.
    const books = { ACB: { bids: [], asks: [] } };
    const stocks = { ACB: {}, HPG: {} };
    assert.deepEqual(getBookSymbols(books, stocks), ["ACB", "HPG"]);
  });

  it("sorts symbols for stable render order across ticks", () => {
    const books = { VCK: {}, ACB: {}, FPT: {} };
    assert.deepEqual(getBookSymbols(books, undefined), ["ACB", "FPT", "VCK"]);
  });

  it("deduplicates overlap between books and stocks", () => {
    const books = { ACB: {}, FPT: {} };
    const stocks = { ACB: {}, FPT: {}, VCK: {} };
    assert.deepEqual(getBookSymbols(books, stocks), ["ACB", "FPT", "VCK"]);
  });
});

describe("OrderBookView.jsx — ECH-ADMIN-005", () => {
  const src = readFileSync(
    new URL("../../src/components/OrderBookView.jsx", import.meta.url),
    "utf8"
  );

  it("does not hardcode a SYMBOLS array (repro)", () => {
    // The original bug: `const SYMBOLS = ["ACB", "FPT", "VCK"];` pins the admin
    // view to those three tickers, so any stock added to DEFAULT_STOCKS is invisible
    // even though StockConfig renders it dynamically.
    assert.ok(
      !/const\s+SYMBOLS\s*=\s*\[\s*["']ACB["']\s*,\s*["']FPT["']\s*,\s*["']VCK["']\s*\]/.test(src),
      "OrderBookView must not hardcode SYMBOLS = ['ACB','FPT','VCK'] — symbols must come from books/stocks."
    );
  });

  it("imports getBookSymbols from the helper module", () => {
    assert.match(
      src,
      /import\s+\{[^}]*\bgetBookSymbols\b[^}]*\}\s+from\s+["'][^"']*getBookSymbols(?:\.js)?["']/,
      "OrderBookView must import getBookSymbols to derive the list dynamically."
    );
  });

  it("calls getBookSymbols with the books prop", () => {
    assert.match(
      src,
      /getBookSymbols\s*\(\s*books\b/,
      "OrderBookView must call getBookSymbols(books, …) to drive the grid."
    );
  });
});
