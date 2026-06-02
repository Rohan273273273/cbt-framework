import { useOrderStore } from '../../store/orderStore'

export default function OrdersPanel() {
  const { orders, account } = useOrderStore()

  return (
    <div className="p-3 overflow-y-auto flex-1">
      <div className="text-[10px] text-[#787b86] font-medium mb-2 uppercase tracking-wider">Open Orders</div>
      {orders.length === 0 && (
        <div className="text-xs text-[#787b86]">No open orders</div>
      )}
      {orders.map(o => (
        <div key={o.id} className="mb-2 pb-2 border-b border-[#2a2f3a]">
          <div className="flex justify-between mb-0.5">
            <span className="text-xs font-medium text-[#d1d4dc]">{o.symbol.replace('USD', '/USD')}</span>
            <span className={`text-xs font-medium ${o.side === 'buy' ? 'text-[#26a69a]' : 'text-[#ef5350]'}`}>
              {o.side.toUpperCase()}
            </span>
          </div>
          <div className="flex justify-between text-[10px] text-[#787b86]">
            <span>qty: {o.qty}</span>
            <span className={`px-1 rounded text-[10px] ${
              o.status === 'filled' ? 'text-[#26a69a]' :
              o.status === 'new' ? 'text-yellow-400' : 'text-[#787b86]'
            }`}>{o.status}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
