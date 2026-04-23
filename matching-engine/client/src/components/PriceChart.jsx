import { useEffect, useRef, useState } from "react";
import {
  createChart,
  CrosshairMode,
  LineStyle,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
import useCandleData from "../hooks/useCandleData";

const SYMBOLS = ["ACB", "FPT", "VCK"];
const INTERVALS = [
  { label: "5s", value: 5 },
  { label: "15s", value: 15 },
  { label: "30s", value: 30 },
  { label: "1m", value: 60 },
];

export default function PriceChart({ trades }) {
  const [selectedSymbol, setSelectedSymbol] = useState("ACB");
  const [timeInterval, setTimeInterval] = useState(5);
  const [chartType, setChartType] = useState("candlestick");
  const [legend, setLegend] = useState(null);

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const priceSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const priceLineRef = useRef(null);

  const { candles, volumeBars } = useCandleData(trades, selectedSymbol, timeInterval);

  // Create chart instance once on mount
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "#0f0f1a" },
        textColor: "#888",
      },
      grid: {
        vertLines: { color: "#222240" },
        horzLines: { color: "#222240" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#333355" },
      timeScale: {
        borderColor: "#333355",
        timeVisible: true,
        secondsVisible: true,
      },
      width: chartContainerRef.current.clientWidth,
      height: 350,
    });

    chartRef.current = chart;

    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !priceSeriesRef.current || !volumeSeriesRef.current) {
        setLegend(null);
        return;
      }
      const priceData = param.seriesData.get(priceSeriesRef.current);
      const volData = param.seriesData.get(volumeSeriesRef.current);
      if (priceData) {
        setLegend({
          open: priceData.open ?? null,
          high: priceData.high ?? null,
          low: priceData.low ?? null,
          close: priceData.close ?? priceData.value ?? null,
          volume: volData?.value ?? null,
        });
      } else {
        setLegend(null);
      }
    });

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (chartRef.current) {
          chartRef.current.applyOptions({ width: entry.contentRect.width });
        }
      }
    });
    ro.observe(chartContainerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      priceSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // Rebuild series when chartType changes
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    if (priceSeriesRef.current) {
      chart.removeSeries(priceSeriesRef.current);
      priceSeriesRef.current = null;
    }
    if (volumeSeriesRef.current) {
      chart.removeSeries(volumeSeriesRef.current);
      volumeSeriesRef.current = null;
    }

    if (chartType === "candlestick") {
      priceSeriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: "#26a69a",
        downColor: "#ef5350",
        borderDownColor: "#ef5350",
        borderUpColor: "#26a69a",
        wickDownColor: "#ef5350",
        wickUpColor: "#26a69a",
      });
    } else {
      priceSeriesRef.current = chart.addSeries(LineSeries, {
        color: "#7c4dff",
        lineWidth: 2,
      });
    }

    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.9, bottom: 0 },
    });
  }, [chartType]);

  // Update data when candles/volumeBars/chartType change
  useEffect(() => {
    if (!priceSeriesRef.current || !volumeSeriesRef.current) return;
    if (candles.length === 0) return;

    if (chartType === "line") {
      priceSeriesRef.current.setData(
        candles.map((c) => ({ time: c.time, value: c.close }))
      );
    } else {
      priceSeriesRef.current.setData(candles);
    }
    volumeSeriesRef.current.setData(volumeBars);

    // Update current price line
    const lastPrice = candles[candles.length - 1].close;
    if (priceLineRef.current) {
      priceSeriesRef.current.removePriceLine(priceLineRef.current);
    }
    priceLineRef.current = priceSeriesRef.current.createPriceLine({
      price: lastPrice,
      color: "#ffeb3b",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "Last",
    });

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [candles, volumeBars, chartType]);

  return (
    <div className="price-chart">
      <div className="chart-header">
        <h2>Price Chart</h2>
        <div className="chart-controls">
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
          >
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select
            value={timeInterval}
            onChange={(e) => setTimeInterval(Number(e.target.value))}
          >
            {INTERVALS.map((i) => (
              <option key={i.value} value={i.value}>{i.label}</option>
            ))}
          </select>
          <button
            className={chartType === "candlestick" ? "active" : ""}
            onClick={() => setChartType("candlestick")}
          >
            Candle
          </button>
          <button
            className={chartType === "line" ? "active" : ""}
            onClick={() => setChartType("line")}
          >
            Line
          </button>
        </div>
      </div>
      <div style={{ position: "relative", display: candles.length === 0 ? "none" : "block" }}>
        {legend && (
          <div className="chart-legend">
            {legend.open != null && (
              <>
                <span>O <b>{legend.open.toLocaleString()}</b></span>
                <span>H <b>{legend.high.toLocaleString()}</b></span>
                <span>L <b>{legend.low.toLocaleString()}</b></span>
              </>
            )}
            <span>C <b>{(legend.close ?? 0).toLocaleString()}</b></span>
            {legend.volume != null && (
              <span className="legend-vol">Vol <b>{legend.volume.toLocaleString()}</b></span>
            )}
          </div>
        )}
        <div ref={chartContainerRef} />
      </div>
      {candles.length === 0 && <div className="empty">No trade data yet</div>}
    </div>
  );
}
