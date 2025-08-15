from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from app.schemas.content import CodeContent, TestTask


class ConversationMessage(BaseModel):
    """对话消息模型

    对话中的单条消息记录，包含角色、内容和时间戳。

    Attributes:
        role: 消息角色，'user'表示用户消息，'assistant'表示AI助手消息
        content: 消息内容，文本格式的对话内容
        timestamp: 时间戳，记录消息发送时间，可选字段
    """
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """聊天请求模型

    用户发送的聊天请求，包含消息内容和上下文信息。

    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        user_message: 用户消息内容，当前发送的消息文本
        conversation_history: 对话历史，包含之前的所有对话消息
        code_context: 代码上下文，用户当前正在编辑的代码内容
        task_context: 任务上下文，用户当前正在进行的测试任务
        topic_title: 知识点标题，标识当前讨论的知识点
    """
    participant_id: str
    user_message: str
    conversation_history: Optional[List[ConversationMessage]] = []
    code_context: Optional[CodeContent] = None
    task_context: Optional[TestTask] = None
    topic_title: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型

    AI助手的聊天响应，只包含回复内容。

    Attributes:
        ai_response: AI回复内容，助手生成的回复文本
    """
    ai_response: str


class SentimentAnalysisResult(BaseModel):
    """情感分析结果模型

    用户消息的情感分析结果，用于理解用户情绪状态。

    Attributes:
        label: 情感标签，如 'NEUTRAL', 'CONFUSED', 'FRUSTRATED', 'EXCITED' 等
        confidence: 置信度，0到1之间的浮点数，表示情感分析的准确程度
        details: 详细信息，包含情感分析的其他相关数据
    """
    label: str  # "NEUTRAL", "CONFUSED", "FRUSTRATED", "EXCITED", etc.
    confidence: float
    details: Optional[Dict[str, Any]] = None


class UserStateSummary(BaseModel):
    """用户状态摘要模型

    用户学习状态的完整摘要，包含情感、行为和知识掌握情况。

    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        emotion_state: 情感状态，包含用户当前的情绪分析结果
        behavior_counters: 行为计数器，记录用户的各种行为统计
        bkt_models: BKT模型数据，包含贝叶斯知识追踪模型的状态
        is_new_user: 是否为新用户，用于判断是否需要特殊处理
        last_updated: 最后更新时间，记录状态摘要的生成时间
    """
    participant_id: str
    emotion_state: Dict[str, Any]
    behavior_counters: Dict[str, Any]
    bkt_models: Dict[str, Any]
    is_new_user: bool
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatHistoryCreate(BaseModel):
    """聊天历史创建模型

    用于创建新的聊天历史记录的数据结构，对应数据库模型 ChatHistory。

    Attributes:
        participant_id: 参与者ID，用于标识特定用户
        role: 消息角色，'user'表示用户消息，'assistant'表示AI助手消息
        message: 消息内容，文本格式的对话内容
        raw_prompt_to_llm: 发送给LLM的完整Prompt，仅对AI消息有效
        timestamp: 时间戳，记录消息发送时间，默认为当前时间
    """
    participant_id: str
    role: str  # "user" 或 "assistant"
    message: str
    raw_prompt_to_llm: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))