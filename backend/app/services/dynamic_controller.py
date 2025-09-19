# backend/app/services/dynamic_controller.py
import json
import logging
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.schemas.chat import ChatRequest, ChatResponse, UserStateSummary, SentimentAnalysisResult
from app.services.sentiment_analysis_service import SentimentAnalysisService
from app.services.user_state_service import UserStateService
from app.services.rag_service import RAGService
from app.services.prompt_generator import PromptGenerator
from app.services.llm_gateway import LLMGateway
from app.services.translation_llm_gateway import translate
from app.services.content_loader import load_json_content  # 导入content_loader
from app.crud.crud_event import event as crud_event
from app.crud.crud_chat_history import chat_history as crud_chat_history
from app.schemas.chat import ChatHistoryCreate
from app.schemas.behavior import BehaviorEvent
# 准备事件数据
from app.schemas.behavior import EventType, AiHelpRequestData
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import AsyncGenerator
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)
class DynamicController:
    """动态控制器 - 编排各个服务的核心逻辑"""

    def __init__(self,
                 user_state_service: UserStateService,
                 sentiment_service: SentimentAnalysisService,
                 rag_service: RAGService,
                 prompt_generator: PromptGenerator,
                 llm_gateway: LLMGateway,
                 clustering_service = None):
        """
        初始化动态控制器

        Args:
            user_state_service: 用户状态服务
            sentiment_service: 情感分析服务
            rag_service: RAG服务
            prompt_generator: 提示词生成器
            llm_gateway: LLM网关服务
            clustering_service: 聚类服务（可选）
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
        self.clustering_service = clustering_service
        self.logger = logging.getLogger(__name__)

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
        logger.info(f"开始进行翻译...{request.user_message}")
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

            # 暂不构建用户状态摘要，等待内容加载后递增提问计数

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
                    # 学习模式：排除 sc_all 字段；测试模式：保留完整JSON
                    if request.mode == "learning":
                        learning_content_dict = loaded_content.model_dump()
                        learning_content_dict.pop('sc_all', None)
                        loaded_content_json = json.dumps(learning_content_dict, ensure_ascii=False)
                    else:
                        loaded_content_json = loaded_content.model_dump_json()

                except Exception as e:
                    print(f"⚠️ 内容加载失败: {e}")
                    loaded_content = None
                    content_title = None
            else:
                loaded_content = None

            # 在生成提示词前：递增求助/提问计数，使当前轮次即可反映最新次数
            try:
                self.user_state_service.handle_ai_help_request(request.participant_id, content_title)
                # 重新获取最新profile（从Redis），以反映递增后的行为计数
                profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)
            except Exception as _:
                # 计数递增失败不影响主流程
                pass

            # 步骤4.5: 进度聚类分析（在构建用户状态摘要前）
            if request.conversation_history:
                # 将ConversationMessage转换为字典格式用于聚类分析
                conversation_for_clustering = []
                for msg in request.conversation_history:
                    conversation_for_clustering.append({
                        'role': msg.role,
                        'content': msg.content
                    })
                
                # 使用节流逻辑：仅在满足条件时才触发聚类分析
                should_cluster = self.user_state_service._should_perform_clustering(profile, conversation_for_clustering)
                if should_cluster:
                    try:
                        # 触发聚类分析：使用注入的聚类服务
                        clustering_result = self.user_state_service.update_progress_clustering(
                            request.participant_id, 
                            conversation_for_clustering,
                            clustering_service=self.clustering_service
                        )
                        
                        if clustering_result and clustering_result.get('analysis_successful'):
                            model_type = clustering_result.get('model_type', 'unknown')
                            print(f"✅ 距离聚类分析完成 ({model_type}): {clustering_result['cluster_name']} "
                                  f"(置信度: {clustering_result.get('confidence', 0):.3f}, 类型: {clustering_result.get('classification_type', 'unknown')})")
                        
                        # 重新获取profile以反映聚类分析结果
                        profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)
                        
                    except Exception as e:
                        print(f"⚠️ 进度聚类分析失败，继续正常流程: {e}")
                else:
                    print(f"🚦 聚类分析节流：跳过此次请求（消息数未达到步长8或时间间隔不足）")

            # 现在构建用户状态摘要（包含最新行为计数、情感和聚类结果）
            user_state_summary = self._build_user_state_summary(profile, sentiment_result)

            # 诊断日志：输出本次对话可见的BKT快照与上下文注入情况
            try:
                bkt = getattr(user_state_summary, 'bkt_models', {}) or {}
                topic_details = []
                for topic_id, model in (bkt.items() if isinstance(bkt, dict) else []):
                    prob = None
                    if isinstance(model, dict):
                        prob = model.get('mastery_prob')
                    else:
                        prob = getattr(model, 'mastery_prob', None)
                        if prob is None and hasattr(model, 'get_mastery_prob'):
                            try:
                                prob = model.get_mastery_prob()
                            except Exception:
                                prob = None
                    if isinstance(prob, (int, float)):
                        topic_details.append(f"{topic_id}={prob:.3f}")
                    else:
                        topic_details.append(f"{topic_id}=None")
                topic_str = "; ".join(topic_details) if topic_details else "none"
                self.logger.info(
                    f"BKT snapshot for {request.participant_id} (mode={request.mode}, content_id={request.content_id}): "
                    f"topics={len(bkt) if isinstance(bkt, dict) else 0}; {topic_str}"
                )
            except Exception as e:
                self.logger.warning(f"Failed to log BKT snapshot: {e}")

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
            # 诊断日志：上下文注入规模
            try:
                test_count = len(request.test_results) if request.test_results else 0
                self.logger.info(
                    f"Context inputs -> RAG={len(retrieved_knowledge_content)}, content_json={'yes' if loaded_content_json else 'no'}, "
                    f"test_results={test_count}"
                )
            except Exception:
                pass
            system_prompt, messages, context_snapshot = self.prompt_generator.create_prompts(
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
            ai_response = await self.llm_gateway.get_completion(
                system_prompt=system_prompt,
                messages=messages
            )
            # 步骤7: 构建响应（只包含AI回复内容，符合TDD-II-10设计）
            response = ChatResponse(ai_response=ai_response)

            # 步骤8: 记录AI交互
            self._log_ai_interaction(request, response, db, sentiment_result, background_tasks, system_prompt, content_title, context_snapshot)

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
        emotion: SentimentAnalysisResult,
        background_tasks: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        content_title: Optional[str] = None,
        context_snapshot: Optional[str] = None,
    ):
        """
        根据TDD-I规范，异步记录AI交互。
        1. 在 event_logs 中记录一个 "ai_chat" 事件。
        2. 在 chat_history 中记录用户和AI的完整消息。
        3. 更新用户状态中的提问计数器（已在生成提示词前完成，不在此重复）。
        """
        try:
            # 准备事件数据
            event = BehaviorEvent(
                participant_id=request.participant_id,
                event_type=EventType.AI_HELP_REQUEST,
                event_data=AiHelpRequestData(message=request.user_message).model_dump(),
                # 统一使用上海时区
                timestamp=datetime.now(ZoneInfo("Asia/Shanghai"))
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
                raw_context_to_llm=context_snapshot + json.dumps(emotion.model_dump(), ensure_ascii=False) if context_snapshot else json.dumps(emotion.model_dump(), ensure_ascii=False),
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
    ):
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
            # 创建翻译缓存避免重复翻译
            translation_cache = {}
            
            def get_translation(text):
                """获取翻译结果，使用缓存避免重复翻译"""
                if text not in translation_cache:
                    translation_cache[text] = translate(text)
                return translation_cache[text]
            
            logger.info(f"翻译前：{request.user_message}")
            translated_message = get_translation(request.user_message)
            logger.info(f"翻译后：{translated_message}")
            # 步骤1: 获取或创建用户档案（使用UserStateService）
            profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)
            # 步骤2: 情感分析
            if self.sentiment_service:
                sentiment_result = self.sentiment_service.analyze_sentiment(
                    translated_message
                )
            else:
                # 如果情感分析服务未启用，创建一个默认的情感分析结果
                from app.schemas.chat import SentimentAnalysisResult
                sentiment_result = SentimentAnalysisResult(
                    label="neutral",
                    confidence=0.0,
                    details={}
                )
            # 暂不构建用户状态摘要，等待内容加载后递增提问计数
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
                    # 学习模式：排除 sc_all 字段；测试模式：保留完整JSON
                    if request.mode == "learning":
                        learning_content_dict = loaded_content.model_dump()
                        learning_content_dict.pop('sc_all', None)
                        loaded_content_json = json.dumps(learning_content_dict, ensure_ascii=False)
                    else:
                        loaded_content_json = loaded_content.model_dump_json()
                except Exception as e:
                    print(f"⚠️ 内容加载失败: {e}")
                    loaded_content = None
                    content_title = None
            else:
                loaded_content = None
            # 在生成提示词前：递增求助/提问计数，使当前轮次即可反映最新次数
            try:
                self.user_state_service.handle_ai_help_request(request.participant_id, content_title)
                # 重新获取最新profile（从Redis），以反映递增后的行为计数
                profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)
            except Exception as _:
                pass

            # 步骤4.5: 进度聚类分析（在构建用户状态摘要前）
            if request.conversation_history:
                # 将ConversationMessage转换为字典格式用于聚类分析
                conversation_for_clustering = []
                trans_history = []
                for msg in request.conversation_history:
                    conversation_for_clustering.append({
                        'role': msg.role,
                        'content': msg.content
                    })
                
                
                # 使用节流逻辑：仅在满足条件时才触发聚类分析
                should_cluster = self.user_state_service._should_perform_clustering(profile,conversation_for_clustering)
                if should_cluster:
                    try:
                        for msg in request.conversation_history:
                            if msg.role == 'user':
                                trans_history.append({
                                    'role': msg.role,
                                    'content': get_translation(msg.content)
                                })
                                logger.info(f"翻译历史：{trans_history}")
                        # 触发聚类分析：使用注入的聚类服务
                        clustering_result = self.user_state_service.update_progress_clustering(
                            request.participant_id, 
                            trans_history,
                            clustering_service=self.clustering_service
                        )
                        
                        if clustering_result and clustering_result.get('analysis_successful'):
                            model_type = clustering_result.get('model_type', 'unknown')
                            logger.info(f"✅ 距离聚类分析完成 (同步-{model_type}): {clustering_result['cluster_name']} "
                                  f"(置信度: {clustering_result.get('confidence', 0):.3f}, 类型: {clustering_result.get('classification_type', 'unknown')})")
                        
                        # 重新获取profile以反映聚类分析结果
                        profile, _ = self.user_state_service.get_or_create_profile(request.participant_id, db)
                        
                    except Exception as e:
                        print(f"⚠️ 进度聚类分析失败 (同步)，继续正常流程: {e}")
                else:
                    print(f"🚦 聚类分析节流 (同步)：跳过此次请求（消息数未达到步长8或时间间隔不足）")

            # 现在构建用户状态摘要（包含最新行为计数、情感和聚类结果）
            user_state_summary = self._build_user_state_summary(profile, sentiment_result)

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
            system_prompt, messages, context_snapshot = self.prompt_generator.create_prompts(
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
            ai_response=""
            # 步骤6: 调用LLM（同步方式）
            for chunck in self.llm_gateway.get_stream_completion_sync(
                system_prompt=system_prompt,
                messages=messages
            ):
                ai_response += chunck
                yield chunck
            # 步骤7: 构建响应（只包含AI回复内容，符合TDD-II-10设计）
            response = ChatResponse(ai_response=ai_response)
            # 步骤8: 记录AI交互
            self._log_ai_interaction(request, response, db, sentiment_result, background_tasks, system_prompt, content_title, context_snapshot)
            #return response
        except Exception as e:
            print(f"❌ CRITICAL ERROR in generate_adaptive_response_sync: {e}")
            import traceback
            traceback.print_exc()
            # 返回一个标准的、用户友好的错误响应
            # 不包含任何可能泄露内部实现的细节
            return ChatResponse(
                ai_response="I'm sorry, but a critical error occurred on our end. Please notify the research staff."
            )
