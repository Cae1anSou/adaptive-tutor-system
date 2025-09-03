import logging
from celery import Celery, signals
from app.core.config import settings
from app.config.dependency_injection import create_dynamic_controller, get_redis_client, get_user_state_service as create_user_state_service
import os

# 配置日志记录器
logger = logging.getLogger(__name__)

# 创建 Celery 应用实例
celery_app = Celery(
    "adaptive_tutor_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks",
        "app.tasks.chat_tasks",
        "app.tasks.behavior_tasks",
        "app.tasks.db_tasks",
        "app.tasks.submission_tasks",
        "app.tasks.wakeup_embedding_task"
    ]
)

# 全局变量，用于在单个 Worker 进程中存储依赖实例
_dynamic_controller_instance = None
_user_state_service_instance = None

@signals.worker_process_init.connect
def init_worker_process(sender=None, **kwargs):
    """
    在 Worker 进程启动时，根据其监听的队列有条件地初始化依赖。
    """
    global _dynamic_controller_instance, _user_state_service_instance
    
    # 1. 初始化所有 Worker 都需要的轻量级服务
    if _user_state_service_instance is None:
        logger.info(f"Initializing UserStateService for Worker (PID: {os.getpid()})...")
        redis_client = get_redis_client()
        _user_state_service_instance = create_user_state_service(redis_client=redis_client)
        logger.info("UserStateService initialized.")

    # 2. 获取 Worker 实例正在监听的队列名称集合
    # 通过检查当前进程的命令行参数来确定队列
    import sys
    queues = set()
    
    # 从命令行参数中提取队列信息
    for i, arg in enumerate(sys.argv):
        if arg == '-Q' and i + 1 < len(sys.argv):
            queues_str = sys.argv[i + 1]
            queues.update(q.strip() for q in queues_str.split(','))
        elif arg.startswith('--queues='):
            queues_str = arg.split('=', 1)[1]
            queues.update(q.strip() for q in queues_str.split(','))
    
    # 如果没有从命令行参数中获取到队列信息，使用默认方法
    if not queues and sender is not None and hasattr(sender, 'options'):
        queues = {q.name for q in sender.options.get('queues', [])}
    
    # 如果仍然没有队列信息，尝试从环境变量获取
    if not queues:
        queue_env = os.environ.get('CELERY_QUEUES')
        if queue_env:
            queues.update(q.strip() for q in queue_env.split(','))
    
    # 3. 只有当 Worker 明确服务于 'chat_queue' 时，才初始化重量级依赖
    if 'chat_queue' in queues:
        if _dynamic_controller_instance is None:
            logger.info(f"Initializing DynamicController for Chat Worker (PID: {os.getpid()})...")
            # UserStateService 已经初始化，直接从 DynamicController 中使用
            # 注意：create_dynamic_controller 内部会创建自己的 UserStateService 实例
            redis_client = get_redis_client()
            _dynamic_controller_instance = create_dynamic_controller(redis_client=redis_client)
            logger.info("DynamicController initialized.")

            # 预加载RAG服务（如果启用）现在不需要，因为我们有一个专门的beat来完成这个
            # try:
            #     from app.config.dependency_injection import get_rag_service
            #     rag_service = get_rag_service()
            #     if rag_service:
            #         logger.info("RAG service preloaded in worker")
            #         # 预热embedding模型，避免第一次调用时的冷启动延迟
            #         try:
            #             logger.info("Warming up embedding model...")
            #             rag_service._get_embedding("warm-up")
            #             logger.info("Embedding model is warm.")
            #         except Exception as warmup_error:
            #             logger.warning(f"Failed to warm up embedding model: {warmup_error}")
            # except Exception as e:
            #     logger.error(f"Failed to preload RAG service: {e}")

    else:
        logger.info(f"Worker (PID: {os.getpid()}) is not serving 'chat_queue'. Skipping DynamicController initialization.")

def get_dynamic_controller():
    """
    在 Celery 任务中获取 DynamicController 实例。
    
    重要: 此函数只应在路由到 'chat_queue' 的任务中调用。
    """
    global _dynamic_controller_instance
    if _dynamic_controller_instance is None:
        raise RuntimeError(
            "DynamicController not initialized. This function should only be called "
            "from tasks routed to the 'chat_queue'."
        )
    return _dynamic_controller_instance

def get_user_state_service():
    """
    在 Celery 任务中获取 UserStateService 实例。
    """
    global _user_state_service_instance
    if _user_state_service_instance is None:
        raise RuntimeError("UserStateService not initialized.")
    return _user_state_service_instance

# Celery 配置
celery_app.conf.update(
    # 任务序列化格式
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 队列配置
    task_routes={
        'app.tasks.chat_tasks.process_chat_request': {'queue': 'chat_queue'},
        'app.tasks.behavior_tasks.interpret_behavior_task': {'queue': 'behavior_queue'},
        'app.tasks.submission_tasks.process_submission_task': {'queue': 'submit_queue'},
        'app.tasks.db_tasks.save_submission_task': {'queue': 'db_writer_queue'},
        'app.tasks.db_tasks.save_behavior_task': {'queue': 'db_writer_queue'},
        'app.tasks.db_tasks.log_ai_event_task': {'queue': 'db_writer_queue'},
        'app.tasks.db_tasks.save_chat_message_task': {'queue': 'db_writer_queue'},
        'app.tasks.wakeup_embedding_task.wakeup_embedding_model': {'queue': 'db_writer_queue'},
    },
    task_default_queue='default',
    
    # 定时任务配置
    beat_schedule={
        'wakeup-embedding-model': {
            'task': 'app.tasks.wakeup_embedding_task.wakeup_embedding_model',
            'schedule': 300.0,  # 每300秒（5分钟）执行一次
        },
    },
)