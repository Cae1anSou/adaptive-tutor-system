import redis

from app.core.config import settings
from app.services.sandbox_service import SandboxService, DefaultPlaywrightManager
from app.services.user_state_service import UserStateService
from app.services.sentiment_analysis_service import sentiment_analysis_service
from app.services.llm_gateway import llm_gateway
from app.services.prompt_generator import prompt_generator
from app.db.database import get_db
from redis.asyncio import Redis

class ProductionConfig:
    """生产环境配置"""
    @staticmethod
    def create_sandbox_service():
        return SandboxService(
            playwright_manager=DefaultPlaywrightManager(),
            headless=True
        )


class DevelopmentConfig:
    """开发环境配置"""
    @staticmethod
    def create_sandbox_service():
        return SandboxService(
            playwright_manager=DefaultPlaywrightManager(),
            headless=False  # 开发环境使用有头模式便于调试
        )


class TestingConfig:
    """测试环境配置"""
    @staticmethod
    def create_sandbox_service(mock_playwright_manager):
        return SandboxService(
            playwright_manager=mock_playwright_manager,
            headless=True
        )


# 应用启动时根据环境选择配置
import os

def get_sandbox_service():
    """根据环境变量获取合适的沙箱服务实例"""
    env = os.getenv('APP_ENV', 'production')
    
    if env == 'development':
        return DevelopmentConfig.create_sandbox_service()
    elif env == 'testing':
        # 在测试环境中，会传入模拟的 Playwright 管理器
        return None  # 实际测试中会传入模拟对象
    else:
        return ProductionConfig.create_sandbox_service()


_redis_client_instance = None
_redis_async_instance = None
def get_redis_client() -> redis.Redis:
    """
    获取 Redis 客户端单例实例
    """
    global _redis_client_instance
    if _redis_client_instance is None:
        # 确保 decode_responses=False，以便 redis-py 返回字节
        # redis-py 的 JSON 命令需要字节作为输入
        _redis_client_instance = redis.from_url(
            settings.REDIS_URL,
            decode_responses=False
        )
    return _redis_client_instance
def get_aioredis() -> Redis:
    """
    获取异步 Redis 客户端 (用于 FastAPI WebSocket 订阅)
    """
    global _redis_async_instance
    if _redis_async_instance is None:
        _redis_async_instance = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True  # 建议 True，避免 json.loads 出错
        )
    return _redis_async_instance
def get_user_state_service(redis_client: redis.Redis) -> UserStateService:
    """
    获取 UserStateService 实例
    """
    return UserStateService(redis_client=redis_client)



# --- AI服务依赖注入 ---

def get_sentiment_analysis_service():
    """
    获取情感分析服务实例
    """
    from app.core.config import settings
    if not settings.ENABLE_SENTIMENT_ANALYSIS:
        return None
    return sentiment_analysis_service


def get_llm_gateway():
    """
    获取LLM网关服务实例
    """
    return llm_gateway


def get_prompt_generator():
    """
    获取提示词生成器实例
    """
    return prompt_generator


def get_rag_service():
    """
    获取RAG服务实例
    """
    from app.core.config import settings
    if not settings.ENABLE_RAG_SERVICE:
        return None
    
    try:
        from app.services.rag_service import RAGService
        # 根据配置决定是否提供翻译服务
        translation_service = None
        if settings.ENABLE_TRANSLATION_SERVICE:
            try:
                from app.services.translation_service import TranslationService
                translation_service = TranslationService()
            except Exception as e:
                print(f"Warning: Translation service initialization failed: {e}")
        
        return RAGService(translation_service)
    except Exception as e:
        print(f"Warning: RAG service initialization failed: {e}")
        return None


def create_dynamic_controller(redis_client: redis.Redis):
    """
    创建动态控制器实例，注入所有依赖
    """
    from app.services.dynamic_controller import DynamicController

    return DynamicController(
        user_state_service=get_user_state_service(redis_client=redis_client),
        sentiment_service=get_sentiment_analysis_service(),
        rag_service=get_rag_service(),
        prompt_generator=get_prompt_generator(),
        llm_gateway=get_llm_gateway()
    )


# 创建单例实例
_dynamic_controller_instance = None

def get_dynamic_controller():
    """
    获取动态控制器实例（单例模式）
    """
    global _dynamic_controller_instance, _redis_client_instance
    if _dynamic_controller_instance is None:
        # 获取Redis客户端实例
        if _redis_client_instance is None:
            _redis_client_instance = get_redis_client()
        _dynamic_controller_instance = create_dynamic_controller(redis_client=_redis_client_instance)
    return _dynamic_controller_instance


