import { useEffect, useRef, useState } from 'react'

export function useAgentLog(maxLines = 200) {
  const [logs, setLogs] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`ws://${window.location.host}/ws/agents`)
      wsRef.current = ws
      ws.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data)
          if (d.type === 'agent_log') {
            setLogs((prev) => [...prev.slice(-maxLines + 1), d.message])
          }
        } catch {}
      }
      ws.onclose = () => setTimeout(connect, 3000)
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  return logs
}
