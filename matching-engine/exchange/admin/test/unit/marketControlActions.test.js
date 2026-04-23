import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { runMarketAction } from "../../src/lib/marketControlActions.js";

describe("runMarketAction — ECH-ADMIN-004", () => {
  it("returns { ok: true, error: null } when the action resolves", async () => {
    const result = await runMarketAction(async () => undefined);
    assert.deepEqual(result, { ok: true, error: null });
  });

  it("captures Error messages instead of leaking as unhandled rejection (repro)", async () => {
    // Simulates api.startMarket() rejecting with the exact message useAdminApi
    // throws on HTTP 400 ("Market is already closed" / "Market is already open").
    const result = await runMarketAction(async () => {
      throw new Error("Market is already closed");
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "Market is already closed");
  });

  it("coerces non-Error rejections to a usable string", async () => {
    const result = await runMarketAction(async () => {
      throw "boom"; // eslint-disable-line no-throw-literal
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "boom");
  });

  it("returns an error when the argument is not a function", async () => {
    const result = await runMarketAction(null);
    assert.equal(result.ok, false);
    assert.match(result.error, /action/i);
  });
});

describe("App.jsx integration — ECH-ADMIN-004", () => {
  const src = readFileSync(
    new URL("../../src/App.jsx", import.meta.url),
    "utf8"
  );

  it("imports runMarketAction from the helper module", () => {
    assert.match(
      src,
      /import\s+\{[^}]*\brunMarketAction\b[^}]*\}\s+from\s+["'][^"']*marketControlActions["']/,
      "App.jsx must import runMarketAction so market-state button clicks no longer leak unhandled rejections."
    );
  });

  it("tracks an error message in component state", () => {
    assert.match(
      src,
      /useState\s*\(\s*(?:""|null)\s*\)/,
      "App.jsx must hold an errorMsg state to surface failed market/start|stop calls."
    );
  });

  it("renders the error message so the user sees silent failures", () => {
    // Rendering errorMsg is the whole point of the fix — if it isn't displayed,
    // the unhandled rejection is just moved from console to state.
    assert.match(
      src,
      /\{errorMsg[^}]*\}/,
      "App.jsx must render errorMsg somewhere so failed Start/Stop clicks are visible."
    );
  });
});
