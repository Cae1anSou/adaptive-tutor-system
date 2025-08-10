# backend/app/schemas/chat.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.schemas.content import CodeContent, TestTask


class ConversationMessage(BaseModel):
    """对话消息模型"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """聊天请求模型"""
    participant_id: str
    user_message: str
    conversation_history: Optional[List[ConversationMessage]] = []
    code_context: Optional[CodeContent] = None
    task_context: Optional[TestTask] = None
    topic_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    ai_response: str
    user_state_summary: Optional[Dict[str, Any]] = None
    retrieved_context: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    timestamp: datetime = datetime.now(timezone.utc)


class SentimentAnalysisResult(BaseModel):
    """情感分析结果模型"""
    label: str  # "NEUTRAL", "CONFUSED", "FRUSTRATED", "EXCITED", etc.
    confidence: float
    details: Optional[Dict[str, Any]] = None


class UserStateSummary(BaseModel):
    """用户状态摘要模型"""
    participant_id: str
    emotion_state: Dict[str, Any]
    behavior_counters: Dict[str, Any]
    bkt_models: Dict[str, Any]
    is_new_user: bool
    last_updated: datetime = datetime.now(timezone.utc)


class ChatHistoryCreate(BaseModel):
    """创建聊天历史记录模型"""
    participant_id: str
    user_message: str
    ai_response: str
    conversation_context: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """聊天历史记录响应模型"""
    id: int
    participant_id: str
    timestamp: datetime
    user_message: str
    ai_response: str
    conversation_context: Optional[str] = None