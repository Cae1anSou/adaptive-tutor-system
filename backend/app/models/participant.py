from sqlalchemy import Column, String, DateTime
from datetime import datetime
import pytz
from app.db.base_class import Base

class Participant(Base):
    """参与者模型
    
    存储每个实验参与者的基本信息。
    
    Attributes:
        id: 系统生成的唯一ID (UUID)
        group: 实验分组，'experimental' 或 'control'
        created_at: 记录创建时间
    """
    __tablename__ = "participants"
    
    id = Column(String, primary_key=True)
    group = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')))