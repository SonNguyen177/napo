export function getBookSymbols(books, stocks) {
  const keys = new Set();
  if (books && typeof books === "object") {
    for (const k of Object.keys(books)) keys.add(k);
  }
  if (stocks && typeof stocks === "object") {
    for (const k of Object.keys(stocks)) keys.add(k);
  }
  return Array.from(keys).sort();
}
