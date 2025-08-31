from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
import pytz
from app.db.base_class import Base

class SurveyResult(Base):
    """问卷结果模型
    
    存储用户提交的所有问卷结果。
    
    Attributes:
        id: 提交记录ID
        participant_id: 关联到participants.id
        survey_type: 问卷类型, 如 'pre-test', 'post-test', 'nasa-tlx'
        answers: 存储用户提交的完整答案的JSON对象
        submitted_at: 提交时间
    """
    __tablename__ = "survey_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String, nullable=False)
    survey_type = Column(String, nullable=False)
    answers = Column(JSON, nullable=False)
    submitted_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')))