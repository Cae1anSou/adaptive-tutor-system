from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from typing import Generator

# 导入统一的 Base 和所有模型
from app.models import Base
from app.models.user_progress import UserProgress
from app.models.event import EventLog
from app.models.bkt import BKTModel
from app.models.chat_history import ChatHistory

# 创建数据库引擎
# connect_args 是SQLite特有的，用于允许多线程访问
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# 创建所有表
Base.metadata.create_all(bind=engine)

# 创建一个Session工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI 依赖项，用于在每个请求中获取数据库会话
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
