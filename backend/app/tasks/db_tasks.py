import logging

from app.celery_app import celery_app, get_user_state_service
from app.db.database import SessionLocal
from app.crud.crud_event import event as crud_event
from app.crud.crud_chat_history import chat_history as crud_chat_history
from app.crud.crud_progress import progress as crud_progress
from app.crud.crud_submission import submission as crud_submission
from app.schemas.behavior import BehaviorEvent
from app.schemas.chat import ChatHistoryCreate
from app.schemas.user_progress import UserProgressCreate
from app.schemas.submission import SubmissionCreate

logger = logging.getLogger(__name__)

@celery_app.task(name='app.tasks.db_tasks.update_bkt_and_snapshot_task')
def update_bkt_and_snapshot_task(participant_id: str, topic_id: str, is_correct: bool):
    """一个专门用于更新BKT模型并可能创建快照的任务"""
    db = SessionLocal()
    user_state_service = get_user_state_service()
    try:
        # 更新BKT模型
        user_state_service.update_bkt_on_submission(
            participant_id=participant_id,
            topic_id=topic_id,
            is_correct=is_correct
        )
        # 触发快照检查
        user_state_service.maybe_create_snapshot(participant_id, db)
    finally:
        db.close()


@celery_app.task(name='app.tasks.db_tasks.save_progress_task')
def save_progress_task(progress_data: dict):
    """一个专门用于保存用户进度数据的轻量级任务"""
    db = SessionLocal()
    try:
        # 创建用户进度记录
        progress_in = UserProgressCreate(**progress_data)
        crud_progress.create(db=db, obj_in=progress_in)
    finally:
        db.close()

@celery_app.task(name='app.tasks.db_tasks.save_code_submission_task')
def save_code_submission_task(submission_data: dict):
    """一个专门用于保存代码提交记录的轻量级任务"""
    db = SessionLocal()
    try:
        # 创建代码提交记录
        submission_in = SubmissionCreate(**submission_data)
        crud_submission.create(db=db, obj_in=submission_in)
    finally:
        db.close()

@celery_app.task(name='app.tasks.db_tasks.save_behavior_task')
def save_behavior_task(behavior_data: dict):
    """一个专门用于保存 behavior 数据的轻量级任务"""
    db = SessionLocal()
    try:
        # 创建行为事件记录
        behavior_event = BehaviorEvent(**behavior_data)
        logger.info(f"DB Task: Saving behavior event - participant_id: {behavior_event.participant_id}, event_type: {behavior_event.event_type}, event_data: {behavior_event.event_data}")
        crud_event.create_from_behavior(db=db, obj_in=behavior_event)
        logger.info(f"DB Task: Successfully saved behavior event for participant {behavior_event.participant_id}")
    except Exception as e:
        logger.error(f"DB Task: Error saving behavior event: {e}")
        raise
    finally:
        db.close()

@celery_app.task(name='app.tasks.db_tasks.log_ai_event_task')
def log_ai_event_task(event_data: dict):
    """一个专门用于记录AI交互事件的轻量级任务"""
    db = SessionLocal()
    try:
        # 创建AI交互事件记录
        behavior_event = BehaviorEvent(**event_data)
        crud_event.create_from_behavior(db=db, obj_in=behavior_event)
    finally:
        db.close()

@celery_app.task(name='app.tasks.db_tasks.save_chat_message_task')
def save_chat_message_task(chat_data: dict):
    """一个专门用于保存聊天记录的轻量级任务"""
    db = SessionLocal()
    try:
        # 创建聊天记录
        chat_history_in = ChatHistoryCreate(**chat_data)
        crud_chat_history.create(db=db, obj_in=chat_history_in)
    finally:
        db.close()