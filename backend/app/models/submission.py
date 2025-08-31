from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
import pytz
from app.db.base_class import Base

class Submission(Base):
    """用户代码提交记录模型
    
    用于存储用户每次提交的代码，包括HTML、CSS、JavaScript部分。
    
    Attributes:
        id: 自增ID
        participant_id: 关联到 participants.id
        topic_id: 知识点ID
        html_code: 提交的HTML代码
        css_code: 提交的CSS代码
        js_code: 提交的JavaScript代码
        submitted_at: 提交时间
    """
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String, index=True, nullable=False)
    topic_id = Column(String, index=True, nullable=False)
    html_code = Column(Text, nullable=True)
    css_code = Column(Text, nullable=True)
    js_code = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')))