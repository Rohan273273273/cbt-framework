export default function SettingsPanel({ settings }: { settings: any }) {
  if (!settings) return <div className="p-4 text-[#787b86]">Loading...</div>

  const s = settings
  const watchdog = s.watchdog ?? {}
  const ml = s.ml ?? {}

  const stateColor = (state: string) =>
    state === 'NORMAL' ? 'text-[#26a69a]' : state === 'REDUCED' ? 'text-yellow-400' : 'text-[#ef5350]'

  return (
    <div className="p-6 overflow-y-auto h-full max-w-2xl">
      <div className="space-y-6">

        {/* Mode */}
        <section>
          <div className="text-[10px] text-[#787b86] font-medium mb-3 uppercase tracking-wider">Trading Mode</div>
          <div className={`inline-block px-4 py-2 rounded text-sm font-bold ${s.mode === 'PAPER' ? 'bg-yellow-600/20 text-yellow-400' : 'bg-[#26a69a]/20 text-[#26a69a]'}`}>
            ● {s.mode}
          </div>
          <div className="text-xs text-[#787b86] mt-2">To switch live: set PAPER=false in .env and restart backend</div>
        </section>

        {/* Account */}
        <section>
          <div className="text-[10px] text-[#787b86] font-medium mb-3 uppercase tracking-wider">Account</div>
          <div className="grid grid-cols-3 gap-3">
            {[
              ['Equity', `$${(s.account?.equity ?? 0).toFixed(2)}`],
              ['Cash', `$${(s.account?.cash ?? 0).toFixed(2)}`],
              ['Day P&L', `${s.account?.daily_pnl >= 0 ? '+' : ''}$${(s.account?.daily_pnl ?? 0).toFixed(2)}`],
            ].map(([l, v]) => (
              <div key={l} className="bg-[#1e2329] rounded p-3">
                <div className="text-[10px] text-[#787b86]">{l}</div>
                <div className="text-sm font-bold text-[#d1d4dc] mt-1">{v}</div>
              </div>
            ))}
          </div>
        </section>

        {/* CRO */}
        <section>
          <div className="text-[10px] text-[#787b86] font-medium mb-3 uppercase tracking-wider">CRO Risk Limits</div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-[#787b86]">Daily loss used</span>
              <span className={s.cro?.halted_today ? 'text-[#ef5350]' : 'text-[#26a69a]'}>
                {s.cro?.daily_loss_pct?.toFixed(1) ?? '0.0'}% / {s.cro?.daily_limit_pct ?? 3}%
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[#787b86]">Open positions</span>
              <span className="text-[#d1d4dc]">{s.cro?.open_positions ?? 0} / {s.cro?.max_positions ?? 3}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[#787b86]">Status</span>
              <span className={s.cro?.halted_today ? 'text-[#ef5350] font-bold' : 'text-[#26a69a]'}>
                {s.cro?.halted_today ? 'HALTED TODAY' : '✓ ACTIVE'}
              </span>
            </div>
          </div>
        </section>

        {/* Watchdog */}
        <section>
          <div className="text-[10px] text-[#787b86] font-medium mb-3 uppercase tracking-wider">Strategy Watchdog</div>
          <div className="space-y-2">
            {Object.entries(watchdog).map(([s, state]: [string, any]) => (
              <div key={s} className="flex justify-between text-xs">
                <span className="text-[#787b86]">{s.replace(/_/g, ' ')}</span>
                <span className={stateColor(state)}>● {state}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ML */}
        <section>
          <div className="text-[10px] text-[#787b86] font-medium mb-3 uppercase tracking-wider">ML Model</div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-[#787b86]">LightGBM</span>
              <span className={ml.lgbm_loaded ? 'text-[#26a69a]' : 'text-yellow-400'}>{ml.lgbm_loaded ? '✓ Loaded' : '⚠ Not trained yet'}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[#787b86]">River live trades</span>
              <span className="text-[#d1d4dc]">{ml.river_trades ?? 0}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-[#787b86]">Confidence threshold</span>
              <span className="text-[#d1d4dc]">{ml.confidence_threshold ?? 0.55}</span>
            </div>
          </div>
        </section>

      </div>
    </div>
  )
}
