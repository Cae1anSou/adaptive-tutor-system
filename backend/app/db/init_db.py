#!/usr/bin/env python3
"""
数据库初始化脚本

这个脚本用于创建所有数据库表。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 确保在导入任何其他模块之前加载环境变量
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.core.config import settings

# 导入所有模型，确保它们被正确注册
from app.models.participant import Participant
from app.models.event import EventLog
from app.models.chat_history import ChatHistory
from app.models.user_progress import UserProgress
from app.models.survey_result import SurveyResult

def init_db():
    """初始化数据库，创建所有表"""
    # 创建数据库引擎
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功！")

if __name__ == "__main__":
    init_db()