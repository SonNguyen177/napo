const SIDES = ["BUY", "SELL"];

function isPositive(n) {
  return typeof n === "number" && Number.isFinite(n) && n > 0;
}

export function generateAutoOrder({ symbol, snap, random = Math.random, now = Date.now, counter = 0 }) {
  if (!snap) return null;
  const { floor, ceiling, price_step, qty_step } = snap;
  if (!isPositive(price_step) || !isPositive(qty_step)) return null;
  if (!Number.isFinite(floor) || !Number.isFinite(ceiling) || ceiling <= floor) return null;

  const priceSteps = Math.floor((ceiling - floor) / price_step);
  const price = floor + Math.floor(random() * (priceSteps + 1)) * price_step;
  const qtySteps = Math.floor(random() * 5) + 1;
  const quantity = qtySteps * qty_step;

  if (!isPositive(price) || !isPositive(quantity)) return null;

  return {
    cl_ord_id: `AUTO-${now()}-${counter}`,
    account: "AUTO",
    symbol,
    side: random() > 0.5 ? SIDES[0] : SIDES[1],
    ord_type: "LIMIT",
    price,
    quantity,
  };
}
