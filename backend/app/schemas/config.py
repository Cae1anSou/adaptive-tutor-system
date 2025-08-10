# backend/app/schemas/config.py
from pydantic import BaseModel
from typing import Dict, Any, Optional

class FrontendConfig(BaseModel):
    """
    面向前端暴露的非敏感配置。

    注意：所有 endpoints 为相对 api_base_url 的路径片段，由前端在运行时拼接。
    """
    # API 基础 URL
    api_base_url: str

    # 端点映射
    endpoints: Dict[str, str] = {}

    # 可选：在前端显示的模型名等信息
    model_name_for_display: Optional[str] = None

    # 可选：功能开关集合
    features: Dict[str, bool] = {}

    # 可选：UI 配置集合
    ui: Dict[str, Any] = {}
