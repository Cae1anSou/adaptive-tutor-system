from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import List, Dict, Optional

class Settings(BaseSettings):
    """
    Loads all application settings from environment variables or a .env file.
    The validation is handled by Pydantic.
    """
    # Server
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000

    # LLM API (for chat completions) - required for chat feature
    # Supports OpenAI, Modelscope, and other OpenAI-compatible APIs
    TUTOR_OPENAI_API_KEY: str 
    TUTOR_OPENAI_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"  # Default to Qwen for Modelscope
    TUTOR_OPENAI_API_BASE: str = "https://ms-fc-1d889e1e-d2ad.api-inference.modelscope.cn/v1"  # Modelscope API base
    
    # Alternative config keys for compatibility
    OPENAI_MODEL: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None

    # Embedding API (optional)
    TUTOR_EMBEDDING_API_KEY: Optional[str] = None
    TUTOR_EMBEDDING_API_BASE: str = "https://ms-fc-1d889e1e-d2ad.api-inference.modelscope.cn/v1"
    TUTOR_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-4B-GGUF"
    
    # Translation API (optional)
    TUTOR_TRANSLATION_API_KEY: Optional[str] = None
    TUTOR_TRANSLATION_API_BASE: str = "https://api.openai.com/v1"
    TUTOR_TRANSLATION_MODEL: str = "gpt-4-turbo"

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

    DATABASE_URL: str = "sqlite:///./database.db"
    
    # File paths
    DATA_DIR: str = "./backend/data"
    DOCUMENTS_DIR: str = "./backend/data/documents"
    VECTOR_STORE_DIR: str = "./backend/data/vector_store"
    KB_ANN_FILENAME: str = "kb.ann"
    KB_CHUNKS_FILENAME: str = "kb_chunks.json"

    # LLM Settings
    LLM_MAX_TOKENS: int = 65536
    LLM_TEMPERATURE: float = 0.7
    
    # Module enable/disable flags
    ENABLE_RAG_SERVICE: bool = True
    ENABLE_SENTIMENT_ANALYSIS: bool = True
    ENABLE_TRANSLATION_SERVICE: bool = True

    # Frontend endpoints mapping (relative to API_V1_STR)
    # Can be overridden via environment (e.g., ENDPOINTS__chat="/custom/chat")
    ENDPOINTS: Dict[str, str] = {
        "chat": "/chat/ai/chat",
        "learningContent": "/learning-content",
        "testTasks": "/test-tasks",
        "knowledgeGraph": "/knowledge-graph",
        "progress": "/progress/participants",
        "progressUpdate": "/progress/participants",
        "sessionInitiate": "/session/initiate",
        "submissionSubmit": "/submission/submit-test",
    }

settings = Settings()
# Aeolyn: 由于翻译和embedding对于用户而言不是必要的，因此这两个功能我改成了可选加载但弹出警告
# Print non-blocking warnings after initialization
try:
    if settings.ENABLE_RAG_SERVICE and not settings.TUTOR_EMBEDDING_API_KEY:
        print("[WARN] ENABLE_RAG_SERVICE=True 但未提供 TUTOR_EMBEDDING_API_KEY，RAG 将被禁用。")
    if settings.ENABLE_TRANSLATION_SERVICE and not settings.TUTOR_TRANSLATION_API_KEY:
        print("[WARN] ENABLE_TRANSLATION_SERVICE=True 但未提供 TUTOR_TRANSLATION_API_KEY，翻译将被禁用。")
except Exception:
    pass