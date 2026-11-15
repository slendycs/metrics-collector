import redis.asyncio as aioredis
from functools import cache
from importlib.resources import files

from ..buffer_client import Buffer
from models import Bid, BidDTO, PutResult


class RedisBuffer(Buffer):
    _SLOTS_KEY = "buffer:slots"
    _ID_KEY = "buffer:bid_id"
    _CHANNEL = "buffer_updated"

    def __init__(self, redis_client:aioredis.Redis, capacity:int) -> None:
        self._redis = redis_client
        self._capacity = capacity

        self._put_script, self._return_script, \
            self._take_next_script = self._register_scripts(self._redis)


    @staticmethod
    @cache
    def _load_script(name: str) -> str:
        return (files("buffer.redis_buffer") / "lua" / f"{name}.lua").read_text(encoding="utf-8")


    def _register_scripts(self, redis_client:aioredis.Redis) -> tuple:
        return (
            redis_client.register_script(self._load_script('put_bid')),
            redis_client.register_script(self._load_script('return_bid')),
            redis_client.register_script(self._load_script('take_next'))
        )

    async def ping(self) -> None:
        """Проверяет доступность Redis."""
        await self._redis.ping()
    
    
    async def aclose(self) -> None:
        """Закрывает пул соединений Redis."""
        await self._redis.aclose()
    

    async def put(self, bid:Bid) -> PutResult:
        """
        Отправляет поступившую заявку в Redis

        Args:
            bid (Bid): Заявка

        Returns:
            PutResult: Данные о результате выполнения операции

        Raises:
            pydantic.ValidationError: Заявку не удалось привести к BidDTO
            redis.exceptions.RedisError: Базовая ошибка Redis: сервер недоступен,
                таймаут, ошибка аутентификации. Команда при этом не выполнена.
            redis.exceptions.ResponseError: Lua-скрипт вернул redis.error_reply
                (например, неизвестный source_type) или упал при выполнении.
                Подкласс RedisError.
        """
        payload = BidDTO.model_validate(bid).model_dump_json()

        accepted, slot, bid_id = await self._put_script(
            keys=[self._SLOTS_KEY, self._ID_KEY],
            args=[self._capacity, bid.source_type.value, payload]
        )

        return PutResult(bool(accepted), slot, bid_id, bid.seq)
    

    async def get_free_space(self) -> int:
        raise NotImplementedError
