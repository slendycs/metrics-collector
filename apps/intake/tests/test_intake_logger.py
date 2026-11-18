import logging

import allure
import pytest

from intake.config import logger as intake_logger
from intake.config.config import settings
from intake.config.logger import log_format, logging_config


class TestIntakeLogger:
    @pytest.mark.unit
    @allure.title("Конфигурация логов задаёт общий формат для форматтера default [UNIT]")
    def test_configures_shared_formatter(self):
        with allure.step("Прочитать формат форматтера default"):
            formatter = logging_config["formatters"]["default"]

        with allure.step("Проверить, что формат совпадает с log_format"):
            assert formatter["format"] == log_format

    @pytest.mark.unit
    @allure.title("Обработчик по умолчанию пишет в stdout [UNIT]")
    def test_default_handler_writes_to_stdout(self):
        with allure.step("Прочитать описание обработчика default"):
            handler = logging_config["handlers"]["default"]

        with allure.step("Проверить класс, форматтер и поток"):
            assert handler["class"] == "logging.StreamHandler"
            assert handler["formatter"] == "default"
            assert handler["stream"] == "ext://sys.stdout"

    @pytest.mark.unit
    @allure.title("Root-логгер использует обработчик default и уровень настроек [UNIT]")
    def test_root_logger_uses_default_handler(self):
        with allure.step("Прочитать настройки root-логгера"):
            root = logging_config["root"]

        with allure.step("Проверить обработчик и уровень из настроек"):
            assert root["handlers"] == ["default"]
            assert root["level"] == settings.log_level

    @pytest.mark.unit
    @allure.title("Логгер uvicorn {name} пишет напрямую в default [UNIT]")
    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("uvicorn", id="root"),
            pytest.param("uvicorn.error", id="error"),
            pytest.param("uvicorn.access", id="access"),
        ],
    )
    def test_uvicorn_logger_uses_default_handler(self, name):
        with allure.step(f"Прочитать настройки логгера {name}"):
            logger_config = logging_config["loggers"][name]

        with allure.step("Проверить обработчик, уровень и отключение propagate"):
            assert logger_config["handlers"] == ["default"]
            assert logger_config["level"] == settings.log_level
            assert logger_config["propagate"] is False

    @pytest.mark.unit
    @allure.title("Формат логов выводит время и уровень записи [UNIT]")
    def test_log_format_renders_time_and_level(self):
        with allure.step("Создать запись уровня INFO"):
            record = logging.LogRecord(
                name="intake",
                level=logging.INFO,
                pathname=__file__,
                lineno=1,
                msg="message",
                args=(),
                exc_info=None,
            )

        with allure.step("Отформатировать запись через log_format"):
            rendered = logging.Formatter(log_format).format(record)

        with allure.step("Проверить начало строки и уровень INFO"):
            assert rendered.startswith("[")
            assert "[INFO]" in rendered
            assert rendered.endswith(": message")

    @pytest.mark.unit
    @allure.title("После импорта логгер intake включён с нашим обработчиком [UNIT]")
    def test_intake_logger_is_configured(self):
        with allure.step("Проверить имя и эффективный уровень логгера intake"):
            assert intake_logger.name == "intake"
            assert intake_logger.getEffectiveLevel() == logging.INFO
            assert intake_logger.isEnabledFor(logging.INFO)
            assert not intake_logger.isEnabledFor(logging.DEBUG)

        with allure.step("Найти у root-логгера StreamHandler с нашим форматом"):
            handlers = [
                handler
                for handler in logging.getLogger().handlers
                if isinstance(handler, logging.StreamHandler)
                and getattr(handler.formatter, "_fmt", None) == log_format
            ]

        with allure.step("Проверить, что обработчик применён"):
            assert handlers
