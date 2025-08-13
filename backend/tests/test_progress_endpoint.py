import os
import sys
from unittest.mock import MagicMock
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# 确保可以以 `from app...` 导入
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.crud import crud_progress


def create_test_app():
    # 伪造 app.config.dependency_injection，避免导入真实依赖（会触发 settings 校验等副作用）
    fake_di = types.ModuleType("app.config.dependency_injection")
    def _fake_db():
        yield MagicMock()
    setattr(fake_di, "get_db", _fake_db)

    # 在导入 progress 路由前注入假的模块
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, "app.config.dependency_injection", fake_di)
        from app.api.endpoints.progress import router as progress_router  # type: ignore

        app = FastAPI()
        app.include_router(progress_router, prefix="/progress")
        return app


@pytest.fixture
def client():
    app = create_test_app()
    return TestClient(app)


def test_get_user_progress_success(client, monkeypatch):
    # 模拟 CRUD 返回
    monkeypatch.setattr(
        crud_progress.progress,
        "get_completed_topics_by_user",
        MagicMock(return_value=["topic1", "topic2"]),
    )

    resp = client.get("/progress/participants/u123/progress")
    assert resp.status_code == 200
    body = resp.json()

    # 标准响应结构
    assert body["code"] == 200
    assert body["message"] == "success"
    assert body["data"]["completed_topics"] == ["topic1", "topic2"]


def test_get_user_progress_internal_error(client, monkeypatch):
    # 让 CRUD 抛出异常触发 500 分支
    def _raise(*args, **kwargs):
        raise Exception("db error")

    monkeypatch.setattr(
        crud_progress.progress,
        "get_completed_topics_by_user",
        _raise,
    )

    resp = client.get("/progress/participants/u123/progress")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"].startswith("Internal server error:")


