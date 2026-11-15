import json

import allure
import pytest
import redis.asyncio as aioredis
from pydantic import ValidationError
from redis.exceptions import RedisError, ResponseError

from buffer import Buffer, RedisBuffer
from models import Bid, BidDTO, PutResult
from models.enums import ServerTypes


class _StubBuffer(Buffer):
    """Minimal Buffer implementation to exercise the default methods."""

    async def put(self, bid: Bid) -> PutResult:
        return PutResult(True, 1, 1, bid.seq)

    async def get_free_space(self) -> int:
        return 0


class TestScripts:
    @pytest.mark.unit
    @allure.title("Загрузка Lua-скрипта {script_name} возвращает код из пакета [UNIT]")
    @pytest.mark.parametrize(
        ("script_name", "expected"),
        [
            pytest.param("put_bid", "redis.error_reply", id="put-bid"),
            pytest.param("return_bid", "redis.call('HSET'", id="return-bid"),
            pytest.param("take_next", "redis.call('HGETALL'", id="take-next"),
        ],
    )
    def test_load_script_reads_packaged_lua(self, script_name, expected):
        with allure.step(f"Загрузить Lua-скрипт {script_name}"):
            source = RedisBuffer._load_script(script_name)

        with allure.step("Проверить содержимое скрипта"):
            assert expected in source

    @pytest.mark.unit
    @allure.title("Загрузка Lua-скрипта кэшируется [UNIT]")
    def test_load_script_is_cached(self):
        with allure.step("Загрузить один и тот же скрипт дважды"):
            first = RedisBuffer._load_script("put_bid")
            second = RedisBuffer._load_script("put_bid")

        with allure.step("Проверить, что вернулся один и тот же объект"):
            assert first is second

    @pytest.mark.unit
    @allure.title("Конструктор регистрирует три Lua-скрипта в Redis [UNIT]")
    def test_init_registers_scripts(self, fake_redis, scripts):
        with allure.step("Создать RedisBuffer"):
            buffer = RedisBuffer(fake_redis, capacity=3)

        with allure.step("Проверить количество вызовов register_script"):
            assert fake_redis.register_script.call_count == 3

        with allure.step("Проверить, что сохранены зарегистрированные скрипты"):
            assert buffer._put_script is scripts["put_bid"]
            assert buffer._return_script is scripts["return_bid"]
            assert buffer._take_next_script is scripts["take_next"]

    @pytest.mark.unit
    @allure.title("Конструктор сохраняет ёмкость буфера [UNIT]")
    def test_init_keeps_capacity(self, fake_redis):
        with allure.step("Создать RedisBuffer с ёмкостью 7"):
            buffer = RedisBuffer(fake_redis, capacity=7)

        with allure.step("Проверить сохранённую ёмкость"):
            assert buffer._capacity == 7


class TestPut:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("put передаёт в Redis capacity, приоритет и JSON-заявку [UNIT]")
    async def test_put_calls_lua_script_with_expected_arguments(
        self, redis_buffer, scripts, bid
    ):
        with allure.step("Настроить успешный ответ Lua-скрипта"):
            scripts["put_bid"].return_value = [1, 2, 42]

        with allure.step("Поставить заявку в буфер"):
            result = await redis_buffer.put(bid)

        with allure.step("Проверить вызов скрипта с ключами и аргументами"):
            scripts["put_bid"].assert_awaited_once_with(
                keys=["buffer:slots", "buffer:bid_id"],
                args=[3, "test", BidDTO.model_validate(bid).model_dump_json()],
            )

        with allure.step("Проверить результат постановки"):
            assert result == PutResult(True, 2, 42, bid.seq)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("put возвращает отказ, когда буфер заполнен [UNIT]")
    async def test_put_returns_rejection(self, redis_buffer, scripts, bid):
        with allure.step("Настроить ответ Lua-скрипта об отказе"):
            scripts["put_bid"].return_value = [0, -1, 17]

        with allure.step("Поставить заявку в заполненный буфер"):
            result = await redis_buffer.put(bid)

        with allure.step("Проверить отказ и номер заявки"):
            assert result.accepted is False
            assert result.slot == -1
            assert result.bid_id == 17
            assert result.seq == bid.seq

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("put приводит числовой accepted из Redis к bool [UNIT]")
    async def test_put_coerces_accepted_to_bool(self, redis_buffer, scripts, bid):
        with allure.step("Настроить числовой ответ Lua-скрипта"):
            scripts["put_bid"].return_value = [1, "3", "8"]

        with allure.step("Поставить заявку в буфер"):
            result = await redis_buffer.put(bid)

        with allure.step("Проверить приведённые значения"):
            assert result.accepted is True
            assert result.slot == "3"
            assert result.bid_id == "8"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("put отклоняет заявку с некорректными метриками [UNIT]")
    async def test_put_rejects_invalid_bid(
        self, redis_buffer, scripts, bid_factory
    ):
        with allure.step("Создать заявку с невалидными метриками"):
            bid = bid_factory(stats=None)

        with allure.step("Попытаться поставить заявку"):
            with pytest.raises(ValidationError):
                await redis_buffer.put(bid)

        with allure.step("Проверить, что Lua-скрипт не вызывался"):
            scripts["put_bid"].assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("put пробрасывает ошибку Redis [UNIT]")
    async def test_put_propagates_redis_error(self, redis_buffer, scripts, bid):
        with allure.step("Смоделировать ошибку Redis в Lua-скрипте"):
            scripts["put_bid"].side_effect = RedisError("connection lost")

        with allure.step("Поставить заявку и ожидать исключение"):
            with pytest.raises(RedisError, match="connection lost"):
                await redis_buffer.put(bid)


