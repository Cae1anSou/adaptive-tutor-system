from fastapi import APIRouter, HTTPException
import json
import os
from app.schemas.knowledge_graph import KnowledgeGraphResponse, KnowledgeGraph
from app.core.config import settings
from app.schemas.response import StandardResponse

router = APIRouter()

# 使用配置中的DATA_DIR确保路径正确
GRAPH_FILE_PATH = os.path.join(settings.DATA_DIR, "knowledge_graph.json")

_knowledge_graph_cache = None

@router.get("", response_model=KnowledgeGraphResponse)  # 空路径，因为路由前缀会在api.py中定义
def get_knowledge_graph():
    global _knowledge_graph_cache

    if _knowledge_graph_cache is None:
        try:
            with open(GRAPH_FILE_PATH, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
                # 使用Pydantic模型验证和结构化数据
                _knowledge_graph_cache = KnowledgeGraph(**graph_data)
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="知识图谱数据文件未找到")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"知识图谱加载失败: {str(e)}")

    return StandardResponse(data=_knowledge_graph_cache)
