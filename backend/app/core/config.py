from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    """
    应用程序配置设置类，从环境变量或.env文件加载所有配置项。
    使用Pydantic进行数据验证和类型检查。

    包含服务器配置、API密钥、模型设置、数据库连接、文件路径等配置项。
    在应用启动时会自动验证必需的配置项是否存在。
    """
    # Server
    BACKEND_PORT: int = 8000

    # OpenAI (for chat completions)
    TUTOR_OPENAI_API_KEY: str = "ms-9ab1cd11-fc6c-4163-9813-d3d0b51bc9e8"
    TUTOR_OPENAI_MODEL: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    TUTOR_OPENAI_API_BASE: str = "https://api-inference.modelscope.cn/v1"


    # Embedding API (can be different from OpenAI)
    TUTOR_EMBEDDING_API_KEY: str = "ms-e9cb1ee1-d248-4f05-87d1-fbc2083c41ae"
    TUTOR_EMBEDDING_API_BASE: str = "https://ms-fc-1d889e1e-d2ad.api-inference.modelscope.cn/v1"
    TUTOR_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-4B-GGUF"

    # Translation API (can be different from OpenAI)
    TUTOR_TRANSLATION_API_KEY: str = "ms-e9cb1ee1-d248-4f05-87d1-fbc2083c41ae"
    TUTOR_TRANSLATION_API_BASE: str = "https://api-inference.modelscope.cn/v1"
    TUTOR_TRANSLATION_MODEL: str = "Qwen/Qwen3-30B-A3B-Instruct-2507"


    # Model configuration tells Pydantic where to find the .env file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True
    )

    PROJECT_NAME: str = "Adaptive Tutor System"
    API_V1_STR: str = "/api/v1"

    # TODO: 到时候可能需要约束，不能放所有都进来
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    DATABASE_URL: str = "sqlite:///./app/db/database.db"

    # File paths
    DATA_DIR: str = "./app/data"
    DOCUMENTS_DIR: str = "./app/data/documents"
    VECTOR_STORE_DIR: str = "./app/data/vector_store"
    KB_ANN_FILENAME: str = "kb.ann"
    KB_CHUNKS_FILENAME: str = "kb_chunks.json"

    # LLM Settings
    LLM_MAX_TOKENS: int = 65536
    LLM_TEMPERATURE: float = 0.7

    # Module enable/disable flags
    ENABLE_RAG_SERVICE: bool = True
    ENABLE_SENTIMENT_ANALYSIS: bool = True
    ENABLE_TRANSLATION_SERVICE: bool = False
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6380/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380
    # REDIS_PASSWORD: str = ""

# Create a single, globally accessible instance of the settings.
# This will raise a validation error on startup if required settings are missing.
settings = Settings()