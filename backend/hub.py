"""Dashboard event bus: broadcasts JSON events to all connected UI clients."""

import json


class Hub:
    def __init__(self):
        self.clients: set = set()

    async def connect(self, ws):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws):
        self.clients.discard(ws)

    async def broadcast(self, event: dict):
        if not self.clients:
            return
        msg = json.dumps(event)
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(msg)
            except Exception:  # noqa: BLE001 - dead client
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


hub = Hub()
