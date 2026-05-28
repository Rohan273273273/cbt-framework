import { create } from 'zustand'

interface Candle { ts: string; open: number; high: number; low: number; close: number; volume: number }
interface MarketStore {
  symbol: string
  timeframe: string
  candles: Candle[]
  prices: Record<string, number | string>
  setSymbol: (s: string) => void
  setTimeframe: (tf: string) => void
  setCandles: (c: Candle[]) => void
  setPrice: (symbol: string, price: number) => void
}

export const useMarketStore = create<MarketStore>((set) => ({
  symbol: 'BTC/USD',
  timeframe: '1h',
  candles: [],
  prices: {},
  setSymbol: (s) => set({ symbol: s }),
  setTimeframe: (tf) => set({ timeframe: tf }),
  setCandles: (c) => set({ candles: c }),
  setPrice: (symbol, price) => set((s) => ({ prices: { ...s.prices, [symbol]: price } })),
}))
