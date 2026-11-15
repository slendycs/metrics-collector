from abc import ABC, abstractmethod

from models import Bid, PutResult


class Buffer(ABC):
    """Интерфейс для работы с буферами"""

    @abstractmethod
    async def put(self, bid: Bid, seq: int) -> PutResult:
        """Добавляет заявку в буфер задач"""

    @abstractmethod
    async def get_free_space(self) -> int:
        """Получает количество свободного места в буфере"""

    async def ping(self) -> None:
        """Проверяет доступность буфера. По умолчанию ничего не делает."""

    async def aclose(self) -> None:
        """Освобождает ресурсы буфера. По умолчанию ничего не делает."""
