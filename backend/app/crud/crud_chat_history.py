from sqlalchemy.orm import Session
from app.models.chat_history import ChatHistory
from app.schemas.chat import ChatHistoryCreate
from typing import List


def create_chat_history(db: Session, *, obj_in: ChatHistoryCreate) -> ChatHistory:
    """
    创建新的聊天历史记录。
    """
    db_obj = ChatHistory(
        participant_id=obj_in.participant_id,
        role=obj_in.role,
        message=obj_in.message,
        raw_prompt_to_llm=obj_in.raw_prompt_to_llm,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_chat_history_by_participant(db: Session, *, participant_id: str, limit: int = 50) -> List[ChatHistory]:
    """
    获取指定参与者的聊天历史记录。
    
    Args:
        db: 数据库会话
        participant_id: 参与者ID
        limit: 返回记录数量限制，默认50条
        
    Returns:
        List[ChatHistory]: 聊天历史记录列表，按时间戳倒序排列
    """
    return db.query(ChatHistory)\
        .filter(ChatHistory.participant_id == participant_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(limit)\
        .all()


# 将其组织到一个对象中以便于导入
class CRUDChatHistory:
    @staticmethod
    def create(db: Session, *, obj_in: ChatHistoryCreate) -> ChatHistory:
        return create_chat_history(db, obj_in=obj_in)
    
    @staticmethod
    def get_by_participant(db: Session, *, participant_id: str, limit: int = 50) -> List[ChatHistory]:
        return get_chat_history_by_participant(db, participant_id=participant_id, limit=limit)

chat_history = CRUDChatHistory()
