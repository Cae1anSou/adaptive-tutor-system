from app.celery_app import celery_app, get_user_state_service
from app.db.database import SessionLocal
from app.schemas.submission import TestSubmissionRequest
from app.services.sandbox_service import sandbox_service
from app.services.content_loader import load_json_content
from app.schemas.user_progress import UserProgressCreate
from app.tasks.db_tasks import save_progress_task
from app.config.dependency_injection import get_redis_client
from app.schemas.chat import ChatRequest,SocketResponse2
from datetime import datetime, timezone

import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.process_submission", bind=True)
def process_submission_task(self, submission_data: dict):
    """
    处理代码提交的重量级任务：评测、更新BKT、触发快照。
    """
    submission_in = TestSubmissionRequest(**submission_data)
    logger.info("处理代码提交任务: %s", submission_in)
    db = SessionLocal()
    user_state_service = get_user_state_service()

    try:
        # 1. 加载测试内容
        try:
            test_task_data = load_json_content("test_tasks", submission_in.topic_id)
            checkpoints = test_task_data.checkpoints
        except Exception as e:
            logger.error(f"Failed to load test content for topic {submission_in.topic_id}: {e}")
            return {"error": f"Topic '{submission_in.topic_id}' not found or invalid."}

        topic_id = submission_in.topic_id
        # 2. 执行代码评测
        evaluation_result = sandbox_service.run_evaluation(
            user_code=submission_in.code.model_dump(),
            checkpoints=checkpoints,
            topic_id=topic_id
        )

        # 3. 异步更新学生模型和快照
        from app.tasks.db_tasks import update_bkt_and_snapshot_task
        update_bkt_and_snapshot_task.apply_async(
            args=[submission_in.participant_id, submission_in.topic_id, evaluation_result["passed"]],
            queue='db_writer_queue'
        )

        # 4. 如果测试通过，异步更新用户进度记录
        if evaluation_result["passed"]:
            progress_data = UserProgressCreate(
                participant_id=submission_in.participant_id,
                topic_id=submission_in.topic_id
            )
            save_progress_task.apply_async(
                args=[progress_data.model_dump()],
                queue='db_writer_queue'
            )
        message = SocketResponse2(
            type="submission_result",
            taskid=self.request.id,
            timestamp=datetime.now(timezone.utc),
            message=evaluation_result,
        )
        redis_client = get_redis_client()
        redis_client.publish(f"ws:user:{submission_data['participant_id']}",  message.model_dump_json())
        logger.info("测评结果已Publish到Redis")

        # 5. 返回评测结果
        return evaluation_result

    except Exception as e:
        logger.error(f"Error processing submission for participant {submission_in.participant_id}: {e}", exc_info=True)
        return {"error": "An internal error occurred during submission processing."}
    finally:
        db.close()