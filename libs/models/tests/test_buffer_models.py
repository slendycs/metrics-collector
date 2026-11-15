from datetime import datetime

import allure
import pytest
from pydantic import ValidationError

from models import Bid, BidDTO, Metrics, PutResult
from models.buffer import PutResultDTO
from models.enums import BufferTypes, ServerTypes


class TestBufferModels:
    @pytest.mark.unit
    @allure.title("Справочник BufferTypes содержит Redis [UNIT]")
    def test_buffer_types_values(self):
        with allure.step("Сравнить значения элементов BufferTypes"):
            assert [item.value for item in BufferTypes] == ["REDIS"]

    @pytest.mark.unit
    @allure.title("BufferTypes ведёт себя как строковое значение [UNIT]")
    def test_buffer_type_compares_with_string(self):
        with allure.step("Сравнить BufferTypes.REDIS со строкой"):
            assert BufferTypes.REDIS == "REDIS"

        with allure.step("Привести BufferTypes к строке"):
            assert str(BufferTypes.REDIS) == "REDIS"

    @pytest.mark.unit
    @allure.title("Bid сохраняет переданные поля и id по умолчанию равен None [UNIT]")
    def test_bid_keeps_fields(self, bid):
        with allure.step("Проверить поля Bid"):
            assert bid.source_name == "agent-1"
            assert bid.source_type is ServerTypes.TEST
            assert bid.seq == 7
            assert bid.time_in == datetime(2026, 1, 1, 12, 0, 0)
            assert isinstance(bid.stats, Metrics)
            assert bid.stats.cpu_load == 12.5
            assert bid.id is None

    @pytest.mark.unit
    @allure.title("Bid принимает явный id заявки [UNIT]")
    def test_bid_accepts_explicit_id(self, bid_factory):
        with allure.step("Создать Bid с id=15"):
            bid = bid_factory(id=15)

        with allure.step("Проверить сохранённый id"):
            assert bid.id == 15

    @pytest.mark.unit
    @allure.title("BidDTO собирается из Bid через from_attributes [UNIT]")
    def test_bid_dto_is_built_from_dataclass(self, bid):
        with allure.step("Преобразовать Bid в BidDTO"):
            dto = BidDTO.model_validate(bid)

        with allure.step("Проверить поля DTO"):
            assert dto.source_name == bid.source_name
            assert dto.source_type is bid.source_type
            assert dto.seq == bid.seq
            assert dto.time_in == bid.time_in
            assert dto.stats.cpu_load == bid.stats.cpu_load
            assert dto.stats.timestamp == bid.stats.timestamp

    @pytest.mark.unit
    @allure.title("BidDTO не содержит id заявки [UNIT]")
    def test_bid_dto_has_no_id_field(self, bid):
        with allure.step("Преобразовать Bid с id в BidDTO"):
            bid.id = 9
            dto = BidDTO.model_validate(bid)

        with allure.step("Проверить отсутствие поля id"):
            assert "id" not in dto.model_dump()

    @pytest.mark.unit
    @allure.title("BidDTO отклоняет неизвестный тип источника [UNIT]")
    def test_bid_dto_rejects_unknown_source_type(self, bid):
        with allure.step("Подготовить payload с неизвестным source_type"):
            payload = BidDTO.model_validate(bid).model_dump(mode="json")
            payload["source_type"] = "unknown"

        with allure.step("Провалидировать payload"):
            with pytest.raises(ValidationError):
                BidDTO.model_validate(payload)

    @pytest.mark.unit
    @allure.title("BidDTO отклоняет payload без метрик [UNIT]")
    def test_bid_dto_rejects_payload_without_stats(self, bid):
        with allure.step("Подготовить payload без stats"):
            payload = BidDTO.model_validate(bid).model_dump(mode="json")
            payload.pop("stats")

        with allure.step("Провалидировать payload"):
            with pytest.raises(ValidationError):
                BidDTO.model_validate(payload)

    @pytest.mark.unit
    @allure.title("BidDTO неизменяем после создания [UNIT]")
    def test_bid_dto_is_frozen(self, bid):
        with allure.step("Преобразовать Bid в BidDTO"):
            dto = BidDTO.model_validate(bid)

        with allure.step("Попытаться изменить поле DTO"):
            with pytest.raises(ValidationError):
                dto.seq = 2

    @pytest.mark.unit
    @allure.title("BidDTO сериализует заявку в JSON-строку [UNIT]")
    def test_bid_dto_serializes_to_json(self, bid):
        with allure.step("Сериализовать BidDTO в JSON"):
            payload = BidDTO.model_validate(bid).model_dump_json()

        with allure.step("Проверить ключевые поля JSON"):
            assert '"source_name":"agent-1"' in payload
            assert '"source_type":"test"' in payload
            assert '"seq":7' in payload

    @pytest.mark.unit
    @allure.title("BidDTO.to_obj восстанавливает Bid с переданным id [UNIT]")
    def test_bid_dto_to_obj_restores_bid(self, bid):
        with allure.step("Преобразовать Bid в DTO и обратно с id=33"):
            dto = BidDTO.model_validate(bid)
            restored = dto.to_obj(33)

        with allure.step("Проверить поля восстановленного Bid"):
            assert isinstance(restored, Bid)
            assert restored.source_name == bid.source_name
            assert restored.source_type is bid.source_type
            assert restored.seq == bid.seq
            assert restored.time_in == bid.time_in
            assert restored.id == 33

        with allure.step("Проверить восстановление вложенных метрик"):
            assert isinstance(restored.stats, Metrics)
            assert restored.stats.cpu_load == bid.stats.cpu_load
            assert restored.stats.load_average == bid.stats.load_average

    @pytest.mark.unit
    @allure.title("BidDTO.to_obj без id оставляет его пустым [UNIT]")
    def test_bid_dto_to_obj_without_id(self, bid):
        with allure.step("Преобразовать Bid в DTO и обратно без id"):
            restored = BidDTO.model_validate(bid).to_obj()

        with allure.step("Проверить отсутствие id"):
            assert restored.id is None

    @pytest.mark.unit
    @allure.title("PutResult сохраняет результат постановки заявки [UNIT]")
    def test_put_result_keeps_fields(self, put_result):
        with allure.step("Проверить поля PutResult"):
            assert put_result.accepted is True
            assert put_result.slot == 1
            assert put_result.bid_id == 42
            assert put_result.seq == 7

    @pytest.mark.unit
    @allure.title("PutResultDTO собирается из PutResult [UNIT]")
    def test_put_result_dto_is_built_from_dataclass(self, put_result):
        with allure.step("Преобразовать PutResult в PutResultDTO"):
            dto = PutResultDTO.model_validate(put_result)

        with allure.step("Сравнить поля DTO и исходной модели"):
            assert dto.accepted is put_result.accepted
            assert dto.slot == put_result.slot
            assert dto.bid_id == put_result.bid_id
            assert dto.seq == put_result.seq

    @pytest.mark.unit
    @allure.title("PutResultDTO сериализуется в JSON-совместимый dict [UNIT]")
    def test_put_result_dto_serializes(self, put_result_factory):
        with allure.step("Создать отказ с slot=-1 и сериализовать его"):
            payload = PutResultDTO.model_validate(
                put_result_factory(accepted=False, slot=-1)
            ).model_dump(mode="json")

        with allure.step("Проверить поля payload"):
            assert payload == {
                "accepted": False,
                "slot": -1,
                "bid_id": 42,
                "seq": 7,
            }
