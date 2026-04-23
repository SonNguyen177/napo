import { useMemo } from "react";

export default function useCandleData(trades, symbol, intervalSeconds = 5) {
  return useMemo(() => {
    if (!trades || trades.length === 0 || !symbol) {
      return { candles: [], volumeBars: [] };
    }

    const filtered = trades.filter((t) => t.symbol === symbol);
    if (filtered.length === 0) {
      return { candles: [], volumeBars: [] };
    }

    // trades are stored newest-first, reverse to oldest-first
    const sorted = [...filtered].reverse();

    // lightweight-charts treats UTCTimestamp as UTC — offset to local so axis shows local time
    const tzOffsetSec = new Date().getTimezoneOffset() * -60;

    const candleMap = new Map();

    for (const t of sorted) {
      const localTime = Math.floor(t.time) + tzOffsetSec;
      const bucket = Math.floor(localTime / intervalSeconds) * intervalSeconds;

      if (candleMap.has(bucket)) {
        const c = candleMap.get(bucket);
        if (t.price > c.high) c.high = t.price;
        if (t.price < c.low) c.low = t.price;
        c.close = t.price;
        c.volume += t.quantity;
      } else {
        candleMap.set(bucket, {
          time: bucket,
          open: t.price,
          high: t.price,
          low: t.price,
          close: t.price,
          volume: t.quantity,
        });
      }
    }

    const candles = [];
    const volumeBars = [];
    const buckets = Array.from(candleMap.values());

    for (let i = 0; i < buckets.length; i++) {
      const c = buckets[i];
      // HLOC: open of current candle = close of previous candle (continuous)
      const open = i > 0 ? buckets[i - 1].close : c.open;
      candles.push({
        time: c.time,
        open,
        high: Math.max(c.high, open),
        low: Math.min(c.low, open),
        close: c.close,
      });
      volumeBars.push({
        time: c.time,
        value: c.volume,
        color: "rgba(33,150,243,0.4)",
      });
    }

    return { candles, volumeBars };
  }, [trades, symbol, intervalSeconds]);
}
