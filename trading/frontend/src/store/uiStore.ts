import { create } from 'zustand'

interface UIStore {
  activeTab: string
  agentLogOpen: boolean
  setTab: (t: string) => void
  toggleAgentLog: () => void
}

export const useUIStore = create<UIStore>((set) => ({
  activeTab: 'chart',
  agentLogOpen: true,
  setTab: (t) => set({ activeTab: t }),
  toggleAgentLog: () => set((s) => ({ agentLogOpen: !s.agentLogOpen })),
}))
