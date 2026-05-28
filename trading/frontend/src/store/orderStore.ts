import { create } from 'zustand'

interface Order {
  id: string; symbol: string; side: string; qty: number
  status: string; created_at: string
}
interface AccountInfo { equity: number; cash: number; daily_pnl: number }

interface OrderStore {
  orders: Order[]
  account: AccountInfo | null
  setOrders: (o: Order[]) => void
  setAccount: (a: AccountInfo) => void
}

export const useOrderStore = create<OrderStore>((set) => ({
  orders: [],
  account: null,
  setOrders: (o) => set({ orders: o }),
  setAccount: (a) => set({ account: a }),
}))
