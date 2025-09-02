# backend/app/api/endpoints/behavior.py
"""
API端点，用于接收和处理前端发送的行为事件。
"""
import logging
from fastapi import APIRouter, status

from app.schemas.behavior import BehaviorEvent
from app.tasks.db_tasks import save_behavior_task
from app.tasks.behavior_tasks import interpret_behavior_task

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/log", status_code=status.HTTP_202_ACCEPTED, summary="记录行为事件")
def log_behavior(
    event_in: BehaviorEvent,
):
    """
    接收、异步持久化并异步解释单个行为事件。

    - **异步持久化**: 将原始事件分派到`db_writer_queue`进行持久化。
    - **异步解释**: 将事件分派到`chat_queue`进行解释和状态更新。
    - **快速响应**: 立即返回 `202 Accepted`，不等待后台任务完成。
    """
    logger.info(f"[log_behavior] 接收到的事件: {event_in}")
    
    # 任务1: 异步持久化原始事件 (fire-and-forget)
    logger.info("[log_behavior] 分派到 save_behavior_task")
    save_behavior_task.apply_async(
        args=[event_in.model_dump()], 
        queue='db_writer_queue'
    )

    # 任务2: 异步解释事件 (fire-and-forget)
    logger.info("[log_behavior] 分派到 interpret_behavior_task")
    interpret_behavior_task.apply_async(
        args=[event_in.model_dump()],
        queue='behavior_queue'
    )

    logger.info(f"[log_behavior] 参与者 {event_in.participant_id} 的事件处理已分派")
    return {"status": "事件已接收并正在处理"}
