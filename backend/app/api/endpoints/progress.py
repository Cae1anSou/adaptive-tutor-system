from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.dependency_injection import get_db
from app.schemas.response import StandardResponse
from app.schemas.user_progress import UserProgressResponse
from app.crud.crud_progress import progress
import logging

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 确保设置为DEBUG级别

router = APIRouter()

@router.get("/participants/{participant_id}/progress", response_model=StandardResponse[UserProgressResponse])
def get_user_progress(participant_id: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"获取用户进度请求: participant_id={participant_id}")
        print("当前数据库文件:", db.bind.url)
        logger.debug("准备调用 get_completed_topics_by_user 方法")
        completed_topics = progress.get_completed_topics_by_user(
            db, participant_id=participant_id
        )
        logger.debug(f"get_completed_topics_by_user 方法调用完成")
        # 正确包装响应数据，确保符合TDD要求的格式
        response_data = UserProgressResponse(completed_topics=completed_topics)
        logger.info(f"用户 {participant_id} 的完成主题: {completed_topics}")
        logger.info(f"返回数据: {response_data.dict()}")
        return StandardResponse(data=response_data)
    except Exception as e:
        logger.error(f"获取用户进度时出错: participant_id={participant_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")