from fastapi import WebSocket
from typing import Dict
import time
class ConnectionManager:
    def __init__(self):
        # 存储用户ID与WebSocket连接的映射
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储用户最后活动时间
        self.last_activity: Dict[str, float] = {}
        # 心跳检测间隔(秒)
        self.heartbeat_interval = 30
        # 超时时间(秒)
        self.timeout = 45

    #websocket.
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

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        disconnected_users = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception:
                disconnected_users.append(user_id)
        
        # 清理已断开的连接
        for user_id in disconnected_users:
            self.disconnect(user_id)

    # async def check_heartbeats(self):
    #     """定期检查心跳，关闭不活跃的连接"""
    #     while True:
    #         await asyncio.sleep(self.heartbeat_interval)
    #         current_time = time.time()
    #         disconnected_users = []
            
    #         for user_id, last_active in self.last_activity.items():
    #             if current_time - last_active > self.timeout:
    #                 print(f"用户 {user_id} 心跳超时，强制断开连接")
    #                 disconnected_users.append(user_id)
            
    #         for user_id in disconnected_users:
    #             if user_id in self.active_connections:
    #                 try:
    #                     await self.active_connections[user_id].close()
    #                 except Exception:
    #                     pass
    #                 self.disconnect(user_id)

    def update_activity(self, user_id: str):
        """更新用户最后活动时间"""
        if user_id in self.last_activity:
            self.last_activity[user_id] = time.time()

manager = ConnectionManager()