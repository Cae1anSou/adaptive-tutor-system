from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
import pytz
from app.db.base_class import Base

class ChatHistory(Base):
    """聊天历史模型
    
    专门记录用户与AI的完整对话历史，以及用于生成AI回答的Prompt。
    
    Attributes:
        id: 消息ID
        participant_id: 关联到participants.id
        timestamp: 消息时间
        role: 'user' 或 'ai'
        message: 消息的文本内容
        raw_prompt_to_llm: (仅对AI消息) 记录当时为了生成这条AI回答，我们实际发送给LLM的完整Prompt
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'ai'
    message = Column(Text, nullable=False)
    raw_prompt_to_llm = Column(Text, nullable=True)
