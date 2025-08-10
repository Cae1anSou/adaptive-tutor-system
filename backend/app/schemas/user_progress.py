from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# 接口通用字段
class UserProgressBase(BaseModel):
    """用户学习进度基础模型
    
    定义用户学习进度的通用字段，作为其他进度模型的基础类。
    
    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        topic_id: 知识点ID，用于标识特定的学习主题或知识点
    """
    participant_id: str
    topic_id: str

# 用于创建接口的输入模型
class UserProgressCreate(UserProgressBase):
    """用户学习进度创建模型
    
    用于创建新的学习进度记录，继承自UserProgressBase。
    包含所有必要的字段来初始化一个学习进度记录。
    """
    pass

# 用于更新接口的输入模型
class UserProgressUpdate(BaseModel):
    """用户学习进度更新模型
    
    用于更新现有的学习进度记录，主要包含完成时间等可更新字段。
    
    Attributes:
        completed_at: 完成时间，记录用户完成该知识点的具体时间
    """
    completed_at: Optional[datetime]

# 用于返回用户已完成的知识点ID列表
class UserProgressResponse(BaseModel):
    """用户学习进度响应模型
    
    用于返回用户已完成的所有知识点列表。
    
    Attributes:
        completed_topics: 已完成的知识点ID列表
    """
    completed_topics: list[str]