class TestConnection:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("ping проверяет соединение с Redis [UNIT]")
    async def test_ping_delegates_to_redis(self, redis_buffer, fake_redis):
        with allure.step("Вызвать ping буфера"):
            await redis_buffer.ping()

        with allure.step("Проверить вызов Redis"):
            fake_redis.ping.assert_awaited_once_with()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("aclose закрывает соединение с Redis [UNIT]")
    async def test_aclose_closes_redis(self, redis_buffer, fake_redis):
        with allure.step("Вызвать aclose буфера"):
            await redis_buffer.aclose()

        with allure.step("Проверить закрытие Redis"):
            fake_redis.aclose.assert_awaited_once_with()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("ping базового Buffer по умолчанию ничего не делает [UNIT]")
    async def test_base_buffer_ping_is_noop(self):
        with allure.step("Вызвать ping заглушки Buffer"):
            result = await _StubBuffer().ping()

        with allure.step("Проверить отсутствие результата"):
            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("aclose базового Buffer по умолчанию ничего не делает [UNIT]")
    async def test_base_buffer_aclose_is_noop(self):
        with allure.step("Вызвать aclose заглушки Buffer"):
            result = await _StubBuffer().aclose()

        with allure.step("Проверить отсутствие результата"):
            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("get_free_space пока не реализован [UNIT]")
    async def test_get_free_space_is_not_implemented(self, redis_buffer):
        with allure.step("Вызвать get_free_space"):
            with pytest.raises(NotImplementedError):
                await redis_buffer.get_free_space()


class TestRedisIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("put сохраняет заявку в реальный Redis [INTEGRATION]")
    async def test_put_stores_bid_in_real_redis(
        self, real_redis, real_buffer_factory, bid
    ):
        with allure.step("Создать буфер с реальным Redis и поставить заявку"):
            buffer = real_buffer_factory(capacity=2)
            result = await buffer.put(bid)

        with allure.step("Проверить результат постановки"):
            assert result == PutResult(True, 1, 1, bid.seq)

        with allure.step("Проверить слот и счётчик заявок в Redis"):
            raw_envelope = await real_redis.hget("buffer:slots", "1")
            assert raw_envelope is not None
            assert await real_redis.get("buffer:bid_id") == "1"

        with allure.step("Проверить сохранённый конверт заявки"):
            envelope = json.loads(raw_envelope)
            assert envelope["id"] == 1
            assert envelope["prio"] == 3
            assert json.loads(envelope["payload"]) == json.loads(
                BidDTO.model_validate(bid).model_dump_json()
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title(
        "put заполняет буфер и отказывает заявке за пределами ёмкости [INTEGRATION]"
    )
    async def test_put_rejects_bid_when_buffer_is_full(
        self, real_redis, real_buffer_factory, bid_factory
    ):
        with allure.step("Заполнить буфер ёмкостью 2 двумя заявками"):
            buffer = real_buffer_factory(capacity=2)
            first = await buffer.put(bid_factory(seq=1))
            second = await buffer.put(bid_factory(seq=2))

        with allure.step("Поставить третью заявку в заполненный буфер"):
            rejected = await buffer.put(bid_factory(seq=3))

        with allure.step("Проверить успешные постановки и отказ"):
            assert (first.accepted, first.slot, first.bid_id) == (True, 1, 1)
            assert (second.accepted, second.slot, second.bid_id) == (True, 2, 2)
            assert (rejected.accepted, rejected.slot, rejected.bid_id) == (
                False,
                -1,
                3,
            )

        with allure.step("Проверить, что буфер не изменился после отказа"):
            assert await real_redis.hlen("buffer:slots") == 2
            assert await real_redis.get("buffer:bid_id") == "3"

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("put занимает первое освободившееся место [INTEGRATION]")
    async def test_put_reuses_first_free_slot(
        self, real_redis, real_buffer_factory, bid_factory
    ):
        with allure.step("Занять оба слота буфера"):
            buffer = real_buffer_factory(capacity=2)
            await buffer.put(bid_factory(seq=1))
            await buffer.put(bid_factory(seq=2))

        with allure.step("Освободить первый слот"):
            await real_redis.hdel("buffer:slots", "1")

        with allure.step("Поставить новую заявку"):
            result = await buffer.put(bid_factory(seq=3))

        with allure.step("Проверить повторное использование первого слота"):
            assert (result.accepted, result.slot, result.bid_id) == (True, 1, 3)

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("put сохраняет приоритет источника {source_type} [INTEGRATION]")
    @pytest.mark.parametrize(
        ("source_type", "expected_priority"),
        [
            pytest.param(ServerTypes.PRODUCTION, 1, id="production"),
            pytest.param(ServerTypes.STAGING, 2, id="staging"),
            pytest.param(ServerTypes.TEST, 3, id="test"),
        ],
    )
    async def test_put_stores_source_priority(
        self, real_redis, real_buffer_factory, bid_factory, source_type, expected_priority
    ):
        with allure.step("Поставить заявку от источника с заданным типом"):
            buffer = real_buffer_factory(capacity=1)
            await buffer.put(bid_factory(source_type=source_type))

        with allure.step("Прочитать приоритет из конверта в Redis"):
            raw_envelope = await real_redis.hget("buffer:slots", "1")
            assert raw_envelope is not None
            envelope = json.loads(raw_envelope)

        with allure.step("Проверить приоритет источника"):
            assert envelope["prio"] == expected_priority

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("return_bid занимает первый свободный слот и сообщает о полном буфере [INTEGRATION]")
    async def test_return_bid_stores_envelope(
        self, real_redis, real_buffer_factory
    ):
        with allure.step("Вернуть две заявки в буфер ёмкостью 2"):
            buffer = real_buffer_factory(capacity=2)
            first = await buffer._return_script(
                keys=["buffer:slots"],
                args=[2, "5", "production", '{"source": "production"}'],
            )
            second = await buffer._return_script(
                keys=["buffer:slots"],
                args=[2, "6", "staging", '{"source": "staging"}'],
            )

        with allure.step("Попытаться вернуть третью заявку"):
            rejected = await buffer._return_script(
                keys=["buffer:slots"],
                args=[2, "7", "test", '{"source": "test"}'],
            )

        with allure.step("Проверить номера слотов и отказ"):
            assert (first, second, rejected) == (1, 2, 0)

        with allure.step("Проверить сохранённый конверт первой заявки"):
            envelope = json.loads(await real_redis.hget("buffer:slots", "1"))
            assert envelope["id"] == 5
            assert envelope["prio"] == 1
            assert envelope["payload"] == '{"source": "production"}'

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("return_bid отклоняет неизвестный тип источника [INTEGRATION]")
    async def test_return_bid_rejects_unknown_source_type(
        self, real_buffer_factory
    ):
        with allure.step("Вернуть заявку с неизвестным source_type"):
            buffer = real_buffer_factory(capacity=1)

            with pytest.raises(ResponseError, match="unknown source_type"):
                await buffer._return_script(
                    keys=["buffer:slots"],
                    args=[1, "1", "unknown", "{}"],
                )

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("take_next возвращает None для пустого буфера [INTEGRATION]")
    async def test_take_next_returns_none_for_empty_buffer(
        self, real_buffer_factory
    ):
        with allure.step("Забрать заявку из пустого буфера"):
            buffer = real_buffer_factory(capacity=1)
            result = await buffer._take_next_script(keys=["buffer:slots"])

        with allure.step("Проверить пустой результат"):
            assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title(
        "take_next выбирает заявки по приоритету источника, затем по id [INTEGRATION]"
    )
    async def test_take_next_orders_by_priority_and_id(
        self, real_redis, real_buffer_factory
    ):
        with allure.step("Вернуть заявки разных источников в обратном порядке приоритета"):
            buffer = real_buffer_factory(capacity=4)
            await buffer._return_script(
                keys=["buffer:slots"],
                args=[4, "10", "test", '"test"'],
            )
            await buffer._return_script(
                keys=["buffer:slots"],
                args=[4, "11", "staging", '"staging"'],
            )
            await buffer._return_script(
                keys=["buffer:slots"],
                args=[4, "12", "production", '"production-old"'],
            )
            await buffer._return_script(
                keys=["buffer:slots"],
                args=[4, "13", "production", '"production-new"'],
            )

        with allure.step("Забрать все заявки из буфера"):
            taken = [
                await buffer._take_next_script(keys=["buffer:slots"])
                for _ in range(4)
            ]

        with allure.step("Проверить порядок выбора заявок"):
            assert [item[1] for item in taken] == [13, 12, 11, 10]
            assert [json.loads(item[2]) for item in taken] == [
                "production-new",
                "production-old",
                "staging",
                "test",
            ]

        with allure.step("Проверить, что буфер опустел"):
            assert await real_redis.hlen("buffer:slots") == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("ping и aclose работают с реальным Redis [INTEGRATION]")
    async def test_ping_and_aclose_with_real_redis(self, redis_url):
        with allure.step("Подключиться к реальному Redis"):
            client = aioredis.from_url(redis_url, decode_responses=True)
            buffer = RedisBuffer(client, capacity=1)

        with allure.step("Проверить доступность через ping"):
            await buffer.ping()

        with allure.step("Закрыть соединение через aclose"):
            await buffer.aclose()
