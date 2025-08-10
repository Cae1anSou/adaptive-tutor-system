from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class BehaviorEvent(BaseModel):
    """
    行为事件模型，对应前端behavior_tracker.js捕获的事件
    
    记录用户在学习过程中的各种交互行为，用于行为分析和学习状态评估。
    
    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        event_type: 事件类型，如 'click', 'scroll', 'code_change' 等
        event_data: 事件数据，包含事件相关的详细信息，字典格式
        timestamp: 事件发生的时间戳，可选字段，默认为当前时间
    """
    # TODO: cxz 需要根据TDD-II-07中的事件类型定义，补充字段说明和验证规则
    participant_id: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp: Optional[datetime] = None
    
    model_config = {"from_attributes": True}