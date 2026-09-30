import { useEffect, useRef } from 'react'

/** Subscribe to /ws/dashboard. onEvent gets each parsed event; the socket
 * auto-reconnects with backoff. */
export default function useDashboardSocket(onEvent, enabled = true) {
  const cb = useRef(onEvent)
  cb.current = onEvent

  useEffect(() => {
    if (!enabled) return
    let ws, closed = false, timer
    const connect = () => {
      ws = new WebSocket(`ws://${location.host}/ws/dashboard`)
      ws.onmessage = (e) => cb.current(JSON.parse(e.data))
      ws.onclose = () => { if (!closed) timer = setTimeout(connect, 1500) }
    }
    connect()
    return () => { closed = true; clearTimeout(timer); ws?.close() }
  }, [])
}
