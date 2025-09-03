#!/usr/bin/env python3
"""
数据库初始化脚本

这个脚本用于创建所有数据库表。
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 确保在导入任何其他模块之前加载环境变量
from dotenv import load_dotenv
env_path = os.path.join(project_root, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # 如果没有.env文件，尝试使用.env.example
    env_example_path = os.path.join(project_root, '.env.example')
    if os.path.exists(env_example_path):
        load_dotenv(env_example_path)

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base
from app.core.config import settings

# 导入所有模型，确保它们被正确注册
from app.models.participant import Participant
from app.models.event import EventLog
from app.models.chat_history import ChatHistory
from app.models.user_progress import UserProgress
from app.models.survey_result import SurveyResult
from app.models.submission import Submission

def init_db():
    """初始化数据库，创建所有表"""
    print(f"Using database URL: {settings.DATABASE_URL}")
    # 创建数据库引擎
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功！")

    # 简易迁移：为 chat_history 表添加 raw_context_to_llm 列（若不存在）
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'chat_history' in tables:
            columns = [col['name'] for col in inspector.get_columns('chat_history')]
            if 'raw_context_to_llm' not in columns:
                with engine.connect() as conn:
                    # SQLite / Postgres 兼容的简单添加（类型TEXT）
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN raw_context_to_llm TEXT"))
                    conn.commit()
                print("迁移: 已为 chat_history 添加列 raw_context_to_llm")
    except Exception as e:
        print(f"迁移检查/执行失败（可忽略或手动处理）: {e}")

if __name__ == "__main__":
    init_db()
