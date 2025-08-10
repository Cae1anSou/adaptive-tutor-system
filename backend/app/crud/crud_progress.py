from typing import List
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.user_progress import UserProgress
from app.schemas.user_progress import UserProgressCreate, UserProgressUpdate

class CRUDProgress(CRUDBase[UserProgress, UserProgressCreate, UserProgressUpdate]):
    @staticmethod
    def get_completed_topics_by_user(db: Session, *, participant_id: str) -> List[str]:
        """
        查询指定用户已完成的 topic_id 列表
        """
        results = db.query(UserProgress.topic_id).filter(
            UserProgress.participant_id == participant_id
        ).all()
        return [row[0] for row in results]


# 实例化并暴露给 API 层使用
progress = CRUDProgress(UserProgress)
