#backend/app/api/endpoints/websocket.py
# backend/app/api/endpoints/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket_manager import ws_manager

router = APIRouter()
@router.websocket("/user/{participant_id}")
async def websocket_endpoint(websocket: WebSocket, participant_id: str, token: str = None):
   
    await ws_manager.connect(participant_id, websocket)

    try:
        while True:
            # WebSocket 这里只是保持连接，不接收客户端主动消息,后面没问题了这边可以换成等待ping信息的逻辑
            data = await websocket.receive_text()
           
    except WebSocketDisconnect:
        await ws_manager.disconnect(participant_id)
