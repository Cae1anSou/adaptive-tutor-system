# backend/app/services/dynamic_controller.py
import json
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.schemas.chat import ChatRequest, ChatResponse, UserStateSummary, SentimentAnalysisResult
from app.services.user_state_service import UserStateService
from app.services.prompt_generator import PromptGenerator
from app.services.llm_gateway import LLMGateway
from typing import Optional, Any
from app.services.content_loader import load_json_content  # 导入content_loader
from app.crud.crud_event import event as crud_event
from app.crud.crud_chat_history import chat_history as crud_chat_history
from app.schemas.chat import ChatHistoryCreate
from app.schemas.behavior import BehaviorEvent
# 准备事件数据
from app.schemas.behavior import EventType, AiHelpRequestData
from datetime import datetime, UTC


class DynamicController:
    """动态控制器（控制组）：不使用用户画像、RAG或情感分析"""

    def __init__(self,
                 user_state_service: Optional[UserStateService],
                 sentiment_service: Optional[Any],
                 rag_service: Optional[Any],
                 prompt_generator: PromptGenerator,
                 llm_gateway: LLMGateway,):
        """
        初始化动态控制器

        Args:
            user_state_service: 用户状态服务
            sentiment_service: 情感分析服务
            rag_service: RAG服务
            prompt_generator: 提示词生成器
            llm_gateway: LLM网关服务
        """
        # 验证必需的服务（控制组仅要求提示词与LLM网关）
        if prompt_generator is None:
            raise TypeError("prompt_generator cannot be None")
        if llm_gateway is None:
            raise TypeError("llm_gateway cannot be None")
        
        self.user_state_service = user_state_service
        self.sentiment_service = sentiment_service
        self.rag_service = rag_service
        self.prompt_generator = prompt_generator
        self.llm_gateway = llm_gateway

    async def generate_adaptive_response(
        self,
        request: ChatRequest,
        db: Session,
        background_tasks = None
    ) -> ChatResponse:
        """
        生成自适应AI回复的核心流程

        Args:
            request: 聊天请求
            db: 数据库会话
            background_tasks: 后台任务处理器（可选）

        Returns:
            ChatResponse: AI回复
        """
        try:
            # 控制组：不做情感分析、不做RAG、不加载内容
            content_title = None

            # 准备对话历史
            conversation_history_dicts = []
            if request.conversation_history:
                for msg in request.conversation_history:
                    conversation_history_dicts.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            elif request.conversation_history is None:
                conversation_history_dicts = []

            system_prompt, messages = self.prompt_generator.create_prompts(
                user_state=None,
                retrieved_context=[],
                conversation_history=conversation_history_dicts,
                user_message=request.user_message,
                code_content=None,
                mode=None,
                content_title=None,
                content_json=None,
                test_results=None
            )

            # 调用LLM
            ai_response = await self.llm_gateway.get_completion(
                system_prompt=system_prompt,
                messages=messages
            )
            # 构建响应并记录
            response = ChatResponse(ai_response=ai_response)
            self._log_ai_interaction(request, response, db, background_tasks, system_prompt, content_title)
            return response

        except Exception as e:
            print(f"❌ CRITICAL ERROR in generate_adaptive_response: {e}")
            import traceback
            traceback.print_exc()
            # 返回一个标准的、用户友好的错误响应
            # 不包含任何可能泄露内部实现的细节
            return ChatResponse(
                ai_response="I'm sorry, but a critical error occurred on our end. Please notify the research staff."
            )

    @staticmethod
    def _build_user_state_summary(
        profile: Any,
        sentiment_result: SentimentAnalysisResult
    ) -> UserStateSummary:
        """构建用户状态摘要"""
        # StudentProfile 已经包含了所有需要的状态
        # 使用传入的sentiment_result来更新emotion_state
        emotion_state = profile.emotion_state if profile.emotion_state else {}

        # 使用情感分析结果更新emotion_state
        emotion_state["current_sentiment"] = sentiment_result.label
        emotion_state["confidence"] = sentiment_result.confidence
        if sentiment_result.details:
            emotion_state["details"] = sentiment_result.details
        elif "details" not in emotion_state:
            emotion_state["details"] = {}

        # 更新传入的profile对象中的情感状态
        # 修复：确保在profile.emotion_state为None时不会出错
        if hasattr(profile, 'emotion_state') and profile.emotion_state is not None:
            profile.emotion_state.update(emotion_state)
        elif hasattr(profile, 'emotion_state') and profile.emotion_state is None:
            # 如果emotion_state为None，创建一个新的字典
            profile.emotion_state = emotion_state

        # behavior_patterns 替代了 behavior_counters
        behavior_counters = profile.behavior_patterns if hasattr(profile, 'behavior_patterns') else {}
        
        return UserStateSummary(
            participant_id=profile.participant_id,
            emotion_state=emotion_state,
            behavior_counters=behavior_counters,
            behavior_patterns=behavior_counters,
            bkt_models=profile.bkt_model,
            is_new_user=profile.is_new_user,
        )

    def _log_ai_interaction(
        self,
        request: ChatRequest,
        response: ChatResponse,
        db: Session,
        background_tasks: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        content_title: Optional[str] = None
    ):
        """
        根据TDD-I规范，异步记录AI交互。
        1. 在 event_logs 中记录一个 "ai_chat" 事件。
        2. 在 chat_history 中记录用户和AI的完整消息。
        3. 更新用户状态中的提问计数器。
        """
        try:
            # 准备事件数据（控制组：不更新用户画像，仅写事件与聊天记录）
            event = BehaviorEvent(
                participant_id=request.participant_id,
                event_type=EventType.AI_HELP_REQUEST,
                event_data=AiHelpRequestData(message=request.user_message).model_dump(),
                # TODO：这里的时区需要改成上海
                timestamp=datetime.now(UTC)
            )

            # 准备用户聊天记录
            user_chat = ChatHistoryCreate(
                participant_id=request.participant_id,
                role="user",
                message=request.user_message
            )

            # 准备AI聊天记录
            usage = getattr(self.llm_gateway, 'last_usage', None)
            ai_chat = ChatHistoryCreate(
                participant_id=request.participant_id,
                role="assistant",
                message=response.ai_response,
                raw_prompt_to_llm=system_prompt,
                prompt_tokens=(usage or {}).get('prompt_tokens') if usage else None,
                completion_tokens=(usage or {}).get('completion_tokens') if usage else None,
                total_tokens=(usage or {}).get('total_tokens') if usage else None,
            )

            # 检查是否在Celery Worker环境中运行（background_tasks为None）
            if background_tasks is None:
                # 在Celery Worker中，将数据库写入操作作为独立任务分派到db_writer_queue
                from app.celery_app import celery_app
                
                # 分派事件记录任务
                celery_app.send_task(
                    'app.tasks.db_tasks.log_ai_event_task',
                    args=[event.model_dump()], 
                    queue='db_writer_queue'
                )
                
                # 分派用户消息记录任务
                celery_app.send_task(
                    'app.tasks.db_tasks.save_chat_message_task',
                    args=[user_chat.model_dump()], 
                    queue='db_writer_queue'
                )
                
                # 分派AI消息记录任务
                celery_app.send_task(
                    'app.tasks.db_tasks.save_chat_message_task',
                    args=[ai_chat.model_dump()], 
                    queue='db_writer_queue'
                )
                
                print(f"INFO: AI interaction for {request.participant_id} queued for async DB write.")
            else:
                # 在FastAPI应用中，使用FastAPI的BackgroundTasks进行异步处理
                background_tasks.add_task(crud_event.create_from_behavior, db=db, obj_in=event)
                background_tasks.add_task(crud_chat_history.create, db=db, obj_in=user_chat)
                background_tasks.add_task(crud_chat_history.create, db=db, obj_in=ai_chat)
                print(f"INFO: AI interaction for {request.participant_id} logged asynchronously via FastAPI.")

        except Exception as e:
            # 数据保存失败必须报错，科研数据完整性优先
            raise RuntimeError(f"Failed to log AI interaction for {request.participant_id}: {e}")

    def generate_adaptive_response_sync(
        self,
        request: ChatRequest,
        db: Session,
        background_tasks = None
    ) -> ChatResponse:
        """
        同步生成自适应AI回复的核心流程（供Celery任务使用）
        Args:
            request: 聊天请求
            db: 数据库会话
            background_tasks: 后台任务处理器（可选）
        Returns:
            ChatResponse: AI回复
        """
        try:
            content_title = None

            # 准备对话历史
            conversation_history_dicts = []
            if request.conversation_history:
                for msg in request.conversation_history:
                    conversation_history_dicts.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            elif request.conversation_history is None:
                conversation_history_dicts = []

            system_prompt, messages = self.prompt_generator.create_prompts(
                user_state=None,
                retrieved_context=[],
                conversation_history=conversation_history_dicts,
                user_message=request.user_message,
                code_content=None,
                mode=None,
                content_title=None,
                content_json=None,
                test_results=None
            )

            # 调用LLM（同步方式）
            ai_response = self.llm_gateway.get_completion_sync(
                system_prompt=system_prompt,
                messages=messages
            )
            response = ChatResponse(ai_response=ai_response)
            self._log_ai_interaction(request, response, db, background_tasks, system_prompt, content_title)
            return response
        except Exception as e:
            print(f"❌ CRITICAL ERROR in generate_adaptive_response_sync: {e}")
            import traceback
            traceback.print_exc()
            # 返回一个标准的、用户友好的错误响应
            # 不包含任何可能泄露内部实现的细节
            return ChatResponse(
                ai_response="I'm sorry, but a critical error occurred on our end. Please notify the research staff."
            )
