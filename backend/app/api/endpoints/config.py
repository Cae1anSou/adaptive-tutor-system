from fastapi import APIRouter
from typing import Dict, Any
from app.schemas.response import StandardResponse
from app.schemas.config import FrontendConfig
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=StandardResponse[FrontendConfig])
async def get_config() -> StandardResponse[FrontendConfig]:
    """
    获取前端配置信息

    Returns:
        StandardResponse[Dict[str, Any]]: 前端配置
    """
    config: Dict[str, Any] = {
        "api_base_url": settings.API_V1_STR,
        "model_name_for_display": "Qwen-Turbo (魔搭)",
        # 前端服务使用的端点映射（相对 api_base_url 的路径），来源于环境/配置
        "endpoints": settings.ENDPOINTS,
        "features": {
            "ai_chat": True,
            "knowledge_graph": True,
            "code_testing": True,
            "sentiment_analysis": True,
        },
        "ui": {
            "theme": "light",
            "language": "zh-CN",
        },
    }
    
    return StandardResponse(
        code=200,
        message="Configuration retrieved successfully",
        data=FrontendConfig(**config)
    )