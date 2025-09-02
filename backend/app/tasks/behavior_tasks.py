from app.celery_app import celery_app, get_user_state_service
from app.db.database import SessionLocal
from app.schemas.behavior import BehaviorEvent
from app.services.behavior_interpreter_service import behavior_interpreter_service
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.interpret_behavior")
def interpret_behavior_task(event_data: dict):
    """
    异步解释行为事件
    """
    logger.info(f"[interpret_behavior_task] 接收到的事件数据: {event_data}")
    
    event = BehaviorEvent(**event_data)
    logger.info(f"行为任务: 解释行为事件 - 参与者ID: {event.participant_id}, 事件类型: {event.event_type}, 事件数据: {event.event_data}")
    
    db = SessionLocal()
    user_state_service = get_user_state_service()
    
    try:
        behavior_interpreter_service.interpret_event(
            event=event,
            user_state_service=user_state_service,
            db_session=db
        )
        logger.info(f"行为任务: 成功解释参与者 {event.participant_id} 的行为事件")
    except Exception as e:
        logger.error(f"解释参与者 {event.participant_id} 的事件时出错: {e}", exc_info=True)
    finally:
        db.close()