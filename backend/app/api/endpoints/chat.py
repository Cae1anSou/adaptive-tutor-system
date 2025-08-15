from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.dependency_injection import get_db, get_dynamic_controller
from app.schemas.chat import ChatRequest, ChatResponse, ConversationMessage
from app.schemas.response import StandardResponse
from app.services.dynamic_controller import DynamicController
from app.crud.crud_chat_history import chat_history as crud_chat_history

router = APIRouter()


@router.post("/ai/chat", response_model=StandardResponse[ChatResponse])
async def chat_with_ai(
    request: ChatRequest,
    db: Session = Depends(get_db),
    controller: DynamicController = Depends(get_dynamic_controller)
) -> StandardResponse[ChatResponse]:
    """
    与AI进行对话
    
    Args:
        request: 聊天请求
        db: 数据库会话
        controller: 动态控制器
        
    Returns:
        StandardResponse[ChatResponse]: AI回复
    """
    try:
        # 验证请求
        if not request.participant_id:
            raise HTTPException(status_code=400, detail="participant_id is required")
        
        if not request.user_message:
            raise HTTPException(status_code=400, detail="user_message is required")
        
        # 调用生成回复
        response = await controller.generate_adaptive_response(
            request=request,
            db=db
        )
        
        return StandardResponse(
            code=200,
            message="AI response generated successfully",
            data=response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat_with_ai: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/history/{participant_id}", response_model=StandardResponse[list[ConversationMessage]])
async def get_chat_history(
    participant_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
) -> StandardResponse[list[ConversationMessage]]:
    """
    获取指定用户的聊天历史
    
    Args:
        participant_id: 参与者ID（从URL路径获取）
        limit: 返回记录数量限制，默认50条
        db: 数据库会话
        
    Returns:
        StandardResponse[list[ConversationMessage]]: 聊天历史记录
    """
    try:
        # 获取聊天历史记录
        history_records = crud_chat_history.get_by_participant(
            db, 
            participant_id=participant_id, 
            limit=limit
        )
        
        # 转换为ConversationMessage格式
        conversation_messages = []
        for record in reversed(history_records):  # 反转顺序，按时间正序返回
            conversation_messages.append(ConversationMessage(
                role=record.role,
                content=record.message,
                timestamp=record.timestamp
            ))
        
        return StandardResponse(
            code=200,
            message="Chat history retrieved successfully",
            data=conversation_messages
        )
        
    except Exception as e:
        print(f"Error in get_chat_history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )