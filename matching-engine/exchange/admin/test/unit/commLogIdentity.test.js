import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  getLogKey,
  findExpandedLog,
} from "../../src/lib/commLogIdentity.js";

const mkLog = (overrides = {}) => ({
  timestamp: 1700000000,
  direction: "IN",
  client_id: "client-1",
  message_type: "D",
  summary: "NewOrderSingle ACB BUY 100@20000",
  fix_raw: "8=FIX.4.4|...",
  ...overrides,
});

describe("getLogKey", () => {
  it("returns the same key for the same log", () => {
    const log = mkLog();
    assert.equal(getLogKey(log), getLogKey(log));
  });

  it("returns different keys for different logs", () => {
    const a = mkLog({ timestamp: 1700000000, summary: "A" });
    const b = mkLog({ timestamp: 1700000001, summary: "B" });
    assert.notEqual(getLogKey(a), getLogKey(b));
  });

  it("handles null / missing fields without throwing", () => {
    assert.equal(getLogKey(null), null);
    assert.doesNotThrow(() =>
      getLogKey({ timestamp: 1, direction: null, client_id: undefined })
    );
  });
});

describe("findExpandedLog", () => {
  it("returns null when no key is provided", () => {
    assert.equal(findExpandedLog([mkLog()], null), null);
  });

  it("returns null when key is not in list (log evicted)", () => {
    const present = mkLog({ summary: "A" });
    const key = getLogKey(mkLog({ summary: "Z" }));
    assert.equal(findExpandedLog([present], key), null);
  });

  it("follows the user's original log after the list shifts (bug scenario)", () => {
    // User expands the 2nd row (index 1) in the reversed display.
    // Reversed display shows newest at index 0.
    const clicked = mkLog({
      timestamp: 1700000005,
      summary: "user-clicked-this-one",
    });
    const initialDisplay = [
      mkLog({ timestamp: 1700000006, summary: "newer-1" }),
      clicked, // index 1
      mkLog({ timestamp: 1700000004, summary: "older-1" }),
    ];
    const expandedKey = getLogKey(initialDisplay[1]);

    // A new log arrives; reversed display prepends it, shifting everything right.
    const refreshedDisplay = [
      mkLog({ timestamp: 1700000007, summary: "brand-new" }),
      ...initialDisplay,
    ];

    const found = findExpandedLog(refreshedDisplay, expandedKey);
    // Identity-based lookup must still resolve to the originally clicked log,
    // NOT whatever is currently at index 1 (which is now "newer-1").
    assert.equal(found?.summary, "user-clicked-this-one");
    assert.notEqual(found?.summary, refreshedDisplay[1].summary);
  });
});
