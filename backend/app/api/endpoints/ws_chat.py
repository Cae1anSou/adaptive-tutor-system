from fastapi import APIRouter, WebSocket, WebSocketDisconnect,Depends
import json
import asyncio
from app.services.llm_gateway import llm_gateway
from sqlalchemy.orm import Session
from app.config.dependency_injection import get_db
from app.services.SocketManager import manager

router = APIRouter()

@router.websocket("/{user_id}")
async def chat__endpoint(websocket: WebSocket, user_id: str, db: Session = Depends(get_db)):
    async def handle_chat(message_data: str,websocket: WebSocket):#TODO:类型要改
        """处理 LLM 流式消息"""
        ...
        # 流式发送开始信号
        start_response = {
            "sender": "AI",
            "message": "",
            "type": "stream_start"
        }
        await websocket.send_text(json.dumps(start_response))
        # 调用LLM服务获取流式响应
        async for chunk in llm_gateway.get_stream_completion(
            system_prompt="You are a helpful AI programming tutor.",
            messages=[{"role": "user", "content": message_data}]
        ):
            # 构建流式响应消息
            stream_response = {
                "sender": "AI",
                "message": chunk,
                "type": "stream"
            }
            await websocket.send_text(json.dumps(stream_response))
            # 添加延迟以控制流式输出速度，避免生成过快
            #await asyncio.sleep(0.05)  # 50ms延迟，可以根据需要调整
        
        # 流式发送结束信号
        end_response = {
            "sender": "AI",
            "message": "",
            "type": "stream_end"
        }
        await websocket.send_text(json.dumps(end_response))

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            manager.update_activity(user_id)
            print(f"收到用户 {user_id} 的消息: {data}")
            print(f"使用的socket: {websocket}")
            # 解析前端发送的JSON数据
            try:
                message_data = json.loads(data)
                
                # 处理心跳消息
                # if message_data.get("type") == "ping":
                #     pong_response = {
                #         "type": "pong",
                #         "timestamp": message_data.get("timestamp")
                #     }
                #     await websocket.send_text(json.dumps(pong_response))
                #     continue
                
                # 处理普通消息
                sender_id = message_data.get("userId", user_id)
                message = message_data.get("message", "")
                type = message_data.get("type", "")
                '''
                request = ChatRequest(user_message=message.get("user_message", ""),
                                      conversation_history=message_data.get("conversation_history", []),
                                      code_context=message_data.get("code_context", None),
                                      mode=message_data.get("mode", None),
                                      content_id=message_data.get("content_id", None)
                                     )
                response = await DynamicController.generate_adaptive_response(
                    request=request,
                    db=Session=db
                )
                '''
                if(type == "ai_message"):
                    task= asyncio.create_task(handle_chat(message,websocket))
                    task.add_done_callback(lambda t: print(f"Task finished: {t.exception()}"))
                
                
            except json.JSONDecodeError:
                # 如果消息不是JSON格式，直接广播
                response = {
                    "sender": user_id,
                    "message": data,
                    "type": "message"
                }
                #await manager.broadcast(json.dumps(response))
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@router.get("/")
async def root():
    return {"message": "WebSocket Server is running"}
