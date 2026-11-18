from types import SimpleNamespace
from unittest.mock import patch

import allure
import pytest

from intake.__main__ import main
from intake.config.config import settings
from intake.config.logger import logging_config


class TestIntakeMain:
    @pytest.mark.unit
    @allure.title("main запускает uvicorn с настройками по умолчанию [UNIT]")
    def test_runs_uvicorn_with_default_settings(self):
        with allure.step("Подменить uvicorn.run"):
            with patch("intake.__main__.uvicorn.run") as run:
                with allure.step("Вызвать main"):
                    main()

        with allure.step("Проверить единственный вызов с приложением и настройками"):
            run.assert_called_once_with(
                "intake.main:app",
                host=settings.uvicorn_host,
                port=settings.uvicorn_port,
                log_level=settings.log_level,
                log_config=logging_config,
            )

    @pytest.mark.unit
    @allure.title("main передаёт в uvicorn хост, порт и уровень из настроек [UNIT]")
    def test_passes_settings_values_to_uvicorn(self):
        with allure.step("Подготовить подменённые настройки uvicorn"):
            fake_settings = SimpleNamespace(
                uvicorn_host="127.0.0.9",
                uvicorn_port=9123,
                log_level="DEBUG",
            )

        with allure.step("Вызвать main с подменёнными настройками"):
            with (
                patch("intake.__main__.settings", fake_settings),
                patch("intake.__main__.uvicorn.run") as run,
            ):
                main()

        with allure.step("Проверить аргументы вызова uvicorn.run"):
            run.assert_called_once_with(
                "intake.main:app",
                host="127.0.0.9",
                port=9123,
                log_level="DEBUG",
                log_config=logging_config,
            )

        with allure.step("Проверить, что передан тот же объект конфигурации логов"):
            assert run.call_args.kwargs["log_config"] is logging_config
