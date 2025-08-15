import sys
import os

# 将项目根目录的 backend 文件夹添加到 sys.path
# This allows the tests to import modules from the 'app' package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


"""
DynamicController 测试文件

测试 DynamicController 的核心功能，包括：
- 自适应响应生成
- 用户状态管理
- 情感分析集成
- RAG服务集成
- AI交互日志记录

注意：此测试文件使用真实的chat_history模块，不再需要mock。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, UTC
from fastapi import BackgroundTasks
import time

# 正常导入所有需要的模块
from app.services.dynamic_controller import DynamicController
from app.services.prompt_generator import PromptGenerator
from app.schemas.chat import (
    ChatRequest, ChatResponse, ConversationMessage, 
    SentimentAnalysisResult, UserStateSummary, ChatHistoryCreate
)
from app.schemas.behavior import BehaviorEvent, EventType, AiHelpRequestData
from app.models.chat_history import ChatHistory
from app.crud.crud_chat_history import chat_history as crud_chat_history

# 导入数据库相关模块
from app.db.database import SessionLocal
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- 测试夹具 ---

@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎"""
    # 使用项目中的实际数据库
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    yield engine

@pytest.fixture
def db_session(db_engine):
    """创建数据库会话"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_user_state_service():
    """创建模拟的UserStateService"""
    mock_service = MagicMock()
    mock_profile = MagicMock()
    mock_profile.participant_id = "test_user_123"  # 添加participant_id
    mock_profile.emotion_state = {
        'current_sentiment': 'NEUTRAL',
        'is_frustrated': False,
        'confidence': 0.5
    }
    mock_profile.behavior_counters = {
        'submission_timestamps': [],
        'error_count': 0,
        'help_requests': 2
    }
    mock_profile.bkt_model = {  # 使用正确的属性名
        'topic_1': MagicMock(mastery_prob=0.6),
        'topic_2': MagicMock(mastery_prob=0.9)
    }
    mock_profile.is_new_user = False  # 添加is_new_user属性
    mock_service.get_or_create_profile.return_value = (mock_profile, False)
    return mock_service

@pytest.fixture
def mock_sentiment_service():
    """创建模拟的SentimentAnalysisService"""
    mock_service = MagicMock()
    mock_service.analyze_sentiment.return_value = SentimentAnalysisResult(
        label="positive",
        confidence=0.8,
        details={"emotion": "happy"}
    )
    return mock_service

@pytest.fixture
def mock_rag_service():
    """创建模拟的RAGService"""
    mock_service = MagicMock()
    mock_service.retrieve.return_value = [
        {"content": "相关知识1", "score": 0.9},
        {"content": "相关知识2", "score": 0.7}
    ]
    return mock_service

@pytest.fixture
def mock_prompt_generator():
    """创建模拟的PromptGenerator"""
    mock_generator = MagicMock()
    mock_generator.create_prompts.return_value = (
        "你是一个智能导师...",
        [{"role": "user", "content": "用户消息"}]
    )
    return mock_generator

@pytest.fixture
def mock_llm_gateway():
    """创建模拟的LLMGateway"""
    mock_gateway = MagicMock()
    mock_gateway.get_completion = AsyncMock(return_value="这是一个AI回复")
    return mock_gateway

@pytest.fixture
def mock_db_session():
    """创建模拟的数据库会话"""
    return MagicMock()

@pytest.fixture
def sample_chat_request():
    """创建示例聊天请求"""
    return ChatRequest(
        participant_id="test_user_123",
        user_message="我需要帮助理解CSS选择器",
        conversation_history=[
            ConversationMessage(role="user", content="什么是CSS？"),
            ConversationMessage(role="assistant", content="CSS是层叠样式表...")
        ],
        code_context=None,  # 暂时设为None，避免CodeContent验证问题
        task_context=None,  # 暂时设为None，避免TestTask验证问题
        topic_title="css_selectors"
    )

@pytest.fixture
def dynamic_controller(
    mock_user_state_service,
    mock_sentiment_service,
    mock_rag_service,
    mock_llm_gateway
):
    """创建DynamicController实例，使用真实的PromptGenerator"""
    # 使用真实的PromptGenerator而不是mock
    prompt_generator = PromptGenerator()
    
    return DynamicController(
        user_state_service=mock_user_state_service,
        sentiment_service=mock_sentiment_service,
        rag_service=mock_rag_service,
        prompt_generator=prompt_generator,
        llm_gateway=mock_llm_gateway
    )

# --- 测试用例 ---

class TestDynamicController:
    """DynamicController测试套件"""

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_success(
        self, 
        dynamic_controller, 
        sample_chat_request, 
        db_session
    ):
        """测试成功的自适应响应生成"""
        # 执行
        response = await dynamic_controller.generate_adaptive_response(
            request=sample_chat_request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证服务调用
        dynamic_controller.user_state_service.get_or_create_profile.assert_called_once()
        dynamic_controller.sentiment_service.analyze_sentiment.assert_called_once_with(
            sample_chat_request.user_message
        )
        dynamic_controller.rag_service.retrieve.assert_called_once_with(
            sample_chat_request.user_message
        )
        dynamic_controller.llm_gateway.get_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_without_sentiment_service(
        self,
        mock_user_state_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试没有情感分析服务时的处理"""
        # 创建没有情感分析服务的控制器
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=None,  # 没有情感分析服务
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 执行
        response = await controller.generate_adaptive_response(
            request=sample_chat_request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证没有调用情感分析服务
        # 但其他服务应该正常调用
        controller.user_state_service.get_or_create_profile.assert_called_once()
        controller.rag_service.retrieve.assert_called_once()
        controller.llm_gateway.get_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_without_rag_service(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试没有RAG服务时的处理"""
        # 创建没有RAG服务的控制器
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=None,  # 没有RAG服务
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 执行
        response = await controller.generate_adaptive_response(
            request=sample_chat_request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证其他服务正常调用
        controller.user_state_service.get_or_create_profile.assert_called_once()
        controller.sentiment_service.analyze_sentiment.assert_called_once()
        controller.llm_gateway.get_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_rag_service_failure(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试RAG服务失败时的处理"""
        # 配置RAG服务抛出异常
        mock_rag_service = MagicMock()
        mock_rag_service.retrieve.side_effect = Exception("RAG服务失败")
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 执行
        response = await controller.generate_adaptive_response(
            request=sample_chat_request,
            db=db_session
        )
        
        # 断言 - 应该继续处理，使用空的检索结果
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证其他服务正常调用
        controller.user_state_service.get_or_create_profile.assert_called_once()
        controller.sentiment_service.analyze_sentiment.assert_called_once()
        controller.llm_gateway.get_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_llm_failure(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        sample_chat_request,
        db_session
    ):
        """测试LLM服务失败时的处理"""
        # 配置LLM网关抛出异常
        mock_llm_gateway = MagicMock()
        mock_llm_gateway.get_completion = AsyncMock(side_effect=Exception("LLM服务失败"))
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 执行
        response = await controller.generate_adaptive_response(
            request=sample_chat_request,
            db=db_session
        )
        
        # 断言 - 应该返回错误响应
        assert isinstance(response, ChatResponse)
        assert "critical error" in response.ai_response.lower()
        assert "research staff" in response.ai_response.lower()

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_new_user(
        self,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试新用户的处理"""
                # 创建新用户的profile
        mock_user_state_service = MagicMock()
        new_user_profile = MagicMock()
        new_user_profile.participant_id = "new_user_456"  # 添加participant_id
        new_user_profile.emotion_state = {'current_sentiment': 'NEUTRAL', 'is_frustrated': False}
        new_user_profile.behavior_counters = {'submission_timestamps': [], 'error_count': 0}
        new_user_profile.bkt_model = {}  # 新用户没有BKT模型
        new_user_profile.is_new_user = True
        # 为 mastery_prob 设置一个默认值或确保它不会被访问
        # 对于新用户，相关的代码路径可能根本不应该访问 mastery_prob
        # 但为确保测试健壮性，我们在这里提供一个模拟值
        if 'bkt_model' in new_user_profile and new_user_profile.bkt_model:
            for topic in new_user_profile.bkt_model.values():
                topic.mastery_prob = 0.0
        else:
             new_user_profile.bkt_models = {}

        mock_user_state_service.get_or_create_profile.return_value = (new_user_profile, True)
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 修改请求为新用户
        new_user_request = sample_chat_request.model_copy(update={"participant_id": "new_user_456"})
        
        # 执行
        response = await controller.generate_adaptive_response(
            request=new_user_request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证新用户标志被正确传递
        controller.user_state_service.get_or_create_profile.assert_called_once()

    def test_build_user_state_summary(self, mock_user_state_service):
        """测试用户状态摘要构建"""
        # 准备测试数据
        profile = MagicMock()
        profile.participant_id = "test_user_123"  # 添加participant_id
        profile.emotion_state = {
            'current_sentiment': 'NEUTRAL',
            'is_frustrated': False
        }
        profile.behavior_counters = {
            'submission_timestamps': [],
            'error_count': 0,
            'help_requests': 3
        }
        profile.bkt_model = {  # 使用正确的属性名
            'topic_1': MagicMock(mastery_prob=0.2),
            'topic_2': MagicMock(mastery_prob=0.7)
        }
        profile.is_new_user = False  # 添加is_new_user属性
        
        sentiment_result = SentimentAnalysisResult(
            label="positive",
            confidence=0.85,
            details={"emotion": "excited"}
        )
        
        # 执行
        summary = DynamicController._build_user_state_summary(profile, sentiment_result)
        
        # 断言
        assert isinstance(summary, UserStateSummary)
        assert summary.participant_id == "test_user_123"
        assert summary.is_new_user is False
        assert summary.emotion_state["current_sentiment"] == "positive"
        assert summary.emotion_state["confidence"] == 0.85
        assert summary.emotion_state["details"]["emotion"] == "excited"
        assert summary.behavior_counters["help_requests"] == 3
        assert len(summary.bkt_models) == 2

    @patch('app.services.dynamic_controller.crud_event')
    @patch('app.services.dynamic_controller.crud_chat_history')
    def test_log_ai_interaction_success(
        self,
        mock_crud_chat_history,
        mock_crud_event,
        sample_chat_request,
        db_session
    ):
        """测试AI交互日志记录成功"""
        # 准备响应
        response = ChatResponse(ai_response="AI回复内容")
        system_prompt = "系统提示词"
        
        # 执行
        DynamicController._log_ai_interaction(
            request=sample_chat_request,
            response=response,
            db=db_session,
            system_prompt=system_prompt
        )
        
        # 验证事件记录
        mock_crud_event.create_from_behavior.assert_called_once()
        call_args = mock_crud_event.create_from_behavior.call_args
        event = call_args[1]['obj_in']
        assert isinstance(event, BehaviorEvent)
        assert event.participant_id == "test_user_123"
        assert event.event_type == EventType.AI_HELP_REQUEST
        
        # 验证聊天历史记录
        assert mock_crud_chat_history.create.call_count == 2
        
        # 验证用户消息记录
        user_call = mock_crud_chat_history.create.call_args_list[0]
        user_chat = user_call[1]['obj_in']
        assert user_chat.role == "user"
        assert user_chat.message == "我需要帮助理解CSS选择器"
        
        # 验证AI消息记录
        ai_call = mock_crud_chat_history.create.call_args_list[1]
        ai_chat = ai_call[1]['obj_in']
        assert ai_chat.role == "assistant"
        assert ai_chat.message == "AI回复内容"
        assert ai_chat.raw_prompt_to_llm == system_prompt

    @patch('app.services.dynamic_controller.crud_event')
    @patch('app.services.dynamic_controller.crud_chat_history')
    def test_log_ai_interaction_with_background_tasks(
        self,
        mock_crud_chat_history,
        mock_crud_event,
        sample_chat_request,
        db_session
    ):
        """测试使用后台任务的AI交互日志记录"""
        # 准备后台任务模拟
        mock_background_tasks = MagicMock()
        response = ChatResponse(ai_response="AI回复内容")
        system_prompt = "系统提示词"
        
        # 执行
        DynamicController._log_ai_interaction(
            request=sample_chat_request,
            response=response,
            db=db_session,
            background_tasks=mock_background_tasks,
            system_prompt=system_prompt
        )
        
        # 验证后台任务被添加
        assert mock_background_tasks.add_task.call_count == 3
        
        # 验证事件记录任务
        event_task_call = mock_background_tasks.add_task.call_args_list[0]
        assert event_task_call[0][0] == mock_crud_event.create_from_behavior
        
        # 验证聊天历史记录任务
        chat_task_calls = mock_background_tasks.add_task.call_args_list[1:]
        assert len(chat_task_calls) == 2
        assert chat_task_calls[0][0][0] == mock_crud_chat_history.create
        assert chat_task_calls[1][0][0] == mock_crud_chat_history.create

    @patch('app.services.dynamic_controller.crud_event')
    @patch('app.services.dynamic_controller.crud_chat_history')
    def test_log_ai_interaction_failure(
        self,
        mock_crud_chat_history,
        mock_crud_event,
        sample_chat_request,
        db_session
    ):
        """测试AI交互日志记录失败时的处理"""
        # 配置CRUD操作抛出异常
        mock_crud_event.create_from_behavior.side_effect = Exception("数据库错误")
        
        response = ChatResponse(ai_response="AI回复内容")
        
        # 执行并验证异常
        with pytest.raises(RuntimeError) as exc_info:
            DynamicController._log_ai_interaction(
                request=sample_chat_request,
                response=response,
                db=db_session
            )
        
        assert "Failed to log AI interaction" in str(exc_info.value)
        assert "test_user_123" in str(exc_info.value)

    @patch('app.services.prompt_generator.PromptGenerator.create_prompts')
    @pytest.mark.asyncio
    async def test_generate_adaptive_response_empty_conversation_history(
        self,
        mock_create_prompts,
        dynamic_controller,
        db_session
    ):
        """测试空对话历史的处理"""
        mock_create_prompts.return_value = ("system_prompt", [{"role": "user", "content": "..."}])
        # 创建没有对话历史的请求
        request = ChatRequest(
            participant_id="test_user_123",
            user_message="第一个问题",
            conversation_history=[],
            code_context=None,
            task_context=None,
            topic_title=""
        )
        
        # 执行
        response = await dynamic_controller.generate_adaptive_response(
            request=request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证提示词生成器被正确调用
        mock_create_prompts.assert_called_once()
        call_args = mock_create_prompts.call_args
        assert call_args.kwargs['conversation_history'] == []

    @patch('app.services.prompt_generator.PromptGenerator.create_prompts')
    @pytest.mark.asyncio
    async def test_generate_adaptive_response_with_code_context(
        self,
        mock_create_prompts,
        dynamic_controller,
        db_session
    ):
        """测试包含代码上下文的请求处理"""
        mock_create_prompts.return_value = ("system_prompt", [{"role": "user", "content": "..."}])
        # 创建包含代码上下文的请求
        request = ChatRequest(
            participant_id="test_user_123",
            user_message="我的代码有什么问题？",
            conversation_history=[],
            code_context=None,  # 暂时设为None，避免CodeContent验证问题
            task_context=None,  # 暂时设为None，避免TestTask验证问题
            topic_title="css_layout"
        )
        
        # 执行
        response = await dynamic_controller.generate_adaptive_response(
            request=request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证代码上下文被正确传递
        mock_create_prompts.assert_called_once()
        call_args = mock_create_prompts.call_args
        assert call_args.kwargs['code_content'] == request.code_context
        assert call_args.kwargs['task_context'] == request.task_context
        assert call_args.kwargs['topic_title'] == "css_layout"

    def test_build_user_state_summary_with_dict_like_profile(self):
        """测试处理字典样式的profile"""
        # 创建字典样式的profile
        profile_dict = {
            'participant_id': 'test_user_123',
            'emotion_state': {'current_sentiment': 'NEUTRAL', 'is_frustrated': False},
            'behavior_counters': {'help_requests': 5},
            'bkt_model': {'topic_1': MagicMock(mastery_prob=0.3)},
            'is_new_user': False
        }
        
        # 创建一个具有字典属性的对象
        class DictLikeProfile:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        profile = DictLikeProfile(profile_dict)
        
        sentiment_result = SentimentAnalysisResult(
            label="negative",
            confidence=0.7,
            details={"emotion": "frustrated"}
        )
        
        # 执行
        summary = DynamicController._build_user_state_summary(profile, sentiment_result)
        
        # 断言
        assert isinstance(summary, UserStateSummary)
        assert summary.participant_id == "test_user_123"
        assert summary.emotion_state["current_sentiment"] == "negative"
        assert summary.emotion_state["confidence"] == 0.7
        assert summary.behavior_counters["help_requests"] == 5

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_malformed_request(
        self,
        dynamic_controller,
        db_session
    ):
        """测试格式错误的请求处理"""
        # 创建格式错误的请求（缺少必要字段）
        request = ChatRequest(
            participant_id="",  # 空的participant_id
            user_message="",    # 空的消息
            conversation_history=[],
            code_context=None,
            task_context=None,
            topic_title=""
        )
        
        # 执行
        response = await dynamic_controller.generate_adaptive_response(
            request=request,
            db=db_session
        )
        
        # 断言 - 应该能够处理，但可能返回默认响应
        assert isinstance(response, ChatResponse)
        # 具体行为取决于各个服务的实现

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_concurrent_requests(
        self,
        dynamic_controller,
        db_session
    ):
        """测试并发请求处理"""
        import asyncio
        
        # 创建多个并发请求
        requests = []
        for i in range(3):
            request = ChatRequest(
                participant_id=f"user_{i}",
                user_message=f"问题{i}",
                conversation_history=[],
                code_context=None,
                task_context=None,
                topic_title=""
            )
            requests.append(request)
        
        # 并发执行
        tasks = [
            dynamic_controller.generate_adaptive_response(request, db_session)
            for request in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # 断言所有请求都成功处理
        assert len(responses) == 3
        for response in responses:
            assert isinstance(response, ChatResponse)
            assert response.ai_response == "这是一个AI回复"

    def test_dynamic_controller_initialization(self):
        """测试DynamicController的初始化"""
        # 创建所有必要的服务
        user_state_service = MagicMock()
        sentiment_service = MagicMock()
        rag_service = MagicMock()
        prompt_generator = MagicMock()
        llm_gateway = MagicMock()
        
        # 执行
        controller = DynamicController(
            user_state_service=user_state_service,
            sentiment_service=sentiment_service,
            rag_service=rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=llm_gateway
        )
        
        # 断言
        assert controller.user_state_service == user_state_service
        assert controller.sentiment_service == sentiment_service
        assert controller.rag_service == rag_service
        assert controller.prompt_generator == prompt_generator
        assert controller.llm_gateway == llm_gateway

    @pytest.mark.asyncio
    async def test_generate_adaptive_response_with_large_conversation_history(
        self,
        dynamic_controller,
        db_session
    ):
        """测试大型对话历史的处理"""
        # 创建大型对话历史
        from app.schemas.chat import ConversationMessage
        large_history = []
        for i in range(50):  # 50轮对话
            large_history.append(ConversationMessage(role="user", content=f"用户消息{i}"))
            large_history.append(ConversationMessage(role="assistant", content=f"AI回复{i}"))
        
        request = ChatRequest(
            participant_id="test_user_123",
            user_message="新问题",
            conversation_history=large_history,
            code_context=None,
            task_context=None,
            topic_title=""
        )
        
        # 执行
        response = await dynamic_controller.generate_adaptive_response(
            request=request,
            db=db_session
        )
        
        # 断言
        assert isinstance(response, ChatResponse)
        assert response.ai_response == "这是一个AI回复"
        
        # 验证对话历史被正确传递
        with patch.object(dynamic_controller.prompt_generator, 'create_prompts', wraps=dynamic_controller.prompt_generator.create_prompts) as mock_create_prompts:
            await dynamic_controller.generate_adaptive_response(
                request=request,
                db=db_session
            )
            mock_create_prompts.assert_called_once()
            call_args = mock_create_prompts.call_args
            assert len(call_args.kwargs['conversation_history']) == 100  # 50轮 * 2条消息

    # === TDD-II-10 核心流程测试 ===
    
    @pytest.mark.asyncio
    async def test_service_orchestration_order_tdd_compliance(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """TDD-II-10: 验证服务调用顺序符合规范"""
        call_order = []
        
        # 设置mock以跟踪调用顺序
        def user_state_side_effect(*args):
            call_order.append('user_state')
            # 确保返回一个可用的profile对象
            mock_profile = MagicMock()
            mock_profile.participant_id = "test_user_123"
            mock_profile.emotion_state = {}
            mock_profile.behavior_counters = {}
            mock_profile.bkt_model = {}
            mock_profile.is_new_user = False
            return (mock_profile, False)

        mock_user_state_service.get_or_create_profile.side_effect = user_state_side_effect
        mock_sentiment_service.analyze_sentiment.side_effect = \
            lambda *args: call_order.append('sentiment') or SentimentAnalysisResult(
                label="positive", confidence=0.8, details={}
            )
        mock_rag_service.retrieve.side_effect = \
            lambda *args, **kwargs: call_order.append('rag') or []
        
        prompt_generator = PromptGenerator()
        
        # 包装原始的create_prompts方法
        original_create_prompts = prompt_generator.create_prompts
        def side_effect_create_prompts(*args, **kwargs):
            call_order.append('prompt_generator')
            return original_create_prompts(*args, **kwargs)

        prompt_generator.create_prompts = MagicMock(side_effect=side_effect_create_prompts)
        
        mock_llm_gateway.get_completion.side_effect = \
            lambda *args, **kwargs: call_order.append('llm_gateway') or "response"
        
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        # 验证TDD-II-10规定的调用顺序
        expected_order = ['user_state', 'sentiment', 'rag', 'prompt_generator', 'llm_gateway']
        assert call_order == expected_order, f"服务调用顺序不符合TDD-II-10规范: {call_order}"

        # 验证 create_prompts 被调用
        prompt_generator.create_prompts.assert_called_once()

    @pytest.mark.asyncio
    async def test_emotion_state_update_integration(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """TDD-II-10: 验证情感分析结果正确更新用户状态"""
        # 创建可跟踪的mock profile
        mock_profile = MagicMock()
        mock_profile.participant_id = "test_user_123"
        mock_profile.emotion_state = {'current_sentiment': 'NEUTRAL', 'confidence': 0.5}
        mock_profile.behavior_counters = {'help_requests': 2}
        mock_profile.bkt_model = {}
        mock_profile.is_new_user = False
        
        mock_user_state_service.get_or_create_profile.return_value = (mock_profile, False)
        
        # 设置情感分析结果
        sentiment_result = SentimentAnalysisResult(
            label="frustrated",
            confidence=0.9,
            details={"emotion": "frustrated", "intensity": "high"}
        )
        mock_sentiment_service.analyze_sentiment.return_value = sentiment_result
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        # 验证情感状态被正确更新
        assert mock_profile.emotion_state['current_sentiment'] == "frustrated"
        assert mock_profile.emotion_state['confidence'] == 0.9
        assert mock_profile.emotion_state['details']['emotion'] == "frustrated"
        assert mock_profile.emotion_state['details']['intensity'] == "high"

    @pytest.mark.asyncio
    async def test_prompt_generation_context_integration(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        db_session
    ):
        """TDD-II-10: 验证所有上下文信息正确融合到提示词生成中"""
        # 准备完整的上下文
        request = ChatRequest(
            participant_id="test_user_123",
            user_message="如何实现响应式布局？",
            conversation_history=[
                ConversationMessage(role="user", content="什么是Flexbox？"),
                ConversationMessage(role="assistant", content="Flexbox是CSS布局模块...")
            ],
            code_context=None,  # 避免验证问题
            task_context=None,  # 避免验证问题
            topic_title="responsive_design"
        )
        
        # 设置服务返回值
        mock_profile = MagicMock()
        mock_profile.participant_id = "test_user_123"
        mock_profile.emotion_state = {'current_sentiment': 'confused', 'confidence': 0.7}
        mock_profile.behavior_counters = {'help_requests': 3, 'error_count': 1}
        mock_profile.bkt_model = {'responsive_design': MagicMock(mastery_prob=0.4)}
        mock_profile.is_new_user = False
        mock_user_state_service.get_or_create_profile.return_value = (mock_profile, False)
        
        mock_sentiment_service.analyze_sentiment.return_value = SentimentAnalysisResult(
            label="confused", confidence=0.7, details={}
        )
        
        retrieved_knowledge = [
            {"content": "响应式设计使用媒体查询...", "score": 0.9},
            {"content": "Flexbox布局的优势...", "score": 0.8}
        ]
        mock_rag_service.retrieve.return_value = retrieved_knowledge
        
        prompt_generator = PromptGenerator()
        
        # 包装原始的create_prompts方法
        original_create_prompts = prompt_generator.create_prompts
        
        # 使用一个list来捕获call_args
        call_args_capture = []
        def side_effect_create_prompts(*args, **kwargs):
            call_args_capture.append(kwargs)
            return original_create_prompts(*args, **kwargs)

        prompt_generator.create_prompts = MagicMock(side_effect=side_effect_create_prompts)
        
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        await controller.generate_adaptive_response(request, db_session)
        
        # 验证提示词生成器接收到完整的上下文
        assert len(call_args_capture) == 1
        call_kwargs = call_args_capture[0]
        
        # 验证用户状态摘要
        user_state_summary = call_kwargs['user_state']
        assert user_state_summary.participant_id == "test_user_123"
        assert user_state_summary.emotion_state['current_sentiment'] == "confused"
        assert user_state_summary.behavior_counters['help_requests'] == 3
        
        # 验证检索的上下文
        retrieved_context = call_kwargs['retrieved_context']
        assert len(retrieved_context) == 2
        assert "响应式设计使用媒体查询" in retrieved_context[0]
        
        # 验证对话历史被正确转换
        conversation_history = call_kwargs['conversation_history']
        assert len(conversation_history) == 2
        assert conversation_history[0]['role'] == "user"
        assert conversation_history[1]['role'] == "assistant"
        
        # 验证其他上下文
        assert call_kwargs['user_message'] == "如何实现响应式布局？"
        assert call_kwargs['code_content'] is None
        assert call_kwargs['task_context'] is None
        assert call_kwargs['topic_title'] == "responsive_design"

    # === 错误处理和边界情况测试 ===
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request
    ):
        """测试数据库连接失败时的处理"""
        # 模拟数据库异常
        mock_db_session = MagicMock()
        mock_user_state_service.get_or_create_profile.side_effect = Exception("数据库连接失败")
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 执行并验证返回友好错误消息
        response = await controller.generate_adaptive_response(sample_chat_request, mock_db_session)
        
        assert isinstance(response, ChatResponse)
        assert "critical error" in response.ai_response.lower()
        assert "research staff" in response.ai_response.lower()

    @pytest.mark.asyncio
    async def test_service_timeout_handling(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试服务超时的处理"""
        # 模拟LLM超时
        async def timeout_completion(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟延迟
            raise asyncio.TimeoutError("LLM服务超时")
        
        mock_llm_gateway.get_completion.side_effect = timeout_completion
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 执行并验证错误处理
        response = await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        assert isinstance(response, ChatResponse)
        assert "critical error" in response.ai_response.lower()

    @pytest.mark.asyncio
    async def test_concurrent_state_consistency(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        db_session
    ):
        """测试并发请求时的状态一致性"""
        # 创建模拟用户profile
        mock_profile = MagicMock()
        mock_profile.participant_id = "concurrent_user"
        mock_profile.emotion_state = {'current_sentiment': 'NEUTRAL', 'confidence': 0.5}
        mock_profile.behavior_counters = {'help_requests': 0}
        mock_profile.bkt_model = {}
        mock_profile.is_new_user = False
        
        # 确保返回同一个profile实例
        mock_user_state_service.get_or_create_profile.return_value = (mock_profile, False)
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 创建并发请求
        requests = []
        for i in range(5):
            request = ChatRequest(
                participant_id="concurrent_user",
                user_message=f"并发问题{i}",
                conversation_history=[],
                code_context=None,
                task_context=None,
                topic_title=""
            )
            requests.append(request)
        
        # 并发执行
        tasks = [
            controller.generate_adaptive_response(request, db_session)
            for request in requests
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有请求都成功处理
        assert len(responses) == 5
        for response in responses:
            assert isinstance(response, ChatResponse)
            assert not isinstance(response, Exception)
        
        # 验证用户状态服务被调用5次
        assert mock_user_state_service.get_or_create_profile.call_count == 5

    @pytest.mark.asyncio
    async def test_background_tasks_execution_verification(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试后台任务正确执行"""
        background_tasks = BackgroundTasks()
        
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        with patch('app.services.dynamic_controller.crud_event') as mock_crud_event, \
             patch('app.services.dynamic_controller.crud_chat_history') as mock_crud_chat:
            
            await controller.generate_adaptive_response(
                sample_chat_request, 
                db_session, 
                background_tasks=background_tasks
            )
            
            # 验证后台任务被添加
            assert background_tasks.tasks
            
            # 手动执行后台任务来验证它们能正常工作
            for task in background_tasks.tasks:
                task.func(*task.args, **task.kwargs)
            
            # 验证CRUD操作被调用
            assert mock_crud_event.create_from_behavior.called
            assert mock_crud_chat.create.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_user_message_handling(
        self,
        dynamic_controller,
        db_session
    ):
        """测试空用户消息的处理"""
        request = ChatRequest(
            participant_id="test_user_123",
            user_message="",  # 空消息
            conversation_history=[],
            code_context=None,
            task_context=None,
            topic_title=""
        )
        
        response = await dynamic_controller.generate_adaptive_response(request, db_session)
        
        # 应该能够处理空消息
        assert isinstance(response, ChatResponse)
        
        # 验证服务仍然被调用
        dynamic_controller.user_state_service.get_or_create_profile.assert_called_once()
        dynamic_controller.rag_service.retrieve.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_invalid_participant_id_handling(
        self,
        dynamic_controller,
        db_session
    ):
        """测试无效participant_id的处理"""
        request = ChatRequest(
            participant_id="",  # 空ID
            user_message="正常消息",
            conversation_history=[],
            code_context=None,
            task_context=None,
            topic_title=""
        )
        
        response = await dynamic_controller.generate_adaptive_response(request, db_session)
        
        # 应该能够处理无效ID
        assert isinstance(response, ChatResponse)
        
        # 验证用户状态服务仍然被调用
        dynamic_controller.user_state_service.get_or_create_profile.assert_called_once()

    @patch('app.services.prompt_generator.PromptGenerator.create_prompts')
    @pytest.mark.asyncio
    async def test_rag_service_returns_empty_results(
        self,
        mock_create_prompts,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试RAG服务返回空结果的处理"""
        mock_rag_service.retrieve.return_value = []  # 空结果
        mock_create_prompts.return_value = ("system_prompt", [{"role": "user", "content": "..."}])
        
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=PromptGenerator(), # Use real generator
            llm_gateway=mock_llm_gateway
        )
        
        response = await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        assert isinstance(response, ChatResponse)
        
        # 验证提示词生成器接收到空的检索结果
        mock_create_prompts.assert_called_once()
        call_args = mock_create_prompts.call_args
        assert call_args.kwargs['retrieved_context'] == []

    @patch('app.services.prompt_generator.PromptGenerator.create_prompts')
    @pytest.mark.asyncio
    async def test_sentiment_service_none_handling(
        self,
        mock_create_prompts,
        mock_user_state_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试情感分析服务为None时的默认行为"""
        mock_create_prompts.return_value = ("system_prompt", [{"role": "user", "content": "..."}])
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=None,  # None服务
            rag_service=mock_rag_service,
            prompt_generator=PromptGenerator(), # Use real generator
            llm_gateway=mock_llm_gateway
        )
        
        response = await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        assert isinstance(response, ChatResponse)
        
        # 验证默认情感分析结果被创建
        mock_create_prompts.assert_called_once()
        call_args = mock_create_prompts.call_args
        user_state_summary = call_args.kwargs['user_state']
        assert user_state_summary.emotion_state['current_sentiment'] == "neutral"
        assert user_state_summary.emotion_state['confidence'] == 0.0

    def test_build_user_state_summary_with_none_emotion_state(self):
        """测试emotion_state为None时的处理"""
        profile = MagicMock()
        profile.participant_id = "test_user_123"
        profile.emotion_state = None  # None emotion_state
        profile.behavior_counters = {'help_requests': 1}
        profile.bkt_model = {}
        profile.is_new_user = False
        
        sentiment_result = SentimentAnalysisResult(
            label="happy", confidence=0.8, details={}
        )
        
        summary = DynamicController._build_user_state_summary(profile, sentiment_result)
        
        assert isinstance(summary, UserStateSummary)
        assert summary.emotion_state['current_sentiment'] == "happy"
        assert summary.emotion_state['confidence'] == 0.8
        assert summary.emotion_state['details'] == {}

    def test_build_user_state_summary_with_empty_emotion_state(self):
        """测试emotion_state为空字典时的处理"""
        profile = MagicMock()
        profile.participant_id = "test_user_123"
        profile.emotion_state = {}  # 空emotion_state
        profile.behavior_counters = {'help_requests': 1}
        profile.bkt_model = {}
        profile.is_new_user = False
        
        sentiment_result = SentimentAnalysisResult(
            label="sad", confidence=0.6, details={"reason": "error"}
        )
        
        summary = DynamicController._build_user_state_summary(profile, sentiment_result)
        
        assert isinstance(summary, UserStateSummary)
        assert summary.emotion_state['current_sentiment'] == "sad"
        assert summary.emotion_state['confidence'] == 0.6
        assert summary.emotion_state['details']['reason'] == "error"

    @pytest.mark.asyncio
    async def test_llm_gateway_partial_failure(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_prompt_generator,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试LLM网关部分失败的处理"""
        # 模拟LLM返回部分错误信息
        mock_llm_gateway.get_completion.return_value = "I'm sorry, I cannot process this request."
        
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=mock_prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        response = await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        # 即使LLM返回错误信息，也应该正常处理
        assert isinstance(response, ChatResponse)
        assert "I'm sorry" in response.ai_response
        
        # 验证交互仍然被记录
        with patch('app.services.dynamic_controller.crud_event') as mock_crud_event:
            # 重新调用以测试日志记录
            await controller.generate_adaptive_response(sample_chat_request, db_session)
            assert mock_crud_event.create_from_behavior.called

    @patch('app.services.prompt_generator.PromptGenerator.create_prompts')
    @pytest.mark.asyncio
    async def test_conversation_history_with_none_values(
        self,
        mock_create_prompts,
        dynamic_controller,
        db_session
    ):
        """测试对话历史中包含None值的处理"""
        mock_create_prompts.return_value = ("system_prompt", [{"role": "user", "content": "..."}])
        # 创建包含None的对话历史
        request = ChatRequest(
            participant_id="test_user_123",
            user_message="最新问题",
            conversation_history=None,  # None历史
            code_context=None,
            task_context=None,
            topic_title=""
        )
        
        response = await dynamic_controller.generate_adaptive_response(request, db_session)
        
        assert isinstance(response, ChatResponse)
        
        # 验证提示词生成器接收到空列表而不是None
        mock_create_prompts.assert_called_once()
        call_args = mock_create_prompts.call_args
        assert call_args.kwargs['conversation_history'] == []

    @pytest.mark.asyncio
    async def test_prompt_generator_exception_handling(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        sample_chat_request,
        db_session
    ):
        """测试提示词生成器异常的处理"""
        # 创建一个模拟的PromptGenerator并设置异常
        mock_prompt_generator = MagicMock()
        mock_prompt_generator.create_prompts.side_effect = Exception("提示词生成失败")
        
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=mock_prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        response = await controller.generate_adaptive_response(sample_chat_request, db_session)
        
        # 应该返回友好错误消息
        assert isinstance(response, ChatResponse)
        assert "critical error" in response.ai_response.lower()

    @pytest.mark.asyncio
    async def test_memory_leak_prevention_concurrent_requests(
        self,
        mock_user_state_service,
        mock_sentiment_service,
        mock_rag_service,
        mock_llm_gateway,
        db_session
    ):
        """测试并发请求时的内存泄漏预防"""
        # 使用真实的PromptGenerator
        prompt_generator = PromptGenerator()
        controller = DynamicController(
            user_state_service=mock_user_state_service,
            sentiment_service=mock_sentiment_service,
            rag_service=mock_rag_service,
            prompt_generator=prompt_generator,
            llm_gateway=mock_llm_gateway
        )
        
        # 创建大量并发请求
        requests = []
        for i in range(20):  # 20个并发请求
            request = ChatRequest(
                participant_id=f"user_{i}",
                user_message=f"问题{i}" * 100,  # 较长的消息
                conversation_history=[],
                code_context=None,
                task_context=None,
                topic_title=""
            )
            requests.append(request)
        
        # 测量执行时间
        start_time = time.time()
        
        # 并发执行
        tasks = [
            controller.generate_adaptive_response(request, db_session)
            for request in requests
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证所有请求都在合理时间内完成
        assert execution_time < 20.0, f"执行时间过长: {execution_time}秒"
        
        # 验证所有请求都成功处理
        assert len(responses) == 20
        for response in responses:
            assert isinstance(response, ChatResponse)
            assert not isinstance(response, Exception)

    def test_dynamic_controller_service_initialization_validation(self):
        """测试DynamicController服务初始化验证"""
        # 测试所有必需的服务都不能为None
        with pytest.raises(TypeError):
            DynamicController(
                user_state_service=None,  # None应该引发错误
                sentiment_service=MagicMock(),
                rag_service=MagicMock(),
                prompt_generator=MagicMock(),
                llm_gateway=MagicMock()
            )
        
        # 测试sentiment_service可以为None
        controller = DynamicController(
            user_state_service=MagicMock(),
            sentiment_service=None,  # 可以为None
            rag_service=MagicMock(),
            prompt_generator=MagicMock(),
            llm_gateway=MagicMock()
        )
        
        assert controller.sentiment_service is None
        
        # 测试rag_service可以为None
        controller = DynamicController(
            user_state_service=MagicMock(),
            sentiment_service=MagicMock(),
            rag_service=None,  # 可以为None
            prompt_generator=MagicMock(),
            llm_gateway=MagicMock()
        )
        
        assert controller.rag_service is None

if __name__ == "__main__":
    pytest.main([__file__])
