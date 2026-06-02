import { useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts'
import { useMarketStore } from '../../store/marketStore'

const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1D']

export default function TradingChart() {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<any>(null)
  const seriesRef = useRef<any>(null)
  const { symbol, timeframe, candles, setSymbol, setTimeframe } = useMarketStore()

  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0d1117' }, textColor: '#787b86' },
      grid: { vertLines: { color: '#1e2329' }, horzLines: { color: '#1e2329' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#2a2f3a' },
      timeScale: { borderColor: '#2a2f3a', timeVisible: true },
      width: chartRef.current.clientWidth,
      height: chartRef.current.clientHeight,
    })
    const series = chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    })
    chartInstance.current = chart
    seriesRef.current = series

    const ro = new ResizeObserver(() => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth, height: chartRef.current.clientHeight })
      }
    })
    ro.observe(chartRef.current)
    return () => { chart.remove(); ro.disconnect() }
  }, [])

  useEffect(() => {
    if (!seriesRef.current || !candles.length) return
    const data = candles
      .filter(c => c.open && c.high && c.low && c.close)
      .map(c => ({
        time: Math.floor(new Date(c.ts).getTime() / 1000) as any,
        open: c.open, high: c.high, low: c.low, close: c.close,
      }))
      .sort((a, b) => a.time - b.time)
    seriesRef.current.setData(data)
  }, [candles])

  const lastCandle = candles[candles.length - 1]
  const price = lastCandle?.close
  const priceColor = lastCandle && lastCandle.close >= lastCandle.open ? '#26a69a' : '#ef5350'

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Chart toolbar */}
      <div className="flex items-center gap-3 px-3 py-1.5 border-b border-[#2a2f3a] bg-[#1e2329] flex-shrink-0">
        <select
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          className="bg-[#2a2f3a] text-[#d1d4dc] text-xs px-2 py-1 rounded border-0 outline-none"
        >
          {['BTC/USD','ETH/USD','SOL/USD','AVAX/USD','LINK/USD'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {price && (
          <span className="font-bold text-sm" style={{ color: priceColor }}>
            ${price.toLocaleString('en', { minimumFractionDigits: 2 })}
          </span>
        )}
        <div className="flex gap-1 ml-2">
          {TIMEFRAMES.map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-0.5 text-xs rounded ${
                timeframe === tf ? 'bg-[#26a69a] text-white' : 'text-[#787b86] hover:text-[#d1d4dc]'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div ref={chartRef} className="flex-1" />
    </div>
  )
}
