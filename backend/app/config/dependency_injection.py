from app.services.sandbox_service_improved import SandboxService, DefaultPlaywrightManager
from app.services.user_state_service import UserStateService
from app.services.sentiment_analysis_service import sentiment_analysis_service
from app.services.llm_gateway import llm_gateway
from app.services.prompt_generator import prompt_generator
from app.db.database import get_db


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


# 在应用启动时创建 UserStateService 的单例
# 这确保了所有用户的状态都保存在同一个内存缓存中
user_state_service_instance = UserStateService()

def get_user_state_service() -> UserStateService:
    """
    一个简单的依赖项，用于在整个应用中共享同一个UserStateService实例。
    """
    return user_state_service_instance


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
    from app.core.config import settings
    if not settings.TUTOR_OPENAI_API_KEY:
        print("[WARN] 缺少 TUTOR_OPENAI_API_KEY，LLM 网关未启用。")
        return None
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
    if not settings.TUTOR_EMBEDDING_API_KEY:
        return None
    
    try:
        from app.services.rag_service import RAGService
        # 根据配置决定是否提供翻译服务
        translation_service = None
        if settings.ENABLE_TRANSLATION_SERVICE and settings.TUTOR_TRANSLATION_API_KEY:
            try:
                from app.services.translation_service import TranslationService
                translation_service = TranslationService()
            except Exception as e:
                print(f"Warning: Translation service initialization failed: {e}")
        
        return RAGService(translation_service)
    except Exception as e:
        print(f"Warning: RAG service initialization failed: {e}")
        return None


def create_dynamic_controller():
    """
    创建动态控制器实例，注入所有依赖
    """
    from app.services.dynamic_controller import DynamicController
    
    return DynamicController(
        user_state_service=get_user_state_service(),
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
    global _dynamic_controller_instance
    if _dynamic_controller_instance is None:
        _dynamic_controller_instance = create_dynamic_controller()
    return _dynamic_controller_instance


