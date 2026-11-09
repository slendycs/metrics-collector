from unittest.mock import patch

import allure
import pytest

import agent


class TestEntrypoint:
    @pytest.mark.unit
    @allure.title("main создаёт PoolingManager и запускает pooling [UNIT]")
    def test_main_starts_pooling_manager(self):
        with allure.step("Подменить PoolingManager и вызвать main"):
            with patch("agent.PoolingManager") as manager_cls:
                agent.main()

        with allure.step("Проверить создание менеджера и запуск опроса"):
            manager_cls.assert_called_once_with()
            manager_cls.return_value.pooling.assert_called_once_with()
