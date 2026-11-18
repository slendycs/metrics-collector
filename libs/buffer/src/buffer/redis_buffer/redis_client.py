import redis.asyncio as aioredis
from redis.exceptions import TimeoutError, ConnectionError, ResponseError, RedisError
from functools import cache
from importlib.resources import files

from ..buffer_client import Buffer
from ..buffer_errors import BufferException, BufferTimeoutError, \
                             BufferConnectionError, BufferResponseError
from models import Bid, BidDTO, PutResult


class RedisBuffer(Buffer):
    _SLOTS_KEY = "buffer:slots"
    _ID_KEY = "buffer:bid_id"
    _CHANNEL = "buffer_updated"


    def __init__(self, redis_client: aioredis.Redis, capacity: int) -> None:
        """Создаёт буфер поверх готового Redis-клиента

        Args:
            redis_client: Асинхронный клиент Redis; владельцем пула остаётся вызывающая сторона (она же обязана вызвать :meth:`aclose`)
            capacity: Максимальное количество заявок в буфере.

        Raises:
            FileNotFoundError: Lua-скрипты не найдены в пакете
                (повреждённая установка `buffer`).
        """
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
        """
        Проверяет доступность Redis

        Raises:
            BufferConnectionError: Не удалось установить соединение: сервер недоступен, неверный хост/порт, обрыв или ошибка аутентификации
            BufferTimeoutError: Сервер не ответил за время, заданное `socket_timeout`/`socket_connect_timeout`
            BufferResponseError: Сервер вернул ошибку на `PING` (например, `LOADING` при загрузке данных)
            BufferException: Любая другая ошибка Redis, не попавшая в подклассы выше
        """
        try:
            await self._redis.ping()
        except TimeoutError as err:
            raise BufferTimeoutError(str(err)) from err
        except ConnectionError as err:
            raise BufferConnectionError(str(err)) from err
        except ResponseError as err:
            raise BufferResponseError(str(err)) from err
        except RedisError as err:
            raise BufferException(str(err)) from err


    async def aclose(self) -> None:
        """Закрывает пул соединений Redis"""
        await self._redis.aclose()
    

    async def put(self, bid:Bid, seq:int) -> PutResult:
        """
        Отправляет поступившую заявку в Redis

        Args:
            bid (Bid): Заявка
            seq (int): Порядковый номер заявки от конкретного агента

        Returns:
            PutResult: Данные о результате выполнения операции

        Raises:
            pydantic.ValidationError: Заявку не удалось привести к BidDTO (некорректные типы полей или ``stats``).
            BufferTimeoutError: Ответ не получен за время, заданное `socket_timeout`
            BufferConnectionError: Соединение не установлено или потеряно: сервер недоступен, неверный хост/порт, обрыв, ошибка аутентификации
            BufferResponseError: Lua-скрипт вернул `redis.error_reply` (например, неизвестный `source_type`) или упал при выполнении
            BufferException: Любая другая ошибка Redis, не попавшая в подклассы выше
        """
        payload = BidDTO.model_validate(bid).model_dump_json()
        try:
            accepted, slot, bid_id = await self._put_script(
                keys=[self._SLOTS_KEY, self._ID_KEY],
                args=[self._capacity, bid.source_type.value, payload]
            )
        except TimeoutError as err:
            raise BufferTimeoutError(str(err)) from err
        except ConnectionError as err:
            raise BufferConnectionError(str(err)) from err
        except ResponseError as err:
            raise BufferResponseError(str(err)) from err
        except RedisError as err:
            raise BufferException(str(err)) from err

        return PutResult(
            accepted=bool(accepted),
            slot=int(slot) if accepted else None,
            bid_id=int(bid_id),
            seq=seq,
            source_name=bid.source_name,
            source_type=bid.source_type
        )
