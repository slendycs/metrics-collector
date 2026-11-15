from .buffer_client import BufferClient

from intake.config import settings
from models.buffer import Bid, PutResult


class RedisBuffer(BufferClient):
    async def put(self, bid: Bid) -> PutResult:
        raise NotImplementedError

    async def get_free_space(self) -> int:
        raise NotImplementedError
