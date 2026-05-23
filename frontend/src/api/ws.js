export function connectEvents(baseUrl, onEvent) {
  const wsUrl = baseUrl.replace(/^http/, "ws") + "/ws/events";
  let ws;
  let stopped = false;
  let retryMs = 1000;

  function open() {
    ws = new WebSocket(wsUrl);
    ws.onopen = () => { retryMs = 1000; };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        onEvent(msg.event, msg.payload);
      } catch {}
    };
    ws.onclose = () => {
      if (stopped) return;
      setTimeout(open, retryMs);
      retryMs = Math.min(retryMs * 2, 15000);
    };
    ws.onerror = () => ws && ws.close();
  }

  open();
  return () => { stopped = true; ws && ws.close(); };
}
