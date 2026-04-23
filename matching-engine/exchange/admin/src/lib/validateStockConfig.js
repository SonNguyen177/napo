export function validateStockConfig(form) {
  const floor = Number(form?.floor);
  const ceiling = Number(form?.ceiling);
  const priceStep = Number(form?.price_step);
  const qtyStep = Number(form?.qty_step);

  if (!Number.isFinite(floor) || floor <= 0) {
    return "Floor must be a positive number";
  }
  if (!Number.isFinite(ceiling) || ceiling <= 0) {
    return "Ceiling must be a positive number";
  }
  if (ceiling <= floor) {
    return "Ceiling must be greater than floor";
  }
  if (!Number.isFinite(priceStep) || priceStep <= 0) {
    return "Price step must be greater than 0";
  }
  if (!Number.isFinite(qtyStep) || qtyStep <= 0) {
    return "Qty step must be greater than 0";
  }
  return null;
}
