import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Any
from app.schemas.submission import TestSubmissionRequest, TestSubmissionResponse, TestSubmissionAsyncResponse
from app.tasks.submission_tasks import process_submission_task
from app.celery_app import celery_app
from celery.result import AsyncResult
from app.services.sandbox_service import sandbox_service
from app.services.user_state_service import UserStateService
from app.services.content_loader import load_json_content
from app.config.dependency_injection import get_user_state_service, get_db, get_redis_client
from app.crud.crud_progress import progress as crud_progress
from app.schemas.user_progress import UserProgressCreate
from app.schemas.response import StandardResponse
from app.tasks.db_tasks import save_progress_task, save_code_submission_task

router = APIRouter()

@router.post("/submit-test2", response_model=StandardResponse[TestSubmissionAsyncResponse], status_code=202)
def submit_test2(
    *,
    submission_in: TestSubmissionRequest,
) -> Any:
    """
    接收用户代码提交，异步进行评测，并返回任务ID。
    """
    # 使用Celery队列异步保存用户提交的代码到数据库
    submission_data = {
        "participant_id": submission_in.participant_id,
        "topic_id": submission_in.topic_id,
        "html_code": submission_in.code.html,
        "css_code": submission_in.code.css,
        "js_code": submission_in.code.js
    }
    save_code_submission_task.apply_async(
        args=[submission_data],
        queue='db_writer_queue'
    )
    
    task = process_submission_task.apply_async(
        args=[submission_in.model_dump()],
        queue='submit_queue'
    )
    return StandardResponse(data={"task_id": task.id})

@router.get("/submit-test2/result/{task_id}", response_model=StandardResponse[TestSubmissionResponse])
def get_submission_result(task_id: str) -> Any:
    """
    获取异步代码评测任务的结果。
    """
    task_result = AsyncResult(task_id, app=celery_app)
    if not task_result.ready():
        raise HTTPException(status_code=202, detail={"status": task_result.status})
    
    result = task_result.get()
    if task_result.failed():
        raise HTTPException(status_code=500, detail=result)
        
    return StandardResponse(data=result)

@router.post("/submit-test", response_model=StandardResponse[TestSubmissionResponse])
def submit_test(
        *,
        db: Session = Depends(get_db),
        submission_in: TestSubmissionRequest,
        user_state_service: UserStateService = Depends(lambda: get_user_state_service(get_redis_client()))
) -> Any:
    """
    接收用户代码提交，进行评测，更新BKT模型，并返回结果。
    """
    # 记录提交的代码内容用于调试
    print(f"Received submission for participant {submission_in.participant_id}, topic {submission_in.topic_id}")
    print(f"Submitted code: {submission_in.code}")

    # 使用Celery队列异步保存用户提交的代码到数据库
    submission_data = {
        "participant_id": submission_in.participant_id,
        "topic_id": submission_in.topic_id,
        "html_code": submission_in.code.html,
        "css_code": submission_in.code.css,
        "js_code": submission_in.code.js
    }
    save_code_submission_task.apply_async(
        args=[submission_data],
        queue='db_writer_queue'
    )

    # 1. 加载测试内容
    try:
        test_task_data = load_json_content("test_tasks", submission_in.topic_id)
        checkpoints = test_task_data.checkpoints
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Topic '{submission_in.topic_id}' not found.")
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    # 2. 执行代码评测
    # 注意：这里的sandbox_service是直接导入的单例，如果未来需要更复杂的依赖管理，
    # 也可以像user_state_service一样通过Depends注入。
    evaluation_result = sandbox_service.run_evaluation(
        user_code=submission_in.code.model_dump(),
        checkpoints=checkpoints,
        topic_id=submission_in.topic_id,
    )

    # 3. 更新学生模型
    user_state_service.update_bkt_on_submission(
        participant_id=submission_in.participant_id,
        topic_id=submission_in.topic_id,
        is_correct=evaluation_result["passed"]
    )

    # 4. 触发一次快照检查（可选但推荐）
    # 这确保了BKT模型更新后，状态能及时被保存
    user_state_service.maybe_create_snapshot(submission_in.participant_id, db)

    # 5. 如果测试通过，使用Celery队列异步更新用户进度记录
    if evaluation_result["passed"]:
        progress_data = UserProgressCreate(
            participant_id=submission_in.participant_id,
            topic_id=submission_in.topic_id
        )
        save_progress_task.apply_async(
            args=[progress_data.model_dump()],
            queue='db_writer_queue'
        )

    # 6. 返回评测结果
    return StandardResponse(data=evaluation_result)
