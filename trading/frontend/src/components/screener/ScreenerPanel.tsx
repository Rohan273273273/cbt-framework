import { useEffect, useState } from 'react'
import { useMarketStore } from '../../store/marketStore'
import api from '../../api/client'

interface ScreenerResult {
  symbol: string; composite_score: number; rel_volume: number
  atr_pct: number; rsi: number; trend: string
}

export default function ScreenerPanel({ fullWidth = false, compact = false }: { fullWidth?: boolean; compact?: boolean }) {
  const [results, setResults] = useState<ScreenerResult[]>([])
  const { setSymbol } = useMarketStore()

  useEffect(() => {
    const fetch = () => api.get('/screener/results').then(r => setResults(r.data)).catch(() => {})
    fetch()
    const id = setInterval(fetch, 10000)
    return () => clearInterval(id)
  }, [])

  const trendColor = (t: string) => t === 'bullish' ? 'text-[#26a69a]' : t === 'bearish' ? 'text-[#ef5350]' : 'text-[#787b86]'

  return (
    <div className={`${fullWidth ? 'p-4' : 'p-2'} overflow-y-auto`}>
      <div className="text-[10px] text-[#787b86] font-medium mb-2 uppercase tracking-wider">Screener</div>
      {results.length === 0 && <div className="text-xs text-[#787b86]">Loading...</div>}
      {results.map((r, i) => (
        <div
          key={r.symbol}
          onClick={() => setSymbol(r.symbol)}
          className="flex items-center justify-between py-1.5 px-1 hover:bg-[#1e2329] rounded cursor-pointer group"
        >
          <div className="flex items-center gap-2">
            <span className="text-[#787b86] text-[10px] w-3">{i + 1}</span>
            <div>
              <div className="text-xs font-medium text-[#d1d4dc]">{r.symbol.replace('/USD','')}</div>
              {!compact && <div className={`text-[10px] ${trendColor(r.trend)}`}>{r.trend}</div>}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-bold text-[#26a69a]">{r.composite_score}</div>
            {!compact && <div className="text-[10px] text-[#787b86]">{r.rel_volume.toFixed(1)}x vol</div>}
          </div>
        </div>
      ))}
    </div>
  )
}
