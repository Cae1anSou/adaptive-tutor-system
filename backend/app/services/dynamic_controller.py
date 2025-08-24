# backend/app/services/dynamic_controller.py
import json
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.schemas.chat import ChatRequest, ChatResponse, UserStateSummary, SentimentAnalysisResult
from app.services.sentiment_analysis_service import SentimentAnalysisService
from app.services.user_state_service import UserStateService
from app.services.rag_service import RAGService
from app.services.prompt_generator import PromptGenerator
from app.services.llm_gateway import LLMGateway
from app.services.content_loader import load_json_content  # 导入content_loader
from app.crud.crud_event import event as crud_event
from app.crud.crud_chat_history import chat_history as crud_chat_history
from app.schemas.chat import ChatHistoryCreate
from app.schemas.behavior import BehaviorEvent
# 准备事件数据
from app.schemas.behavior import EventType, AiHelpRequestData
from datetime import datetime, UTC


class DynamicController:
    """动态控制器 - 编排各个服务的核心逻辑"""

    def __init__(self,
                 user_state_service: UserStateService,
                 sentiment_service: SentimentAnalysisService,
                 rag_service: RAGService,
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
        # 验证必需的服务
        if user_state_service is None:
            raise TypeError("user_state_service cannot be None")
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
            # 步骤1: 获取或创建用户档案（使用UserStateService）
            profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)

            # 步骤2: 情感分析
            if self.sentiment_service:
                sentiment_result = self.sentiment_service.analyze_sentiment(
                    request.user_message
                )
            else:
                # 如果情感分析服务未启用，创建一个默认的情感分析结果
                from app.schemas.chat import SentimentAnalysisResult
                sentiment_result = SentimentAnalysisResult(
                    label="neutral",
                    confidence=0.0,
                    details={}
                )

            # 构建用户状态摘要（同时更新用户情感状态）
            user_state_summary = self._build_user_state_summary(profile, sentiment_result)

            # 步骤3: RAG检索
            retrieved_knowledge = []
            if self.rag_service:
                try:
                    retrieved_knowledge = self.rag_service.retrieve(request.user_message)
                except Exception as e:
                    print(f"⚠️ RAG检索失败，使用空知识内容: {e}")
                    retrieved_knowledge = []

            # 步骤4: 加载内容（学习内容或测试任务）
            content_title = None
            loaded_content_json = None
            if request.mode and request.content_id:
                try:
                    content_type = "learning_content" if request.mode == "learning" else "test_tasks"
                    loaded_content = load_json_content(content_type, request.content_id)
                    content_title = getattr(loaded_content, 'title', None) or getattr(loaded_content, 'topic_id', None)
                    
                    # 根据模式处理内容
                    if request.mode == "test":
                        loaded_content_json = loaded_content.model_dump_json()
                    elif request.mode == "learning":
                        # 移除sc_all字段
                        learning_content_dict = loaded_content.model_dump()
                        learning_content_dict.pop('sc_all', None)
                        loaded_content_json = json.dumps(learning_content_dict)

                except Exception as e:
                    print(f"⚠️ 内容加载失败: {e}")
                    loaded_content = None
                    content_title = None
            else:
                loaded_content = None

            # 步骤5: 生成提示词
            # 将ConversationMessage转换为字典格式
            conversation_history_dicts = []
            if request.conversation_history:
                for msg in request.conversation_history:
                    conversation_history_dicts.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            elif request.conversation_history is None:
                # 确保即使conversation_history为None也传递空列表
                conversation_history_dicts = []

            retrieved_knowledge_content = [item['content'] for item in retrieved_knowledge if isinstance(item, dict) and 'content' in item]
            system_prompt, messages = self.prompt_generator.create_prompts(
                user_state=user_state_summary,
                retrieved_context=retrieved_knowledge_content,
                conversation_history=conversation_history_dicts,
                user_message=request.user_message,
                code_content=request.code_context,
                mode=request.mode,
                content_title=content_title,
                content_json=loaded_content_json,  # 传递加载的内容JSON
                test_results=request.test_results  # 传递测试结果
            )

            # 步骤6: 调用LLM
            #TODO:done表示流式输出是否完成    elapsed:表示当前已经输出多少字
            ai_response = await self.llm_gateway.get_stream_completion(
                system_prompt=system_prompt,
                messages=messages
            )

            
            # ai_response = await self.llm_gateway.get_completion(
            #     system_prompt=system_prompt,
            #     messages=messages
            # )


            # 步骤7: 构建响应（只包含AI回复内容，符合TDD-II-10设计）
            response = ChatResponse(ai_response=ai_response)

            # 步骤8: 记录AI交互
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

        return UserStateSummary(
            participant_id=profile.participant_id,
            emotion_state=emotion_state,
            behavior_counters=profile.behavior_counters,
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
            # 更新用户状态
            self.user_state_service.handle_ai_help_request(request.participant_id, content_title)

            # 准备事件数据
            event = BehaviorEvent(
                participant_id=request.participant_id,
                event_type=EventType.AI_HELP_REQUEST,
                event_data=AiHelpRequestData(message=request.user_message),
                timestamp=datetime.now(UTC)
            )

            # 准备用户聊天记录
            user_chat = ChatHistoryCreate(
                participant_id=request.participant_id,
                role="user",
                message=request.user_message
            )

            # 准备AI聊天记录
            ai_chat = ChatHistoryCreate(
                participant_id=request.participant_id,
                role="assistant",
                message=response.ai_response,
                raw_prompt_to_llm=system_prompt
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
            # 步骤1: 获取或创建用户档案（使用UserStateService）
            profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)
            # 步骤2: 情感分析
            if self.sentiment_service:
                sentiment_result = self.sentiment_service.analyze_sentiment(
                    request.user_message
                )
            else:
                # 如果情感分析服务未启用，创建一个默认的情感分析结果
                from app.schemas.chat import SentimentAnalysisResult
                sentiment_result = SentimentAnalysisResult(
                    label="neutral",
                    confidence=0.0,
                    details={}
                )
            # 构建用户状态摘要（同时更新用户情感状态）
            user_state_summary = self._build_user_state_summary(profile, sentiment_result)
            # 步骤3: RAG检索
            retrieved_knowledge = []
            if self.rag_service:
                try:
                    retrieved_knowledge = self.rag_service.retrieve(request.user_message)
                except Exception as e:
                    print(f"⚠️ RAG检索失败，使用空知识内容: {e}")
                    retrieved_knowledge = []
            # 步骤4: 加载内容（学习内容或测试任务）
            content_title = None
            loaded_content_json = None
            if request.mode and request.content_id:
                try:
                    content_type = "learning_content" if request.mode == "learning" else "test_tasks"
                    loaded_content = load_json_content(content_type, request.content_id)
                    content_title = getattr(loaded_content, 'title', None) or getattr(loaded_content, 'topic_id', None)
                    
                    # 根据模式处理内容
                    if request.mode == "test":
                        loaded_content_json = loaded_content.model_dump_json()
                    elif request.mode == "learning":
                        # 移除sc_all字段
                        learning_content_dict = loaded_content.model_dump()
                        learning_content_dict.pop('sc_all', None)
                        loaded_content_json = json.dumps(learning_content_dict)
                except Exception as e:
                    print(f"⚠️ 内容加载失败: {e}")
                    loaded_content = None
                    content_title = None
            else:
                loaded_content = None
            # 步骤5: 生成提示词
            # 将ConversationMessage转换为字典格式
            conversation_history_dicts = []
            if request.conversation_history:
                for msg in request.conversation_history:
                    conversation_history_dicts.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            elif request.conversation_history is None:
                # 确保即使conversation_history为None也传递空列表
                conversation_history_dicts = []
            retrieved_knowledge_content = [item['content'] for item in retrieved_knowledge if isinstance(item, dict) and 'content' in item]
            system_prompt, messages = self.prompt_generator.create_prompts(
                user_state=user_state_summary,
                retrieved_context=retrieved_knowledge_content,
                conversation_history=conversation_history_dicts,
                user_message=request.user_message,
                code_content=request.code_context,
                mode=request.mode,
                content_title=content_title,
                content_json=loaded_content_json,  # 传递加载的内容JSON
                test_results=request.test_results  # 传递测试结果
            )
            # 步骤6: 调用LLM（同步方式）
            ai_response = self.llm_gateway.get_completion_sync(
                system_prompt=system_prompt,
                messages=messages
            )
            # 步骤7: 构建响应（只包含AI回复内容，符合TDD-II-10设计）
            response = ChatResponse(ai_response=ai_response)
            # 步骤8: 记录AI交互
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