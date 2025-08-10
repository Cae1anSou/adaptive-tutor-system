#!/usr/bin/env python3
"""
测试数据库连接和基本操作
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保在导入任何其他模块之前加载环境变量
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.db.base_class import Base
from app.models.participant import Participant

def test_db_connection():
    """测试数据库连接"""
    try:
        # 创建会话
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # 测试创建一个参与者
        participant = Participant(
            id="test_user_001",
            group="experimental"
        )
        
        db.add(participant)
        db.commit()
        db.refresh(participant)
        
        print(f"成功创建参与者: {participant.id}")
        
        # 查询参与者
        retrieved_participant = db.query(Participant).filter(Participant.id == "test_user_001").first()
        print(f"成功查询参与者: {retrieved_participant.id}, 分组: {retrieved_participant.group}")
        
        # 清理测试数据
        db.delete(participant)
        db.commit()
        
        print("数据库连接测试成功！")
        
    except Exception as e:
        print(f"数据库连接测试失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db_connection()