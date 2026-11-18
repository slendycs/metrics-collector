from datetime import datetime
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict
from typing import Optional

from .enums import ServerTypes
from .metrics import Metrics, MetricsDTO


@dataclass
class Bid:
    source_name:str # Имя сервера
    source_type:ServerTypes # Тип сервера
    time_in:datetime # Время поступления заявки
    stats:Metrics # Пакет метрик
    id:Optional[int] = None # id заявки (назначается Redis)


class BidDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        frozen=True
    )

    source_name:str
    source_type:ServerTypes
    time_in:datetime
    stats:MetricsDTO

    def to_obj(self, bid_id:Optional[int] = None) -> Bid:
        return Bid(
            source_name=self.source_name,
            source_type=self.source_type,
            time_in=self.time_in,
            stats=self.stats.to_obj(),
            id=bid_id
        )


@dataclass
class PutResult:
    accepted:bool # Статус заявки 
    bid_id:int # id заявки
    seq:int # Порядковый номер заявки от источника
    source_name:str # Имя источника
    source_type:ServerTypes # Тип источника
    slot:Optional[int] = None # Номер места в буфере


class PutResultDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        frozen=True
    )

    accepted:bool
    bid_id:int
    seq:int
    source_name:str
    source_type:ServerTypes
    slot:Optional[int] = None
