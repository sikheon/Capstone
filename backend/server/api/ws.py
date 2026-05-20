import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class EventBus:
    """Fan-out async pub/sub for dashboard updates."""

    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=128)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def publish(self, event: str, payload: dict) -> None:
        msg = {"event": event, "payload": payload}
        for q in list(self._subs):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass


def make_router(bus: EventBus) -> APIRouter:
    router = APIRouter()

    @router.websocket("/events")
    async def events(ws: WebSocket):
        await ws.accept()
        q = bus.subscribe()
        try:
            while True:
                msg = await q.get()
                await ws.send_text(json.dumps(msg))
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(q)

    return router
