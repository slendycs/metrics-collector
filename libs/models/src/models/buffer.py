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
    seq:int # Порядковый номер заявки внутри источника
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
    seq:int
    time_in:datetime
    stats:MetricsDTO

    def to_obj(self, bid_id:Optional[int] = None) -> Bid:
        return Bid(
            source_name=self.source_name,
            source_type=self.source_type,
            seq=self.seq,
            time_in=self.time_in,
            stats=self.stats.to_obj(),
            id=bid_id
        )


@dataclass
class PutResult:
    accepted:bool # Статус заявки 
    slot:int # Номер места в буфере
    bid_id:int # id заявки
    seq:int # Порядковый номер заявки от источника


class PutResultDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        frozen=True
    )

    accepted:bool
    slot:int
    bid_id:int
    seq:int
