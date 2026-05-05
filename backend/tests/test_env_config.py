import os
import sys
import pytest

# 将 backend 目录添加到 sys.path 中，便于按项目方式导入
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings

def test_settings_are_loaded_correctly():
    """
    测试关键配置项在 settings 对象中可访问。

    说明：
    1. 项目采用“密钥由外部环境注入”的方式，仓库中不再要求默认密钥非空。
    2. 因此这里只校验字段存在，不强制校验值非空。
    """
    required_attributes = [
        "TUTOR_OPENAI_API_KEY",
        "TUTOR_OPENAI_API_BASE",
        "TUTOR_OPENAI_MODEL",
        "TUTOR_EMBEDDING_API_KEY",
        "TUTOR_TRANSLATION_API_KEY",
    ]

    missing_settings = []
    for attr in required_attributes:
        value = getattr(settings, attr, None)
        if value is None:
            missing_settings.append(attr)

    assert not missing_settings, (
        f"The following required settings are missing in your configuration: {missing_settings}"
    )

if __name__ == "__main__":
    # A simple way to run the check standalone
    try:
        test_settings_are_loaded_correctly()
        print("✅ All required settings are present.")
    except AssertionError as e:
        print(f"❌ Configuration check failed: {e}")
