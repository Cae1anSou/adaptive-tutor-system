from app.celery_app import celery_app, get_user_state_service
from app.db.database import SessionLocal
from app.schemas.behavior import BehaviorEvent
from app.services.behavior_interpreter_service import behavior_interpreter_service
import logging
import json

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.interpret_behavior")
def interpret_behavior_task(event_data: dict):
    """
    异步解释行为事件
    """
    # event = BehaviorEvent(**event_data)
    # logger.info(f"Behavior Task: Interpreting behavior event - participant_id: {event.participant_id}, event_type: {event.event_type}, event_data: {event.event_data}")
    
    # db = SessionLocal()
    # user_state_service = get_user_state_service()
    
    try:
        # 检查必要字段
        if 'participant_id' not in event_data:
            logger.error("解释行为事件失败: 缺少 participant_id")
            return

        event = BehaviorEvent(**event_data)
        logger.info(f"Behavior Task: Interpreting behavior event - participant_id: {event.participant_id}, event_type: {event.event_type}, event_data: {event.event_data}")

        db = SessionLocal()
        user_state_service = get_user_state_service()
        behavior_interpreter_service.interpret_event(
            event=event,
            user_state_service=user_state_service,
            db_session=db
        )
        logger.info(f"Behavior Task: 成功解释用户 {event.participant_id} 的行为事件")
    except Exception as e:
        logger.error(f"解释行为事件失败: {e}")
        # 记录错误数据以便调试
        logger.error(f"错误数据: {json.dumps(event_data, ensure_ascii=False)}")
    finally:
        db.close()