import asyncio
from typing import Dict
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock() # 并发锁

    async def connect(self, participant_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock: # 获取锁
            self.active_connections[participant_id] = websocket

    async def disconnect(self, participant_id: str):
        async with self._lock: # 获取锁
            if participant_id in self.active_connections:
                del self.active_connections[participant_id]

    async def send_to_user(self, participant_id: str, message: str):
        
        if participant_id in self.active_connections:
            websocket = self.active_connections[participant_id]
            await websocket.send_text(message)
ws_manager = WebSocketManager()
