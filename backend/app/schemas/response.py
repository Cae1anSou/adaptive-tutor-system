# backend/app/schemas/response.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')
class StandardResponse(BaseModel, Generic[T]):
    """标准响应模型
    
    统一的API响应格式，包含状态码、消息和数据载荷。
    
    Attributes:
        code: 状态码，默认200表示成功
        message: 响应消息，默认'success'表示成功
        data: 数据载荷，泛型类型，可选字段
    """
    code: int = 200
    message: str = 'success'
    data: Optional[T]