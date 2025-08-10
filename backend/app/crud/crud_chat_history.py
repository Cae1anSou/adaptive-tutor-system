# backend/app/crud/crud_chat_history.py
from sqlalchemy.orm import Session
from app.models.chat_history import ChatHistory
from app.schemas.chat import ChatHistoryCreate


def create_chat_history(db: Session, *, obj_in: ChatHistoryCreate) -> ChatHistory:
    """
    创建新的聊天历史记录。
    """
    db_obj = ChatHistory(
        participant_id=obj_in.participant_id,
        user_message=obj_in.user_message,
        ai_response=obj_in.ai_response,
        conversation_context=obj_in.conversation_context,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 将其组织到一个对象中以便于导入
class CRUDChatHistory:
    def create(self, db: Session, *, obj_in: ChatHistoryCreate) -> ChatHistory:
        return create_chat_history(db, obj_in=obj_in)

chat_history = CRUDChatHistory()
