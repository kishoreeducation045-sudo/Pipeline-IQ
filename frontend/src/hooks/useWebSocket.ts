import { useEffect, useRef, useCallback } from "react";

export function useWebSocket(onMessage: (data: Record<string, unknown>) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const stableCallback = useCallback(onMessage, []);

  useEffect(() => {
    const base = ((import.meta.env.VITE_API_BASE as string) ?? "http://localhost:8000")
      .replace("http://", "ws://")
      .replace("https://", "wss://");

    let ws: WebSocket;
    let retryTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        ws = new WebSocket(`${base}/ws/live`);
        ws.onopen = () => console.log("[WS] Connected to PipelineIQ live stream");
        ws.onmessage = (e) => {
          try { stableCallback(JSON.parse(e.data)); } catch { /* ignore */ }
        };
        ws.onclose = () => {
          retryTimeout = setTimeout(connect, 3000);
        };
        wsRef.current = ws;
      } catch {
        retryTimeout = setTimeout(connect, 3000);
      }
    };

    connect();
    return () => {
      clearTimeout(retryTimeout);
      ws?.close();
    };
  }, [stableCallback]);
}
