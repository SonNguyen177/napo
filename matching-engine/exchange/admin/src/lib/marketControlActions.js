export async function runMarketAction(action) {
  if (typeof action !== "function") {
    return { ok: false, error: "Invalid action" };
  }
  try {
    await action();
    return { ok: true, error: null };
  } catch (err) {
    const message =
      err instanceof Error && err.message
        ? err.message
        : typeof err === "string" && err
          ? err
          : "Unknown error";
    return { ok: false, error: message };
  }
}
