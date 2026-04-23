import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const src = readFileSync(
  new URL("../../src/components/CommLogs.jsx", import.meta.url),
  "utf8"
);

describe("CommLogs list rendering — ECH-ADMIN-003", () => {
  // Extract the display.map(...) callback body so the assertions don't
  // accidentally match fragments used elsewhere.
  const mapMatch = src.match(/display\.map\(\s*\([^)]*\)\s*=>\s*\{[\s\S]*?^\s{12}\}\s*\)/m);
  const block = mapMatch ? mapMatch[0] : src;

  it("does not use fragment shorthand inside display.map", () => {
    // Shorthand <>...</> cannot carry a `key`, so when the map adds/removes
    // rows (expand toggle + prepended logs per 0.5s tick), React reconciles
    // by position and mounts/unmounts the wrong <tr>.
    assert.ok(
      !/<>\s*\n/.test(block) && !/<\/>\s*$/m.test(block),
      "Fragment shorthand <>...</> found inside display.map — the Fragment wrapping each log row must be keyed."
    );
  });

  it("wraps each mapped row in a keyed Fragment", () => {
    // Either <Fragment key=...> or React.Fragment key=...
    assert.match(
      block,
      /<(React\.)?Fragment\s+key=/,
      "Expected a keyed <Fragment key=...> wrapping each row in display.map."
    );
  });

  it("imports Fragment from react", () => {
    assert.match(
      src,
      /import\s+\{[^}]*\bFragment\b[^}]*\}\s+from\s+["']react["']/,
      "Expected `Fragment` to be imported from 'react'."
    );
  });
});
