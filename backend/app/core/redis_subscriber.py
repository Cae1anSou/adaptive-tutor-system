# ws_pubsub.py
import asyncio
import json
from app.config.dependency_injection import get_aioredis
from app.core.websocket_manager import ws_manager
import logging

logger = logging.getLogger(__name__)
async def redis_subscriber():
    try:
        redis = get_aioredis()
        pubsub = redis.pubsub()
        await pubsub.psubscribe("ws:user:*")
        logger.info("已订阅 ws:user:*")

        async for message in pubsub.listen():
            try:
                # 只处理模式消息
                if message["type"] != "pmessage":
                    continue
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                print(channel)
                #channel = message["channel"].decode()  # ws:user:{participant_id}
                raw_data = message["data"]
                print(raw_data)

                try:
                    payload = json.loads(raw_data)
                except json.JSONDecodeError:
                    logger.warning(f"收到非JSON消息: {raw_data} (channel={channel})")
                    continue

                participant_id = channel.split(":")[-1]
                logger.debug(f"准备分发消息给用户 {participant_id}: {payload}")

                # 启动异步任务，防止阻塞主循环
                asyncio.create_task(ws_manager.send_to_user(participant_id, raw_data))

            except Exception as e:
                logger.error(f"处理消息出错: {e}", exc_info=True)

    except Exception as e:
        logger.critical("Redis 订阅器崩溃", exc_info=True)
        # 这里可以考虑重试 / 重连
        await asyncio.sleep(5)
        asyncio.create_task(redis_subscriber())  # 自动重启订阅