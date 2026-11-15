import redis

from .buffer_client import BufferClient
from buffer import load_script
from intake.config import settings
from models.buffer import Bid, PutResult


class RedisBuffer(BufferClient):
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._put_script = self._redis.register_script(load_script('put_bid'))

    async def put(self, bid: Bid) -> PutResult:
        raise NotImplementedError

    async def get_free_space(self) -> int:
        raise NotImplementedError
