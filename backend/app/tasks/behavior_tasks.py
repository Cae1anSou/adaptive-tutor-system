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
    event = BehaviorEvent(**event_data)
    logger.info(f"Behavior Task: Interpreting behavior event - participant_id: {event.participant_id}, event_type: {event.event_type}, event_data: {event.event_data}")
    
    db = SessionLocal()
    user_state_service = get_user_state_service()
    
    try:
        behavior_interpreter_service.interpret_event(
            event=event,
            user_state_service=user_state_service,
            db_session=db
        )
        logger.info(f"Behavior Task: Successfully interpreted behavior event for participant {event.participant_id}")
    except Exception as e:
        logger.error(f"Error interpreting event for participant {event.participant_id}: {e}", exc_info=True)
    finally:
        db.close()