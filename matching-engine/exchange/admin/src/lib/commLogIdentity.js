export function getLogKey(log) {
  if (log == null) return null;
  const parts = [
    log.timestamp,
    log.direction,
    log.client_id,
    log.message_type,
    log.summary,
  ];
  return parts.map((p) => (p == null ? "" : String(p))).join("|");
}

export function findExpandedLog(display, expandedKey) {
  if (!expandedKey || !Array.isArray(display)) return null;
  return display.find((log) => getLogKey(log) === expandedKey) ?? null;
}
