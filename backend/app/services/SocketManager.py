from fastapi import WebSocket
from typing import Dict, Union
from pydantic import BaseModel
import time, json, asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.last_activity: Dict[str, float] = {}
        self.heartbeat_interval = 30
        self.timeout = 45

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.last_activity[user_id] = time.time()
        print(f"用户 {user_id} 已连接。当前活跃连接数: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.last_activity:
            del self.last_activity[user_id]
        print(f"用户 {user_id} 已断开连接。当前活跃连接数: {len(self.active_connections)}")

    async def send_json(self, user_id: str, message: Union[dict, BaseModel]):
        """给单个用户发送 JSON 消息"""
        if user_id in self.active_connections:
            ws = self.active_connections[user_id]
            if isinstance(message, BaseModel):
                message = message.dict()
            await ws.send_text(json.dumps(message, default=str))

    async def send_text(self, user_id: str, message: str):
        """兼容原来的纯字符串发送"""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def broadcast(self, message: Union[dict, BaseModel, str]):
        """广播 JSON/str 消息"""
        disconnected_users = []
        if isinstance(message, BaseModel):
            message = message.dict()
        if isinstance(message, dict):
            message = json.dumps(message, default=str)

        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception:
                disconnected_users.append(user_id)

        for user_id in disconnected_users:
            self.disconnect(user_id)

    async def check_heartbeats(self):
        """定期检查心跳，关闭不活跃的连接"""
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            current_time = time.time()
            disconnected_users = []
            for user_id, last_active in self.last_activity.items():
                if current_time - last_active > self.timeout:
                    print(f"用户 {user_id} 心跳超时，强制断开连接")
                    disconnected_users.append(user_id)

            for user_id in disconnected_users:
                if user_id in self.active_connections:
                    try:
                        await self.active_connections[user_id].close()
                    except Exception:
                        pass
                    self.disconnect(user_id)

    def update_activity(self, user_id: str):
        if user_id in self.last_activity:
            self.last_activity[user_id] = time.time()

manager = ConnectionManager()
