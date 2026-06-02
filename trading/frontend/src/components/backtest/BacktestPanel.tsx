import { useState } from 'react'
import api from '../../api/client'

const STRATEGIES = ['volume_profile', 'amd_session', 'liquidity_sweep', 'order_blocks_fvg']
const SYMBOLS = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'AVAX/USD', 'LINK/USD']

export default function BacktestPanel() {
  const [symbol, setSymbol] = useState('BTC/USD')
  const [strategy, setStrategy] = useState('liquidity_sweep')
  const [timeframe, setTimeframe] = useState('1h')
  const [dateFrom, setDateFrom] = useState('2024-01-01')
  const [dateTo, setDateTo] = useState(new Date().toISOString().slice(0, 10))
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true); setError(''); setResults(null)
    try {
      const r = await api.post('/backtest/run', { symbol, strategy, timeframe, date_from: dateFrom, date_to: dateTo })
      setResults(r.data)
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Backtest failed')
    } finally {
      setLoading(false)
    }
  }

  const m = results?.metrics ?? {}

  const MetricCard = ({ label, value, color }: { label: string; value: string; color?: string }) => (
    <div className="bg-[#1e2329] rounded p-3">
      <div className="text-[10px] text-[#787b86] mb-1">{label}</div>
      <div className={`text-sm font-bold ${color ?? 'text-[#d1d4dc]'}`}>{value}</div>
    </div>
  )

  return (
    <div className="p-4 overflow-y-auto h-full">
      {/* Config row */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select value={symbol} onChange={e => setSymbol(e.target.value)} className="bg-[#1e2329] text-[#d1d4dc] text-xs px-3 py-2 rounded border border-[#2a2f3a] outline-none">
          {SYMBOLS.map(s => <option key={s}>{s}</option>)}
        </select>
        <select value={strategy} onChange={e => setStrategy(e.target.value)} className="bg-[#1e2329] text-[#d1d4dc] text-xs px-3 py-2 rounded border border-[#2a2f3a] outline-none">
          {STRATEGIES.map(s => <option key={s}>{s}</option>)}
        </select>
        <select value={timeframe} onChange={e => setTimeframe(e.target.value)} className="bg-[#1e2329] text-[#d1d4dc] text-xs px-3 py-2 rounded border border-[#2a2f3a] outline-none">
          {['1h','4h','1D'].map(tf => <option key={tf}>{tf}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="bg-[#1e2329] text-[#d1d4dc] text-xs px-3 py-2 rounded border border-[#2a2f3a] outline-none" />
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="bg-[#1e2329] text-[#d1d4dc] text-xs px-3 py-2 rounded border border-[#2a2f3a] outline-none" />
        <button onClick={run} disabled={loading} className="bg-[#26a69a] text-white text-xs px-4 py-2 rounded font-medium hover:bg-[#2bbbad] disabled:opacity-50">
          {loading ? 'Running...' : '▶ Run Backtest'}
        </button>
      </div>

      {error && <div className="text-[#ef5350] text-sm mb-4">{error}</div>}

      {results && (
        <>
          <div className="grid grid-cols-4 gap-2 mb-4">
            <MetricCard label="Total Trades" value={String(results.trades?.length ?? '—')} />
            <MetricCard label="Win Rate" value={m.win_rate != null ? `${(m.win_rate * 100).toFixed(1)}%` : '—'} color={m.win_rate > 0.55 ? 'text-[#26a69a]' : 'text-[#ef5350]'} />
            <MetricCard label="Profit Factor" value={m.profit_factor != null ? m.profit_factor.toFixed(2) : '—'} color={m.profit_factor > 1.5 ? 'text-[#26a69a]' : 'text-[#787b86]'} />
            <MetricCard label="Sharpe Ratio" value={m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(2) : '—'} />
            <MetricCard label="Max Drawdown" value={m.max_drawdown != null ? `${(m.max_drawdown * 100).toFixed(1)}%` : '—'} color="text-[#ef5350]" />
            <MetricCard label="Avg Win" value={m.avg_win != null ? `$${m.avg_win.toFixed(2)}` : '—'} color="text-[#26a69a]" />
            <MetricCard label="Avg Loss" value={m.avg_loss != null ? `$${Math.abs(m.avg_loss).toFixed(2)}` : '—'} color="text-[#ef5350]" />
            <MetricCard label="Expectancy" value={m.expectancy != null ? `$${m.expectancy.toFixed(2)}` : '—'} />
          </div>

          {/* Trade list */}
          <div className="text-[10px] text-[#787b86] mb-2 uppercase tracking-wider">Trades</div>
          <div className="space-y-1">
            {results.trades?.slice(-50).map((t: any, i: number) => (
              <div key={i} className={`flex justify-between text-xs px-2 py-1 rounded border-l-2 ${t.color === 'green' ? 'border-[#26a69a] bg-[#26a69a]/5' : 'border-[#ef5350] bg-[#ef5350]/5'}`}>
                <span className="text-[#787b86]">{t.direction === 1 ? 'LONG' : 'SHORT'} @ {t.entry_price?.toFixed(2)}</span>
                <span className={t.pnl >= 0 ? 'text-[#26a69a]' : 'text-[#ef5350]'}>
                  {t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(4)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
