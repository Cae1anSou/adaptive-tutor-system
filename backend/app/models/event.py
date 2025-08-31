from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
import pytz
from app.db.base_class import Base

class EventLog(Base):
    """事件日志模型
    
    记录所有由前端发送的、结构化的原始行为痕迹。
    
    Attributes:
        id: 事件唯一ID
        participant_id: 关联到participants.id
        timestamp: 事件发生的精确时间
        event_type: 事件类型，如 `code_edit`, `ai_chat`, `submit_test`
        event_data: 包含事件所有细节的JSON对象
    """
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')), nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSON)
