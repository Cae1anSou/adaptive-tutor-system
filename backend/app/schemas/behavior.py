from pydantic import BaseModel, Field
from typing import Dict, Any,Literal, Optional, Union
from datetime import datetime
from enum import Enum

# TODO: 这里的类型可能不对，等恩琪的模块完成之后，需要再改
class EventType(str, Enum):
    """行为事件类型枚举
    
    根据TDD-II-07文档定义，对应前端behavior_tracker.js捕获的所有事件类型
    以及后端生成的事件类型（如state_snapshot）
    """
    CODE_EDIT = "code_edit"
    AI_HELP_REQUEST = "ai_help_request"
    TEST_SUBMISSION = "test_submission"
    DOM_ELEMENT_SELECT = "dom_element_select"
    USER_IDLE = "user_idle"
    CLICK="click"
    KNOWLEDGE_LEVEL_ACCESS = "knowledge_level_access"
    STATE_SNAPSHOT = "state_snapshot"
    PAGE_CLICK="page_click"
    SIGNIFICANT_EDITS = "significant_edits"
    LARGE_ADDITION = "large_addition"
    CODING_PROBLEM = "coding_problem"
    CODING_SESSION_SUMMARY = "coding_session_summary"
    IDLE_HINT_DISPLAYED = "idle_hint_displayed"
    PAGE_FOCUS_CHANGE = "page_focus_change"


class CodeEditCycleData(BaseModel):
    """代码编辑周期数据"""
    editor: str = Field(..., description="编辑器类型")
    edit_type: str = Field(..., description="编辑类型")
    deleted_chars: int = Field(0, description="删除的字符数")
    added_chars: int = Field(0, description="新增的字符数")
    total_modified: int = Field(0, description="总共修改的字符数")
    duration_ms: int = Field(0, description="编辑持续时间（毫秒）")
    consecutive_edits: int = Field(0, description="连续编辑次数")
    timestamp: datetime = Field(..., description="时间戳")
    submitted: Optional[bool] = Field(False, description="是否已提交到后端")

class CodingProblemData(BaseModel):
    """编码问题数据"""
    editor: str = Field(..., description="编辑器类型")
    consecutive_edits: int = Field(..., description="连续编辑次数")
    severity: str = Field(..., description="问题严重程度")
    timestamp: datetime = Field(..., description="时间戳")

class CodingSessionSummaryData(BaseModel):
    """编码会话摘要数据"""
    total_edits: int = Field(0, description="总编辑次数")
    problem_events: int = Field(0, description="问题事件次数")
    session_duration: int = Field(0, description="会话持续时间（秒）")
    avg_edit_size: float = Field(0.0, description="平均编辑规模")
    edits_by_editor: Dict[str, int] = Field(default_factory=dict, description="按编辑器分类的编辑数")
    edits_by_type: Dict[str, int] = Field(default_factory=dict, description="按类型分类的编辑数")

class CodeEditData(BaseModel):
    """代码编辑事件数据
    
    Attributes:
        editor_name: 编辑器名称，如 'html', 'css', 'js'
        new_length: 新的代码长度
    """
    editor_name: str = Field(..., description="编辑器名称")
    new_length: int = Field(..., ge=0, description="新的代码长度")


class AiHelpRequestData(BaseModel):
    """AI帮助请求数据
    
    Attributes:
        message: 用户向AI提问的消息内容
    """
    message: str = Field(..., min_length=1, description="用户向AI提问的消息内容")


class SubmissionData(BaseModel):
    """测试提交数据
    
    Attributes:
        topic_id: 知识点ID
        code: 用户提交的代码内容
    """
    topic_id: str = Field(..., description="知识点ID")
    code: Dict[str, str] = Field(..., description="用户提交的代码内容，包含html、css、js")


class DomElementSelectData(BaseModel):
    """DOM元素选择数据
    
    Attributes:
        tag_name: 选择的DOM元素标签名
        selector: DOM元素选择器
    """
    tag_name: str = Field(..., description="选择的DOM元素标签名")
    selector: str = Field(..., description="DOM元素选择器")


class UserIdleData(BaseModel):
    """用户闲置数据
    
    Attributes:
        duration_ms: 闲置时长（毫秒）
    """
    duration_ms: int = Field(..., gt=0, description="闲置时长（毫秒）")


class KnowledgeLevelAccessData(BaseModel):
    """知识点访问事件数据
    
    Attributes:
        topic_id: 主题ID
        level: 知识点级别
        action: 动作：进入或离开
        duration_ms: 停留时长（毫秒），仅在leave时提供
    """
    topic_id: str = Field(..., description="主题ID")
    level: int = Field(..., description="知识点级别")
    action: Literal["enter", "leave"] = Field(..., description="动作：进入或离开")
    duration_ms: Optional[int] = Field(None, description="停留时长（毫秒），仅在leave时提供")


class StateSnapshotData(BaseModel):
    """状态快照数据
    
    Attributes:
        profile_data: 用户档案数据
    """
    profile_data: Dict[str, Any] = Field(..., description="用户档案数据")


EventDataType = Union[
    CodeEditData,
    AiHelpRequestData,
    SubmissionData,
    DomElementSelectData,
    UserIdleData,
    KnowledgeLevelAccessData,
    StateSnapshotData,
    Dict[str, Any],  # 用于 page_click 等复杂事件
    CodeEditCycleData,
    CodingProblemData,
    CodingSessionSummaryData
    # todo:

]


class BehaviorEvent(BaseModel):
    """
    行为事件模型，对应前端behavior_tracker.js捕获的事件
    
    记录用户在学习过程中的各种交互行为，用于行为分析和学习状态评估。
    
    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        event_type: 事件类型，枚举值
        event_data: 事件数据，根据事件类型有不同的结构
        timestamp: 事件发生的时间戳，可选字段，默认为当前时间
    """

    # 与 TDD-II-07 对齐的事件类型枚举（若将来扩展只需在此添加）TODO：ceq可能添加热力图事件（heatmap_snapshot）
    # 使用已定义的 EventType 枚举类

    participant_id: str = Field(..., description="参与者ID，用于标识特定用户")
    event_type: EventType = Field(..., description="事件类型")
    event_data: Dict[str, Any]  = Field(..., description="事件数据，根据事件类型有不同的结构")
    timestamp: Optional[datetime] = Field(None, description="事件发生的时间戳，可选字段，默认为当前时间")

    
    class Config:
        orm_mode = True