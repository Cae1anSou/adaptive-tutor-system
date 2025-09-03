from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CodePayload(BaseModel):
    """代码载荷模型
    
    用于承载用户提交的代码内容，包含HTML、CSS和JavaScript三个部分。
    
    Attributes:
        html: HTML代码内容
        css: CSS样式代码内容
        js: JavaScript脚本代码内容
    """
    html: str = ""
    css: str = ""
    js: str = ""

class TestSubmissionRequest(BaseModel):
    """测试提交请求模型
    
    用于接收用户提交的代码测试请求，包含用户信息和代码内容。
    
    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        topic_id: 知识点ID，用于标识测试对应的知识点
        code: 用户提交的代码内容，包含HTML、CSS、JS三部分
    """
    participant_id: str = Field(..., description="参与者ID")
    topic_id: str = Field(..., description="知识点ID")
    code: CodePayload = Field(..., description="用户提交的代码")

class TestSubmissionResponse(BaseModel):
    """测试提交响应模型
    
    用于返回代码测试结果，包含整体评测结果和详细反馈信息。
    
    Attributes:
        passed: 是否所有检查点都通过，True表示全部通过
        message: 总体评测信息，提供综合性的反馈
        details: 详细的失败反馈列表，包含每个检查点的具体反馈信息
    """
    passed: bool = Field(..., description="是否所有检查点都通过")
    message: str = Field(..., description="总体评测信息")
    details: List[str] = Field(..., description="详细的失败反馈列表")

class TestSubmissionAsyncResponse(BaseModel):
    """异步测试提交响应模型"""
    task_id: str = Field(..., description="异步评测任务的ID")

# 新增的类用于数据库操作
# 接口通用字段
class SubmissionBase(BaseModel):
    """代码提交基础模型
    
    定义代码提交的通用字段，作为其他提交模型的基础类。
    
    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        topic_id: 知识点ID，用于标识特定的学习主题或知识点
        html_code: 提交的HTML代码
        css_code: 提交的CSS代码
        js_code: 提交的JavaScript代码
    """
    participant_id: str
    topic_id: str
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None

# 用于创建接口的输入模型
class SubmissionCreate(SubmissionBase):
    """代码提交创建模型
    
    用于创建新的代码提交记录，继承自SubmissionBase。
    包含所有必要的字段来初始化一个代码提交记录。
    """
    pass

# 用于更新接口的输入模型
class SubmissionUpdate(BaseModel):
    """代码提交更新模型
    
    用于更新现有的代码提交记录。
    """
    html_code: Optional[str] = None
    css_code: Optional[str] = None
    js_code: Optional[str] = None

# 数据库记录返回模型
class SubmissionInDB(SubmissionBase):
    """数据库中的代码提交记录模型
    
    用于从数据库中读取代码提交记录，包含所有字段。
    
    Attributes:
        id: 自增ID
        submitted_at: 提交时间
    """
    id: int
    submitted_at: datetime

    class Config:
        from_attributes = True