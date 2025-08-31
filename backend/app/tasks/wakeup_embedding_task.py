from app.celery_app import celery_app
from app.config.dependency_injection import get_rag_service
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.wakeup_embedding_task.wakeup_embedding_model")
def wakeup_embedding_model():
    """
    定时任务：唤醒 embedding 模型，防止其因长时间未使用而休眠。
    """
    try:
        logger.info("Wakeup Task: Starting to wakeup embedding model...")
        rag_service = get_rag_service()
        if rag_service:
            logger.info(f"Wakeup Task: RAG service acquired: {type(rag_service)}")
            # 调用 _get_embedding 方法触发模型加载
            embedding = rag_service._get_embedding("wake-up")
            logger.info(f"Wakeup Task: Embedding model wakeup successful. Embedding length: {len(embedding) if embedding else 'N/A'}")
        else:
            logger.warning("Wakeup Task: RAG service is not available.")
    except Exception as e:
        logger.error(f"Wakeup Task: Failed to wakeup embedding model: {e}", exc_info=True)
        # 重新抛出异常，让Celery记录任务失败
        raise