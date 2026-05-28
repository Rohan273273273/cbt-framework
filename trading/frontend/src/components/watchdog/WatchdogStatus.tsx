const STATE_COLORS: Record<string, string> = {
  NORMAL: 'text-[#26a69a]',
  REDUCED: 'text-yellow-400',
  PAUSED: 'text-[#ef5350]',
}

const LABELS: Record<string, string> = {
  volume_profile: 'Vol Profile',
  amd_session: 'AMD',
  liquidity_sweep: 'Liq Sweep',
  order_blocks_fvg: 'Order Block',
}

export default function WatchdogStatus({ states }: { states?: Record<string, string> }) {
  if (!states) return (
    <div className="text-[10px] text-[#787b86]">Watchdog loading...</div>
  )

  return (
    <div>
      <div className="text-[10px] text-[#787b86] font-medium mb-2 uppercase tracking-wider">Watchdog</div>
      {Object.entries(states).map(([strategy, state]) => (
        <div key={strategy} className="flex justify-between items-center py-1">
          <span className="text-[11px] text-[#787b86]">{LABELS[strategy] ?? strategy}</span>
          <span className={`text-[11px] font-medium ${STATE_COLORS[state] ?? 'text-[#787b86]'}`}>
            ● {state}
          </span>
        </div>
      ))}
    </div>
  )
}
