/** Auto-reconnecting WebSocket manager. */

type MessageHandler = (data: unknown) => void

export class WSClient {
  private ws: WebSocket | null = null
  private url: string
  private handlers: MessageHandler[] = []
  private reconnectDelay = 1000
  private maxDelay = 30000
  private stopped = false

  constructor(path: string) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    this.url = `${proto}://${location.host}${path}`
  }

  connect(): void {
    if (this.stopped) return
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      this.reconnectDelay = 1000
    }

    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        this.handlers.forEach(h => h(data))
      } catch {
        // non-JSON frame — ignore
      }
    }

    this.ws.onclose = () => {
      if (this.stopped) return
      setTimeout(() => {
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay)
        this.connect()
      }, this.reconnectDelay)
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter(h => h !== handler)
    }
  }

  close(): void {
    this.stopped = true
    this.ws?.close()
  }
}

// Singleton instances
const priceWS = new WSClient('/ws/prices')
const orderWS = new WSClient('/ws/orders')
const agentWS = new WSClient('/ws/agents')

priceWS.connect()
orderWS.connect()
agentWS.connect()

export { priceWS, orderWS, agentWS }
