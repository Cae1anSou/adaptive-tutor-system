from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.schemas.response import StandardResponse
from app.schemas.session import SessionInitiateRequest, SessionInitiateResponse
from app.config.dependency_injection import get_user_state_service, get_db, get_redis_client
from app.services.user_state_service import UserStateService

router = APIRouter()


@router.post("/initiate", response_model=StandardResponse[SessionInitiateResponse])
def initiate_session(
        response: Response,
        session_in: SessionInitiateRequest,
        user_state_service: UserStateService = Depends(lambda: get_user_state_service(get_redis_client())),
        db: Session = Depends(get_db)
):
    """
    初始化用户会话
    
    Args:
        response: HTTP响应对象
        session_in: 会话初始化请求数据
        user_state_service: 用户状态服务
        db: 数据库会话
        
    Returns:
        StandardResponse[SessionInitiateResponse]: 会话初始化响应
    """
    # 获取或创建用户配置
    profile, is_new_user = user_state_service.get_or_create_profile(session_in.participant_id, db, session_in.group)

    if is_new_user:
        response.status_code = status.HTTP_201_CREATED

    # 构建响应数据
    response_data = SessionInitiateResponse(
        participant_id=profile.participant_id,
        is_new_user=is_new_user
    )

    # 返回标准成功响应
    return StandardResponse(
        data=response_data
    )
