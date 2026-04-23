export function validateOrderForm(form) {
  if (!form.account) return false;
  const qty = parseInt(form.quantity, 10);
  if (!Number.isFinite(qty) || qty <= 0) return false;
  if (form.ord_type === "LIMIT") {
    const price = parseInt(form.price, 10);
    if (!Number.isFinite(price) || price <= 0) return false;
  }
  return true;
}
