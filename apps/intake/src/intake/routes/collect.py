from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from buffer import Buffer, BufferException, BufferTimeoutError, BufferConnectionError
from intake.config import get_buffer, logger
from models import Bid, PutResult, ServerStatsDTO, PutResultDTO


intake_router = APIRouter()
collect_response_codes = {
    500: {'description': 'Error while process Bid by buffer'},
    502: {'description': 'Failed to connect to buffer'},
    504: {'description': 'Request timeout for buffer access'}
}


@intake_router.post('/collect', status_code=201,
                    responses=collect_response_codes,
                    response_model=PutResultDTO)
async def collect_metrics(stats: ServerStatsDTO,
                          buffer: Buffer = Depends(get_buffer)):
    try:
        stats_obj = stats.to_obj()

        bid = Bid(
            source_name=stats_obj.server_name,
            source_type=stats_obj.server_type,
            time_in=datetime.now(),
            stats=stats_obj.metrics
        )

        return await buffer.put(bid, stats_obj.seq)
    except BufferTimeoutError as err:
        logger.error(err)
        raise HTTPException(status_code=504) from err
    except BufferConnectionError as err:
        logger.critical(err)
        raise HTTPException(status_code=502) from err
    except (BufferException, ValidationError) as err:
        logger.error(err)
        raise HTTPException(status_code=500) from err
