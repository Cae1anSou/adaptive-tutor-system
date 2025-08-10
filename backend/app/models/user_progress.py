from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from . import Base

class UserProgress(Base):
    __tablename__ = "user_progress"
    # TODO:  需要根据后续TDD-II-06完成测试后更新用户学习情况的事件类型，补充字段说明
    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(String, index=True, nullable=False)  # 用户唯一标识
    topic_id = Column(String, index=True, nullable=False)        # 知识点唯一标识
    completed_at = Column(DateTime, default=datetime.utcnow)     # 完成时间，可选字段
