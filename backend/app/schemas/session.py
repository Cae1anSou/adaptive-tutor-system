from pydantic import BaseModel, Field

class SessionInitiateRequest(BaseModel):
    """会话初始化请求模型
    
    用于初始化用户会话，包含参与者ID和分组信息。
    
    Attributes:
        participant_id: 参与者唯一标识符（UUID格式）
        group: 实验分组，默认为'experimental'实验组
    """
    participant_id: str = Field(..., description="System-generated unique ID (UUID) for the participant")
    group: str = Field("experimental", description="Assigned experiment group")

class SessionInitiateResponse(BaseModel):
    """会话初始化响应模型
    
    返回会话初始化结果，包含参与者ID和新用户状态。
    
    Attributes:
        participant_id: 参与者唯一标识符（UUID格式）
        is_new_user: 是否为新用户，用于判断是否需要显示引导内容
    """
    participant_id: str = Field(..., description="System-generated unique ID (UUID) for the participant")
    is_new_user: bool