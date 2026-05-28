import { useEffect, useState } from 'react'
import api from '../../api/client'

interface NewsEvent {
  headline: string; source: string; sentiment: string
  confidence: number; impact_score: number; high_impact: boolean
  affected: string[]; timestamp: string
}

export default function NewsFeed({ compact = false }: { compact?: boolean }) {
  const [news, setNews] = useState<NewsEvent[]>([])

  useEffect(() => {
    const fetch = () => api.get('/screener/news').then(r => setNews(r.data)).catch(() => {})
    fetch()
    const id = setInterval(fetch, 30000)
    return () => clearInterval(id)
  }, [])

  const sentColor = (s: string) => s === 'bullish' ? 'text-[#26a69a] bg-[#26a69a]/10' : s === 'bearish' ? 'text-[#ef5350] bg-[#ef5350]/10' : 'text-[#787b86] bg-[#787b86]/10'

  return (
    <div className="p-2 overflow-y-auto h-full">
      <div className="text-[10px] text-[#787b86] font-medium mb-2 uppercase tracking-wider">News</div>
      {news.length === 0 && <div className="text-xs text-[#787b86]">No events</div>}
      {news.map((n, i) => (
        <div key={i} className={`mb-2 pb-2 border-b border-[#2a2f3a] ${n.high_impact ? 'border-l-2 border-l-yellow-500 pl-2' : ''}`}>
          <div className="text-xs text-[#d1d4dc] leading-4 mb-1">{compact ? n.headline.slice(0, 60) + '...' : n.headline}</div>
          <div className="flex items-center gap-1 flex-wrap">
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${sentColor(n.sentiment)}`}>{n.sentiment}</span>
            {n.affected.slice(0, 2).map(s => (
              <span key={s} className="text-[10px] text-[#787b86] bg-[#1e2329] px-1 rounded">{s.replace('/USD','')}</span>
            ))}
            <span className="text-[10px] text-[#787b86] ml-auto">{new Date(n.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
