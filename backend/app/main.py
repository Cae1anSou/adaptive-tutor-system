import uvicorn
import os
import pytz
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.core.config import settings
import asyncio
from contextlib import asynccontextmanager
#from app.api import socket_router 
from app.core.redis_subscriber import redis_subscriber
import logging

# 设置时区为上海
os.environ['TZ'] = 'Asia/Shanghai'

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    在应用生命周期里启动 redis_subscriber 作为后台任务，并在关闭时取消它。
    保证订阅器和 ws_manager 在同一进程内。
    """
    # 启动订阅协程（不会阻塞主线程）
    logging.info("启动 Redis 订阅器任务")
    app.state.redis_task = asyncio.create_task(redis_subscriber())

    try:
        yield
    finally:
        # 关闭时取消任务并等待其结束
        logging.info("取消 Redis 订阅器任务")
        task = getattr(app.state, "redis_task", None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logging.info("Redis 订阅器已取消")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
    ,lifespan=lifespan
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
#app.include_router(socket_router.ws_router, prefix="/ws", tags=["ws"])


if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=settings.BACKEND_PORT,
        reload=True
    )