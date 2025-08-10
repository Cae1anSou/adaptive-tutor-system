from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.dependency_injection import get_db, get_dynamic_controller
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import StandardResponse
from app.services.dynamic_controller import DynamicController

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
        
        # 获取动态控制器实例并调用生成回复
        controller = get_dynamic_controller()
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