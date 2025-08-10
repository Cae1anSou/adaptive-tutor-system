# backend/app/services/content_loader.py
import json
from pathlib import Path
from fastapi import HTTPException
from functools import lru_cache
from typing import Union

from app.core.config import settings
from app.schemas.content import (
    LearningContent, 
    TestTask,
    AssertAttributeCheckpoint,
    AssertStyleCheckpoint,
    AssertTextContentCheckpoint,
    CustomScriptCheckpoint,
    InteractionAndAssertCheckpoint,
    BaseCheckpoint
)
# 从配置中获取data目录路径
DATA_DIR = Path(settings.DATA_DIR)

# 使用LRU缓存来避免重复读取文件，提升性能
@lru_cache(maxsize=128)
def load_json_content(content_type: str, topic_id: str) -> Union[LearningContent, TestTask]:
    """
    一个带缓存的函数，用于从JSON文件中加载内容。 
    content_type 应该是 'learning_content' 或 'test_tasks'。
    """
    content_file = DATA_DIR / content_type / f"{topic_id}.json"
    if not content_file.exists():
        raise HTTPException(status_code=404, detail=f"未找到主题'{topic_id}'的{content_type}。")

    with open(content_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 根据content_type返回相应的Pydantic模型实例
    if content_type == "learning_content":
        return LearningContent(**data)
    elif content_type == "test_tasks":
        # 处理检查点类型
        if "checkpoints" in data:
            processed_checkpoints = []
            for checkpoint_data in data["checkpoints"]:
                checkpoint_type = checkpoint_data.get("type")
                if checkpoint_type == "assert_attribute":
                    processed_checkpoints.append(AssertAttributeCheckpoint(**checkpoint_data))
                elif checkpoint_type == "assert_style":
                    processed_checkpoints.append(AssertStyleCheckpoint(**checkpoint_data))
                elif checkpoint_type == "assert_text_content":
                    processed_checkpoints.append(AssertTextContentCheckpoint(**checkpoint_data))
                elif checkpoint_type == "custom_script":
                    processed_checkpoints.append(CustomScriptCheckpoint(**checkpoint_data))
                elif checkpoint_type == "interaction_and_assert":
                    # 递归处理嵌套的断言
                    if "assertion" in checkpoint_data and checkpoint_data["assertion"]:
                        assertion_data = checkpoint_data["assertion"]
                        assertion_type = assertion_data.get("type")
                        if assertion_type == "assert_attribute":
                            checkpoint_data["assertion"] = AssertAttributeCheckpoint(**assertion_data)
                        elif assertion_type == "assert_style":
                            checkpoint_data["assertion"] = AssertStyleCheckpoint(**assertion_data)
                        elif assertion_type == "assert_text_content":
                            checkpoint_data["assertion"] = AssertTextContentCheckpoint(**assertion_data)
                        elif assertion_type == "custom_script":
                            checkpoint_data["assertion"] = CustomScriptCheckpoint(**assertion_data)
                        elif assertion_type == "interaction_and_assert":
                            # 对于嵌套的interaction_and_assert，我们需要递归处理
                            # 这里简化处理，实际项目中可能需要更复杂的递归逻辑
                            checkpoint_data["assertion"] = InteractionAndAssertCheckpoint(**assertion_data)
                    processed_checkpoints.append(InteractionAndAssertCheckpoint(**checkpoint_data))
                else:
                    # 如果类型未知，使用基类
                    processed_checkpoints.append(BaseCheckpoint(**checkpoint_data))
            data["checkpoints"] = processed_checkpoints
        return TestTask(**data)
    else:
        raise ValueError(f"不支持的content_type: {content_type}")