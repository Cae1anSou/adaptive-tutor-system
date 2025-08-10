from sqlalchemy.orm import Session
from app.models.chat_history import ChatHistory
from app.schemas.chat import ChatHistoryCreate


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

# 将其组织到一个对象中以便于导入
class CRUDChatHistory:
    @staticmethod
    def create(db: Session, *, obj_in: ChatHistoryCreate) -> ChatHistory:
        return create_chat_history(db, obj_in=obj_in)

chat_history = CRUDChatHistory()
