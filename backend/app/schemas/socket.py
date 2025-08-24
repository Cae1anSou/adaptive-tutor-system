# from pydantic import BaseModel
# from typing import Optional, Dict, Any
# from datetime import datetime


# class ConnectionData(BaseModel):
#     """连接数据模型

#     WebSocket连接建立时传递的数据。

#     Attributes:
#         participant_id: 参与者ID
#         session_id: 会话ID
#         token: 认证令牌
#     """
#     participant_id: str
#     session_id: str
#     token: str


# class ConnectionAck(BaseModel):
#     """连接确认模型

#     WebSocket连接建立后的确认消息。

#     Attributes:
#         status: 连接状态
#         message: 状态消息
#         timestamp: 时间戳
#     """
#     status: str
#     message: str
#     timestamp: datetime = None


# class DisconnectionData(BaseModel):
#     """断开连接数据模型

#     WebSocket连接断开时传递的数据。

#     Attributes:
#         participant_id: 参与者ID
#         reason: 断开原因
#         timestamp: 时间戳
#     """
#     participant_id: str
#     reason: Optional[str] = None
#     timestamp: datetime = None