import { useEffect, useRef } from "react";

export function useWebSocket(onMessage: (data: Record<string, unknown>) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    const base = (import.meta.env.VITE_API_BASE ?? "http://localhost:8000")
      .replace("http://", "ws://")
      .replace("https://", "wss://");
    const ws = new WebSocket(`${base}/ws/live`);
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch { /* ignore malformed */ }
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [onMessage]);
}
