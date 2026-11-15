import redis.asyncio as aioredis
from fastapi import Request

from buffer import Buffer, RedisBuffer
from models import BufferTypes

from .config import settings


def create_buffer() -> Buffer:
    """Создаёт буфер указанного в конфигурации типа.

    Returns:
        Buffer: Объект для работы с буфером.

    Raises:
        ValueError: Если тип буфера не поддерживается или не задан redis_url.
    """
    if settings.buffer_type == BufferTypes.REDIS:
        if settings.redis_url is None:
            raise ValueError('redis_url is required for the Redis buffer')

        redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
        return RedisBuffer(redis_client, settings.buffer_capacity)

    raise ValueError(f'Unsupported buffer type: {settings.buffer_type}')


def get_buffer(request: Request) -> Buffer:
    """FastAPI-зависимость: отдаёт буфер, созданный в lifespan."""
    return request.app.state.buffer
