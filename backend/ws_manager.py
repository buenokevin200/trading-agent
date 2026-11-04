"""WebSocket connection manager for real-time trading dashboard updates."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, payload: Any) -> None:
        message = json.dumps(
            {
                "type": event_type,
                "data": payload,
            },
            default=str,
        )
        stale: List[WebSocket] = []
        async with self._lock:
            connections = list(self.active_connections)

        for conn in connections:
            try:
                await conn.send_text(message)
            except Exception:
                stale.append(conn)

        if stale:
            async with self._lock:
                for s in stale:
                    if s in self.active_connections:
                        self.active_connections.remove(s)
