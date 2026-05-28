import { useEffect, useState } from 'react'
import { useUIStore } from './store/uiStore'
import { useMarketStore } from './store/marketStore'
import { useOrderStore } from './store/orderStore'
import { useAgentLog } from './hooks/useAgentLog'
import api from './api/client'
import TradingChart from './components/chart/TradingChart'
import ScreenerPanel from './components/screener/ScreenerPanel'
import NewsFeed from './components/news/NewsFeed'
import OrdersPanel from './components/orders/OrdersPanel'
import WatchdogStatus from './components/watchdog/WatchdogStatus'
import BacktestPanel from './components/backtest/BacktestPanel'
import SettingsPanel from './components/settings/SettingsPanel'

const TABS = ['chart', 'screener', 'news', 'backtest', 'knowledge', 'settings']

export default function App() {
  const { activeTab, setTab, agentLogOpen, toggleAgentLog } = useUIStore()
  const { symbol, timeframe, setCandles, setPrice } = useMarketStore()
  const { setOrders, setAccount } = useOrderStore()
  const agentLogs = useAgentLog()
  const [settings, setSettings] = useState<any>(null)

  // Poll account + orders every 5s
  useEffect(() => {
    const fetch = async () => {
      try {
        const [acc, ord, sett] = await Promise.all([
          api.get('/market/account'),
          api.get('/orders'),
          api.get('/settings'),
        ])
        setAccount(acc.data)
        setOrders(ord.data)
        setSettings(sett.data)
      } catch {}
    }
    fetch()
    const id = setInterval(fetch, 5000)
    return () => clearInterval(id)
  }, [])

  // Load candles when symbol/timeframe changes
  useEffect(() => {
    api.get(`/market/candles/${encodeURIComponent(symbol)}`, { params: { timeframe } })
      .then(r => setCandles(r.data))
      .catch(() => {})
  }, [symbol, timeframe])

  const account = useOrderStore(s => s.account)
  const dailyPnl = account?.daily_pnl ?? 0
  const equity = account?.equity ?? 1000
  const croStatus = settings?.cro
  const mode = settings?.mode ?? 'PAPER'

  return (
    <div className="flex flex-col h-screen bg-[#0d1117] text-[#d1d4dc] overflow-hidden">

      {/* TOP BAR */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1e2329] border-b border-[#2a2f3a] flex-shrink-0">
        <div className="flex items-center gap-6">
          <span className="font-bold text-[#26a69a] text-sm">CBT TERMINAL</span>
          <span className="text-xs text-[#787b86]">
            Account: <span className="text-[#d1d4dc] font-medium">${equity.toLocaleString('en', {minimumFractionDigits: 2})}</span>
          </span>
          <span className="text-xs text-[#787b86]">
            Day P&L: <span className={`font-medium ${dailyPnl >= 0 ? 'text-[#26a69a]' : 'text-[#ef5350]'}`}>
              {dailyPnl >= 0 ? '+' : ''}${dailyPnl.toFixed(2)}
            </span>
          </span>
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${mode === 'PAPER' ? 'bg-yellow-600/20 text-yellow-400' : 'bg-green-600/20 text-[#26a69a]'}`}>
            ● {mode}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-[#787b86]">
            CRO: <span className={`font-medium ${croStatus?.halted_today ? 'text-[#ef5350]' : 'text-[#26a69a]'}`}>
              {croStatus?.halted_today ? 'HALTED' : '✓ OK'}
            </span>
          </span>
          <span className="text-xs text-[#787b86]">
            Daily: {croStatus?.daily_loss_pct?.toFixed(1) ?? '0.0'}% / {croStatus?.daily_limit_pct ?? 3}%
          </span>
        </div>
      </div>

      {/* TAB BAR */}
      <div className="flex bg-[#1e2329] border-b border-[#2a2f3a] flex-shrink-0">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setTab(tab)}
            className={`px-4 py-2 text-xs font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'text-[#26a69a] border-b-2 border-[#26a69a]'
                : 'text-[#787b86] hover:text-[#d1d4dc]'
            }`}
          >
            {tab}
          </button>
        ))}
        <div className="ml-auto px-3 flex items-center">
          <button onClick={toggleAgentLog} className="text-xs text-[#787b86] hover:text-[#d1d4dc]">
            Agent Log {agentLogOpen ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT PANEL — screener + news (chart tab only) */}
        {activeTab === 'chart' && (
          <div className="w-52 flex-shrink-0 border-r border-[#2a2f3a] flex flex-col overflow-hidden">
            <ScreenerPanel />
            <div className="border-t border-[#2a2f3a] flex-1 overflow-y-auto">
              <NewsFeed compact />
            </div>
          </div>
        )}

        {/* CENTER */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {activeTab === 'chart' && <TradingChart />}
          {activeTab === 'screener' && <ScreenerPanel fullWidth />}
          {activeTab === 'news' && <NewsFeed />}
          {activeTab === 'backtest' && <BacktestPanel />}
          {activeTab === 'knowledge' && (
            <iframe
              src="http://localhost:7474/browser/"
              className="flex-1 w-full h-full border-0"
              title="Neo4j Knowledge Graph"
            />
          )}
          {activeTab === 'settings' && <SettingsPanel settings={settings} />}
        </div>

        {/* RIGHT PANEL */}
        {activeTab === 'chart' && (
          <div className="w-64 flex-shrink-0 border-l border-[#2a2f3a] flex flex-col overflow-hidden">
            <OrdersPanel />
            <div className="border-t border-[#2a2f3a] p-3">
              <WatchdogStatus states={settings?.watchdog} />
            </div>
          </div>
        )}
      </div>

      {/* AGENT LOG DRAWER */}
      {agentLogOpen && (
        <div className="h-36 border-t border-[#2a2f3a] bg-[#0d1117] flex-shrink-0 overflow-y-auto p-2">
          <div className="text-[10px] text-[#787b86] mb-1 font-medium">AGENT LOG</div>
          {agentLogs.length === 0 && (
            <div className="text-[#787b86] text-xs">Waiting for agent cycle...</div>
          )}
          {[...agentLogs].reverse().map((log, i) => (
            <div key={i} className={`text-[11px] font-mono leading-5 ${
              log.includes('BLOCKED') || log.includes('ERROR') ? 'text-[#ef5350]' :
              log.includes('APPROVED') || log.includes('PLACED') ? 'text-[#26a69a]' :
              log.includes('FLAT') ? 'text-yellow-500' : 'text-[#787b86]'
            }`}>{log}</div>
          ))}
        </div>
      )}
    </div>
  )
}
