from app.services.SocketManager import socket_manager
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.services.SocketManager import manager

router = APIRouter()

@router.websocket("/{user_id}")
async def chat__endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)