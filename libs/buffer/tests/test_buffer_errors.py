import builtins

import allure
import pytest

import buffer
from buffer import (
    BufferConnectionError,
    BufferException,
    BufferResponseError,
    BufferTimeoutError,
)


class TestBufferErrors:
    @pytest.mark.unit
    @allure.title("Базовое доменное исключение не перекрывает builtin BufferError [UNIT]")
    def test_base_error_does_not_shadow_builtin(self):
        with allure.step("Сравнить доменное исключение со встроенным BufferError"):
            same_object = BufferException is builtins.BufferError
            is_subclass = issubclass(BufferException, builtins.BufferError)

        with allure.step("Проверить, что это разные классы"):
            assert same_object is False
            assert is_subclass is False

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "error_class",
        [
            pytest.param(BufferTimeoutError, id="timeout"),
            pytest.param(BufferConnectionError, id="connection"),
            pytest.param(BufferResponseError, id="response"),
        ],
    )
    @allure.title("{error_class.__name__} наследуется от BufferException [UNIT]")
    def test_specific_error_inherits_base(self, error_class):
        with allure.step(f"Проверить иерархию {error_class.__name__}"):
            assert issubclass(error_class, BufferException)
            assert not issubclass(error_class, builtins.BufferError)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("error_class", "prefix"),
        [
            pytest.param(
                BufferTimeoutError,
                "Time limit exceeded when accessing the buffer",
                id="timeout",
            ),
            pytest.param(
                BufferConnectionError,
                "Problem when connecting to the buffer",
                id="connection",
            ),
            pytest.param(
                BufferResponseError,
                "An error occurred while executing the request",
                id="response",
            ),
        ],
    )
    @allure.title("{error_class.__name__} дополняет сообщение пояснением [UNIT]")
    def test_str_adds_context(self, error_class, prefix):
        with allure.step("Создать исключение с исходным сообщением"):
            error = error_class("redis is down")

        with allure.step("Проверить текст исключения"):
            assert str(error) == f"{prefix}: redis is down"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "error_class",
        [
            pytest.param(BufferException, id="base"),
            pytest.param(BufferTimeoutError, id="timeout"),
            pytest.param(BufferConnectionError, id="connection"),
            pytest.param(BufferResponseError, id="response"),
        ],
    )
    @allure.title("{error_class.__name__} сохраняет исходное сообщение и args [UNIT]")
    def test_keeps_original_message(self, error_class):
        with allure.step("Создать исключение с сообщением"):
            error = error_class("original message")

        with allure.step("Проверить атрибут и аргументы исключения"):
            assert error.error_msg == "original message"
            assert error.args == ("original message",)

    @pytest.mark.unit
    @allure.title("Пакет buffer экспортирует все доменные исключения [UNIT]")
    def test_errors_are_exported_from_package(self):
        with allure.step("Проверить публичный список экспортов"):
            exported = set(buffer.__all__)

        with allure.step("Убедиться, что все исключения доступны из пакета"):
            for name in (
                "BufferException",
                "BufferTimeoutError",
                "BufferConnectionError",
                "BufferResponseError",
            ):
                assert name in exported
                assert getattr(buffer, name).__name__ == name
