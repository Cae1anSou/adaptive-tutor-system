import logging
from app.celery_app import celery_app, get_dynamic_controller
from app.db.database import SessionLocal
from app.schemas.chat import ChatRequest,SocketResponse2
from app.config.dependency_injection import get_redis_client
from datetime import datetime, timezone
import json

logger=logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_chat_request(self,request_data: dict):
    db = SessionLocal()
    try:
        controller = get_dynamic_controller()
        # 将 db 会话传递给需要它的服务方法
        # 调用生成回复（使用同步函数）
        request_obj = ChatRequest(**request_data)
        redis_client = get_redis_client()
        # stream_start
        message = SocketResponse2(
                type="stream_start",
                taskid=self.request.id,
                timestamp=datetime.now(timezone.utc),
                message="开始",
            )
        redis_client.publish(f"ws:user:{request_data['participant_id']}",  message.model_dump_json() )    
        #streaming
        for trunk in controller.generate_adaptive_response_sync(
            request=request_obj,
            db=db,
            background_tasks=None  # Celery任务中不使用FastAPI的BackgroundTasks
        ):
        # 注意：响应结果会自动存储在Celery的result backend中
            message = SocketResponse2(
                type="streaming",
                taskid=self.request.id,
                timestamp=datetime.now(timezone.utc),
                message=trunk,
            )
            redis_client.publish(f"ws:user:{request_data['participant_id']}",  message.model_dump_json() )
        #stream_end
        message = SocketResponse2(
            type="stream_end",
            taskid=self.request.id,
            timestamp=datetime.now(timezone.utc),
            message="结束",
        )
        redis_client.publish(f"ws:user:{request_data['participant_id']}",  message.model_dump_json() )
        #logger.info("已public到Redis")
        #return response.model_dump()
    finally:
        db.close()