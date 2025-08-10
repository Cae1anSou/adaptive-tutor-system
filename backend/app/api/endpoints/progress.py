from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.dependency_injection import get_db
from app.schemas.response import StandardResponse
from app.schemas.user_progress import UserProgressResponse
from app.crud.crud_progress import progress

router = APIRouter()

@router.get("/participants/{participant_id}/progress", response_model=StandardResponse[UserProgressResponse])
def get_user_progress(participant_id: str, db: Session = Depends(get_db)):
    try:
        completed_topics = progress.get_completed_topics_by_user(
            db, participant_id=participant_id
        )
        # 正确包装响应数据，确保符合TDD要求的格式
        response_data = UserProgressResponse(completed_topics=completed_topics)
        return StandardResponse(data=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
