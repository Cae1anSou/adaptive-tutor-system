from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, UTC
from . import Base

class UserProgress(Base):
    """用户进度模型
    
    高效地记录和查询用户已完成的知识点。
    
    Attributes:
        id: 自增ID
        participant_id: 关联到 participants.id
        topic_id: 已完成的知识点ID
        completed_at: 完成时间
    """
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String, index=True, nullable=False)
    topic_id = Column(String, index=True, nullable=False)
    completed_at = Column(DateTime, default=datetime.now(UTC))
