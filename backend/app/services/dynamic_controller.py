# backend/app/services/dynamic_controller.py
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from app.schemas.chat import ChatRequest, ChatResponse, UserStateSummary, SentimentAnalysisResult
from app.services.sentiment_analysis_service import SentimentAnalysisService
from app.services.user_state_service import UserStateService, StudentProfile
from app.services.rag_service import RAGService
from app.services.prompt_generator import PromptGenerator
from app.services.llm_gateway import LLMGateway

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

            # 更新用户状态（包含情感信息）
            if self.sentiment_service:
                self._update_user_state_with_sentiment(profile, sentiment_result)

            # 构建用户状态摘要
            # TODO: cxz 改用pulic
            user_state_summary = self._build_user_state_summary(profile, sentiment_result)
            
            # 步骤5: RAG检索
            if self.rag_service:
                try:
                    retrieved_knowledge = self.rag_service.retrieve(request.user_message)
                except Exception as e:
                    print(f"⚠️ RAG检索失败，使用空知识内容: {e}")
                    retrieved_knowledge = []
            else:
                retrieved_knowledge = []  # RAG服务未配置
            
            # 步骤6: 生成提示词
            # 将ConversationMessage转换为字典格式
            conversation_history_dicts = []
            if request.conversation_history:
                for msg in request.conversation_history:
                    conversation_history_dicts.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            
            system_prompt, messages = self.prompt_generator.create_prompts(
                user_state=user_state_summary,
                retrieved_context=retrieved_knowledge,
                conversation_history=conversation_history_dicts,
                user_message=request.user_message,
                code_content=request.code_context,
                task_context=request.task_context,
                topic_id=request.topic_id
            )
            
            # 步骤7: 调用LLM
            ai_response = await self.llm_gateway.get_completion(
                system_prompt=system_prompt,
                messages=messages
            )
            
            # 步骤8: 构建响应
            response = ChatResponse(
                ai_response=ai_response,
                user_state_summary=user_state_summary.dict(),
                retrieved_context=retrieved_knowledge,
                system_prompt=system_prompt
            )


            # 步骤9: 记录AI交互
            self._log_ai_interaction(request, response, db, background_tasks)
            
            return response
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR in generate_adaptive_response: {e}")
            import traceback
            traceback.print_exc()
            # 返回一个标准的、用户友好的错误响应
            # 不包含任何可能泄露内部实现的细节
            return ChatResponse(
                ai_response="I'm sorry, but a critical error occurred on our end. Please notify the research staff.",
                user_state_summary={},
                retrieved_context=[],
                system_prompt=""
            )
    
    def _update_user_state_with_sentiment(
        self, 
        profile: StudentProfile,
        sentiment_result: SentimentAnalysisResult
    ):
        """更新用户状态中的情感信息"""
        # 使用StudentProfile的属性，确保兼容性
        if hasattr(profile, 'emotion_state'):
            profile.emotion_state['current_sentiment'] = sentiment_result.label
            profile.emotion_state['confidence'] = sentiment_result.confidence
            if sentiment_result.details:
                profile.emotion_state['details'] = sentiment_result.details
    
    def _build_user_state_summary(
        self, 
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
        background_tasks: Optional[Any] = None
    ):
        """
        根据TDD-I规范，异步记录AI交互。
        1. 在 event_logs 中记录一个 "ai_chat" 事件。
        2. 在 chat_history 中记录用户和AI的完整消息。
        """
        try:
            from app.crud.crud_event import event as crud_event
            from app.crud.crud_chat_history import chat_history as crud_chat_history
            from app.schemas.behavior import BehaviorEvent
            from app.schemas.chat import ChatHistoryCreate

            # 准备事件数据
            event = BehaviorEvent(
                participant_id=request.participant_id,
                event_type="ai_chat",
                event_data={"user_message_length": len(request.user_message)}
            )
            
            # 准备用户聊天记录
            user_chat = ChatHistoryCreate(
                participant_id=request.participant_id,
                role="user",
                message=request.user_message,
                raw_prompt_to_llm=None  # 用户消息没有raw_prompt_to_llm
            )

            # 准备AI聊天记录
            ai_chat = ChatHistoryCreate(
                participant_id=request.participant_id,
                role="ai",
                message=response.ai_response,
                raw_prompt_to_llm=response.system_prompt
            )

            if background_tasks:
                # 异步执行
                background_tasks.add_task(crud_event.create, db=db, obj_in=event)
                background_tasks.add_task(crud_chat_history.create, db=db, obj_in=user_chat)
                background_tasks.add_task(crud_chat_history.create, db=db, obj_in=ai_chat)
                print(f"INFO: AI interaction for {request.participant_id} logged asynchronously.")
            else:
                # 同步执行 (备用)
                crud_event.create(db=db, obj_in=event)
                crud_chat_history.create(db=db, obj_in=user_chat)
                crud_chat_history.create(db=db, obj_in=ai_chat)
                print(f"WARNING: AI interaction for {request.participant_id} logged synchronously.")

        except Exception as e:
            # 数据保存失败必须报错，科研数据完整性优先
            raise RuntimeError(f"Failed to log AI interaction for {request.participant_id}: {e}")

    


# 注意：DynamicController实例现在通过依赖注入容器创建
# 请使用 get_dynamic_controller() 函数获取实例
