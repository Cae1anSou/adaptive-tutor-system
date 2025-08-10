from pydantic import BaseModel, Field
from typing import Dict, Any, List

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
