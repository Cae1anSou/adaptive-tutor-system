from fastapi import APIRouter, HTTPException
from app.schemas.response import StandardResponse
from app.schemas.content import LearningContent, TestTask
from app.services.content_loader import load_json_content

# 使用前缀统一版本管理,可修改
router = APIRouter()


@router.get("/learning-content/{topic_id}", response_model=StandardResponse[LearningContent])
def get_learning_content(topic_id: str):
    """
    获取指定主题的学习材料。
    """
    try:
        content_data = load_json_content("learning_content", topic_id)
        return StandardResponse(data=content_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/test-tasks/{topic_id}", response_model=StandardResponse[TestTask])
def get_test_task(topic_id: str):
    """
    获取指定主题的测试任务。
    """
    try:
        content_data = load_json_content("test_tasks", topic_id)
        return StandardResponse(data=content_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")