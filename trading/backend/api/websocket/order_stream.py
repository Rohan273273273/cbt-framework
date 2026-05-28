"""WebSocket /ws/orders — streams fill events from Redis pub/sub."""
import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from config import get_settings

logger = logging.getLogger(__name__)


async def order_stream_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    settings = get_settings()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("fills")
    logger.info("Order stream WS connected")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                await websocket.send_json(data)
            except (json.JSONDecodeError, WebSocketDisconnect):
                break
    except WebSocketDisconnect:
        logger.info("Order stream WS disconnected")
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("fills")
        await redis.aclose()
