from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.config.dependency_injection import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import StandardResponse
from app.tasks.chat_tasks import process_chat_request
from app.celery_app import celery_app

router = APIRouter()


@router.post("/ai/chat", response_model=StandardResponse[ChatResponse])
async def chat_with_ai(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> StandardResponse[ChatResponse]:
    """
    与AI进行对话 (保持原有端点以确保向后兼容)
    
    Args:
        request: 聊天请求
        background_tasks: 后台任务处理器
        db: 数据库会话
        
    Returns:
        StandardResponse[ChatResponse]: AI回复
    """
    try:
        # 验证请求
        if not request.participant_id:
            raise HTTPException(status_code=400, detail="participant_id is required")
        
        if not request.user_message:
            raise HTTPException(status_code=400, detail="user_message is required")
        
        # 直接调用controller处理（保持原有逻辑）
        from app.config.dependency_injection import get_dynamic_controller
        controller = get_dynamic_controller()
        
        # 调用生成回复
        response = await controller.generate_adaptive_response(
            request=request,
            db=db,
            background_tasks=background_tasks
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


@router.post("/ai/chat2", response_model=StandardResponse[dict])
async def chat_with_ai2(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> StandardResponse[dict]:
    """
    与AI进行异步对话 (新端点，使用Celery任务队列)
    
    Args:
        request: 聊天请求
        background_tasks: 后台任务处理器（保留以确保兼容性，但实际任务已委托给Celery）
        db: 数据库会话（保留以确保兼容性，但实际任务已委托给Celery）
        
    Returns:
        StandardResponse[dict]: 包含任务ID的响应
    """
    # 验证请求
    if not request.participant_id:
        raise HTTPException(status_code=400, detail="participant_id is required")
    
    if not request.user_message:
        raise HTTPException(status_code=400, detail="user_message is required")
    
    # 将任务分派到 Celery 队列
    task = process_chat_request.apply_async(
        args=[request.dict()], 
        queue='chat_queue'
    )
    
    # 立即返回任务ID
    return StandardResponse(
        code=202,
        message="Task submitted successfully",
        data={"task_id": task.id}
    )


@router.get("/ai/chat2/result/{task_id}", response_model=StandardResponse[ChatResponse])
def get_chat_result(task_id: str) -> StandardResponse[ChatResponse]:
    """
    获取异步聊天任务的结果。
    
    Args:
        task_id: 异步任务的ID
        
    Returns:
        StandardResponse[ChatResponse]: AI回复结果
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    if not task_result.ready():
        raise HTTPException(status_code=202, detail={"status": task_result.status})
    
    result = task_result.get()
    if task_result.failed():
        raise HTTPException(status_code=500, detail=str(result))
        
    return StandardResponse(data=result)