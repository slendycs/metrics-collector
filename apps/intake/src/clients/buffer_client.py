from abc import ABC, abstractmethod

from models import Bid, PutResult

class BufferClient(ABC):
    @abstractmethod
    async def put(self, bid:Bid) -> PutResult: ...
    """Добавляет задние в буффер задач"""

    @abstractmethod
    async def get_free_space(self) -> int: ...
    """Получает количество свободного места в буфере"""
