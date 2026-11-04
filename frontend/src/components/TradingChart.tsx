import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  IPriceLine,
  LineStyle,
  CrosshairMode,
  SeriesMarker,
  Time,
} from 'lightweight-charts';
import { CandleBar, Instrument, PriceUpdateEvent, SignalEvent } from '../types';

interface TradingChartProps {
  instrument: Instrument;
  candles: CandleBar[];
  signals: SignalEvent[];
  selectedSignal: SignalEvent | null;
  latestQuote: PriceUpdateEvent | null;
}

interface ShadedBandCoords {
  top: number;
  height: number;
  isLong: boolean;
  entryY: number | null;
}

export const TradingChart: React.FC<TradingChartProps> = ({
  instrument,
  candles,
  signals,
  selectedSignal,
  latestQuote,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const [bandCoords, setBandCoords] = useState<ShadedBandCoords | null>(null);

  // Determine the active signal for this instrument (user-selected or latest with SL/TP)
  const activeSignal =
    (selectedSignal && selectedSignal.instrument === instrument ? selectedSignal : null) ||
    signals.find(
      (s) =>
        s.instrument === instrument &&
        (s.signal_type === 'BUY' || s.signal_type === 'SELL') &&
        s.stop_loss !== null &&
        s.take_profit !== null
    ) ||
    signals.find((s) => s.instrument === instrument) ||
    null;

  const updateShadedZone = useCallback(() => {
    const series = candleSeriesRef.current;
    if (
      !series ||
      !activeSignal ||
      activeSignal.stop_loss == null ||
      activeSignal.take_profit == null
    ) {
      setBandCoords(null);
      return;
    }

    const slY = series.priceToCoordinate(activeSignal.stop_loss);
    const tpY = series.priceToCoordinate(activeSignal.take_profit);
    const entryY = series.priceToCoordinate(activeSignal.entry_price);

    if (slY === null || tpY === null) {
      setBandCoords(null);
      return;
    }

    const top = Math.min(slY, tpY);
    const height = Math.max(2, Math.abs(tpY - slY));
    setBandCoords({
      top,
      height,
      isLong: activeSignal.signal_type !== 'SELL',
      entryY: entryY ?? null,
    });
  }, [activeSignal]);

  // Initialize chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight || 420,
      layout: {
        background: { color: '#0b101b' },
        textColor: '#94a3b8',
        fontFamily: 'JetBrains Mono, Consolas, monospace',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#1e293b',
        scaleMargins: {
          top: 0.12,
          bottom: 0.24,
        },
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
        secondsVisible: true,
      },
      watermark: {
        visible: true,
        fontSize: 28,
        horzAlign: 'center',
        vertAlign: 'center',
        color: 'rgba(148, 163, 184, 0.10)',
        text: 'DATOS SINTÉTICOS — SIMULACIÓN',
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    const volumeSeries = chart.addHistogramSeries({
      color: '#38bdf8',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleResize = () => {
      if (!containerRef.current || !chartRef.current) return;
      chartRef.current.applyOptions({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight || 420,
      });
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // Update candles & volume series data
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!candleSeries || !volumeSeries || candles.length === 0) return;

    // Sort & deduplicate by time ascending
    const sorted = [...candles]
      .sort((a, b) => a.time - b.time)
      .filter((item, idx, arr) => idx === 0 || item.time > arr[idx - 1].time);

    candleSeries.setData(
      sorted.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    volumeSeries.setData(
      sorted.map((c) => ({
        time: c.time as Time,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)',
      }))
    );

    updateShadedZone();
  }, [candles, instrument, updateShadedZone]);

  // Update visual markers (BUY / SELL / NO_OP) on the candlestick series
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    if (!candleSeries || candles.length === 0) return;

    const validTimes = candles.map((c) => c.time).sort((a, b) => a - b);
    const findClosestCandleTime = (target?: number): number => {
      if (!target) return validTimes[validTimes.length - 1];
      let best = validTimes[0];
      let minDiff = Math.abs(target - best);
      for (const t of validTimes) {
        const d = Math.abs(target - t);
        if (d <= minDiff) {
          minDiff = d;
          best = t;
        }
      }
      return best;
    };

    const instSignals = signals
      .filter((s) => s.instrument === instrument)
      .slice(0, 30);

    const markerByTime = new Map<number, SeriesMarker<Time>>();
    for (const sig of instSignals) {
      const barTime = findClosestCandleTime(sig.chart_time);
      if (sig.signal_type === 'BUY') {
        markerByTime.set(barTime, {
          time: barTime as Time,
          position: 'belowBar',
          color: '#10b981',
          shape: 'arrowUp',
          text: `🟢 BUY @ ${sig.entry_price.toFixed(2)}`,
        });
      } else if (sig.signal_type === 'SELL') {
        markerByTime.set(barTime, {
          time: barTime as Time,
          position: 'aboveBar',
          color: '#ef4444',
          shape: 'arrowDown',
          text: `🔴 SELL @ ${sig.entry_price.toFixed(2)}`,
        });
      } else if (!markerByTime.has(barTime)) {
        markerByTime.set(barTime, {
          time: barTime as Time,
          position: 'inBar',
          color: '#eab308',
          shape: 'circle',
          text: '🟡 NO_OP',
        });
      }
    }

    const sortedMarkers = Array.from(markerByTime.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([, m]) => m);

    candleSeries.setMarkers(sortedMarkers);
  }, [signals, candles, instrument]);

  // Draw stop_loss, take_profit, and entry_price lines + shaded zone
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !chart) return;

    // Remove previous price lines
    for (const line of priceLinesRef.current) {
      try {
        candleSeries.removePriceLine(line);
      } catch {
        // ignore
      }
    }
    priceLinesRef.current = [];

    if (activeSignal) {
      const entryLine = candleSeries.createPriceLine({
        price: activeSignal.entry_price,
        color:
          activeSignal.signal_type === 'BUY'
            ? '#10b981'
            : activeSignal.signal_type === 'SELL'
            ? '#ef4444'
            : '#eab308',
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: `ENTRY (${activeSignal.signal_type === 'NO_OPERATION' ? 'NO_OP' : activeSignal.signal_type})`,
      });
      priceLinesRef.current.push(entryLine);

      if (activeSignal.stop_loss != null) {
        const slLine = candleSeries.createPriceLine({
          price: activeSignal.stop_loss,
          color: '#ef4444',
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'STOP LOSS',
        });
        priceLinesRef.current.push(slLine);
      }

      if (activeSignal.take_profit != null) {
        const tpLine = candleSeries.createPriceLine({
          price: activeSignal.take_profit,
          color: '#10b981',
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'TAKE PROFIT',
        });
        priceLinesRef.current.push(tpLine);
      }
    }

    updateShadedZone();
    const timeScale = chart.timeScale();
    const onRangeChange = () => updateShadedZone();
    timeScale.subscribeVisibleLogicalRangeChange(onRangeChange);

    return () => {
      timeScale.unsubscribeVisibleLogicalRangeChange(onRangeChange);
    };
  }, [activeSignal, candles, updateShadedZone]);

  // Center chart when user clicks a specific signal in SignalsPanel
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !selectedSignal || selectedSignal.instrument !== instrument || candles.length === 0) {
      return;
    }
    const targetTime = selectedSignal.chart_time;
    if (!targetTime) return;

    const sorted = [...candles].sort((a, b) => a.time - b.time);
    const idx = sorted.findIndex((c) => Math.abs(c.time - targetTime) <= 60);
    if (idx >= 0) {
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, idx - 20),
        to: Math.min(sorted.length + 5, idx + 20),
      });
      setTimeout(updateShadedZone, 50);
    }
  }, [selectedSignal, instrument, candles, updateShadedZone]);

  const lastCandle = candles[candles.length - 1];
  const currentPrice = latestQuote?.price ?? lastCandle?.close ?? 0;
  const bid = latestQuote?.bid ?? (currentPrice ? +(currentPrice * 0.9998).toFixed(2) : 0);
  const ask = latestQuote?.ask ?? (currentPrice ? +(currentPrice * 1.0002).toFixed(2) : 0);
  const volume = latestQuote?.volume ?? lastCandle?.volume ?? 0;

  return (
    <div className="flex flex-col h-full bg-[#0b101b] border border-slate-800 rounded-lg overflow-hidden">
      {/* Chart Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-sky-400 animate-pulse" />
            <h2 className="text-base font-bold font-mono tracking-tight text-white">
              {instrument}
            </h2>
          </div>
          <span className="px-2 py-0.5 text-[11px] font-mono font-semibold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30 rounded">
            DATOS SINTÉTICOS — SIMULACIÓN
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-400 mr-1">PRECIO:</span>
            <span className="text-white font-bold">${currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1">BID:</span>
            <span className="text-emerald-400">${bid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1">ASK:</span>
            <span className="text-rose-400">${ask.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          <div>
            <span className="text-slate-400 mr-1">VOL:</span>
            <span className="text-sky-300">{volume.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Legend Bar for Active Signal */}
      {activeSignal && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-1.5 bg-slate-950/80 border-b border-slate-800/80 text-[11px] font-mono">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-slate-400">SEÑAL ACTIVA EN GRÁFICO:</span>
            <span
              className={`px-1.5 py-0.5 rounded font-bold ${
                activeSignal.signal_type === 'BUY'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : activeSignal.signal_type === 'SELL'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/40'
              }`}
            >
              {activeSignal.signal_type === 'BUY'
                ? '🟢 BUY'
                : activeSignal.signal_type === 'SELL'
                ? '🔴 SELL'
                : '🟡 NO_OP'}
            </span>
            <span className="text-slate-300">
              Entry: <strong className="text-white">${activeSignal.entry_price.toFixed(2)}</strong>
            </span>
            {activeSignal.stop_loss != null && (
              <span className="text-rose-400">
                SL (rojo punteado): <strong>${activeSignal.stop_loss.toFixed(2)}</strong>
              </span>
            )}
            {activeSignal.take_profit != null && (
              <span className="text-emerald-400">
                TP (verde punteado): <strong>${activeSignal.take_profit.toFixed(2)}</strong>
              </span>
            )}
          </div>
          <div className="text-slate-500">
            Click en cualquier señal del panel derecho para centrar
          </div>
        </div>
      )}

      {/* Chart Canvas + Shaded SL/TP Band Overlay */}
      <div className="relative flex-1 min-h-[340px] w-full">
        {bandCoords && (
          <div
            className="pointer-events-none absolute left-0 right-[68px] z-10 transition-all duration-75"
            style={{
              top: `${bandCoords.top}px`,
              height: `${bandCoords.height}px`,
              background: bandCoords.isLong
                ? 'linear-gradient(180deg, rgba(16, 185, 129, 0.14) 0%, rgba(239, 68, 68, 0.14) 100%)'
                : 'linear-gradient(180deg, rgba(239, 68, 68, 0.14) 0%, rgba(16, 185, 129, 0.14) 100%)',
              borderTop: '1px dashed rgba(16, 185, 129, 0.35)',
              borderBottom: '1px dashed rgba(239, 68, 68, 0.35)',
            }}
          >
            <span className="absolute right-2 top-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900/80 text-slate-300 border border-slate-700/60">
              Rango SL / TP ({activeSignal?.signal_type === 'NO_OPERATION' ? 'NO_OP' : activeSignal?.signal_type})
            </span>
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>
    </div>
  );
};
