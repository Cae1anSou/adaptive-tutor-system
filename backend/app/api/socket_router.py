from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.endpoints import ws_chat
#chat -> danamic controller -> llmgateway
import json
import logging 

logger = logging.getLogger(__name__)

# 创建 WebSocket 路由器
ws_router = APIRouter()
ws_router.include_router(ws_chat.router, prefix="/chat", tags=["chat"])