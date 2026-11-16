from abc import ABC, abstractmethod

from models import Bid, PutResult


class Buffer(ABC):
    """Интерфейс для работы с буферами"""

    @abstractmethod
    async def put(self, bid: Bid, seq: int) -> PutResult:
        """
        Добавляет заявку в буфер задач

        Args:
            bid (Bid): Заявка
            seq (int): Порядковый номер заявки от конкретного агента

        Returns:
            PutResult: Данные о результате выполнения операции

        Raises:
            pydantic.ValidationError: Заявку не удалось привести к DTO
            BufferTimeoutError: Ответ не получен за заданное время
            BufferConnectionError: Соединение не установлено или потеряно: сервер недоступен, неверный хост/порт, обрыв, ошибка аутентификации
            BufferResponseError: Ошибка при выполнении запроса
        """

    @abstractmethod
    async def ping(self) -> None:
        """
        Проверяет доступность буфера

        Raises:
            BufferTimeoutError: Ответ не получен за заданное время
            BufferConnectionError: Соединение не установлено или потеряно: сервер недоступен, неверный хост/порт, обрыв, ошибка аутентификации
            BufferResponseError: Ошибка при выполнении запроса
        """

    @abstractmethod
    async def aclose(self) -> None:
        """Освобождает ресурсы буфера. По умолчанию ничего не делает."""
