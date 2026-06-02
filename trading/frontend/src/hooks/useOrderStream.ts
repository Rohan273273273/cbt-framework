import { useEffect } from 'react'
import { orderWS } from '../api/websocket'
import { useOrderStore } from '../store/orderStore'

export function useOrderStream() {
  const setOrders = useOrderStore(s => s.setOrders)
  const setAccount = useOrderStore(s => s.setAccount)

  useEffect(() => {
    const unsub = orderWS.onMessage((data: any) => {
      if (data.type === 'orders' && Array.isArray(data.orders)) {
        setOrders(data.orders)
      }
      if (data.type === 'account' && data.account) {
        setAccount(data.account)
      }
    })
    return unsub
  }, [setOrders, setAccount])
}
