from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError

from buffer import Buffer
from intake.config import get_buffer
from models import Bid, PutResult, ServerStatsDTO


intake_router = APIRouter()


@intake_router.post('/collect', status_code=201)
async def collect_metrics(stats: ServerStatsDTO,
                          buffer: Buffer = Depends(get_buffer)) -> PutResult:
    stats_obj = stats.to_obj()

    bid = Bid(
        source_name=stats_obj.server_name,
        source_type=stats_obj.server_type,
        seq=stats_obj.seq,
        time_in=datetime.now(),
        stats=stats_obj.metrics
    )


