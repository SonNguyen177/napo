export function validateOrderForm(form) {
  if (!form.account) return false;
  const qty = parseInt(form.quantity, 10);
  if (!Number.isFinite(qty) || qty <= 0) return false;
  if (form.ord_type === "LIMIT" && !form.price) return false;
  return true;
}
