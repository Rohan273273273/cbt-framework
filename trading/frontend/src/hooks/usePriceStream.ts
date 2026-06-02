import { useEffect } from 'react'
import { priceWS } from '../api/websocket'
import { useMarketStore } from '../store/marketStore'

export function usePriceStream() {
  const setPrice = useMarketStore(s => s.setPrice)
  const setCandles = useMarketStore(s => s.setCandles)

  useEffect(() => {
    const unsub = priceWS.onMessage((data: any) => {
      if (data.type === 'price' && data.symbol && data.price != null) {
        setPrice(data.symbol, data.price)
      }
      if (data.type === 'candles' && Array.isArray(data.candles)) {
        setCandles(data.candles)
      }
    })
    return unsub
  }, [setPrice, setCandles])
}
