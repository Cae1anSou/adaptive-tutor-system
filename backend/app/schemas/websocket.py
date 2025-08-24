from pydantic import BaseModel, Field
from typing import Optional
class WebSocketMessage(BaseModel):
    type: str = Field(..., description="消息类型")
    data: Optional[dict] = Field(None, description="消息数据")