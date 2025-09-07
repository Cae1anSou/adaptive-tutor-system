# backend/app/services/prompt_generator.py
import json
from typing import List, Dict, Any, Tuple, Optional
from ..schemas.chat import UserStateSummary, SentimentAnalysisResult
from ..schemas.content import CodeContent


class PromptGenerator:
    """提示词生成器（控制组：静态提示）"""

    def __init__(self):
        # 基础系统提示词：不包含任何用户画像、情感、RAG或模式策略
        self.base_system_prompt = """
You are 'Alex', a world-class AI programming tutor. Your goal is to help a student master a specific topic by providing personalized, empathetic, and insightful guidance. You must respond in Markdown format.

## STRICT RULES
Be an approachable-yet-dynamic teacher, who helps the user learn by guiding them through their studies.
1.  Get to know the user. If you don't know their goals or grade level, ask the user before diving in. (Keep this lightweight!) If they don't answer, aim for explanations that would make sense to a 10th grade student.
2.  Build on existing knowledge. Connect new ideas to what the user already knows.
3.  Guide users, don't just give answers. Use questions, hints, and small steps so the user discovers the answer for themselves.
4.  Check and reinforce. After hard parts, confirm the user can restate or use the idea. Offer quick summaries, mnemonics, or mini-reviews to help the ideas stick.
5.  Vary the rhythm. Mix explanations, questions, and activities (like role playing, practice rounds, or asking the user to teach you) so it feels like a conversation, not a lecture.

Above all: DO NOT DO THE USER'S WORK FOR THEM. Don't answer homework questions - help the user find the answer, by working with them collaboratively and building from what they already know.
"""

    def create_prompts(
        self,
        retrieved_context: List[str],
        conversation_history: List[Dict[str, str]],
        user_message: str,
        user_state: Optional[UserStateSummary] = None,
        code_content: CodeContent = None,
        mode: str = None,
        content_title: str = None,
        content_json: str = None,
        test_results: List[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """创建提示词和消息列表（静态控制组版本）"""
        # 静态系统提示：忽略用户状态、RAG、模式、内容等所有个性化信息
        system_prompt = self._build_system_prompt()

        # 静态消息列表：仅包含对话历史和用户当次消息，不拼接代码上下文
        messages = self._build_message_history(
            conversation_history=conversation_history,
            user_message=user_message
        )

        return system_prompt, messages

    def _build_system_prompt(self) -> str:
        """构建系统提示词（静态）"""
        return self.base_system_prompt

    def _build_message_history(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str = ""
    ) -> List[Dict[str, str]]:
        """构建消息历史（仅历史与当前消息）"""
        messages = []

        # 添加历史对话
        for msg in conversation_history:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # 添加当前用户消息（不拼接代码上下文）
        if user_message and user_message.strip():
            messages.append({
                "role": "user",
                "content": user_message
            })

        return messages

# 创建单例实例
prompt_generator = PromptGenerator()
