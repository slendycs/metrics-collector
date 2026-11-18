from fastapi import APIRouter, Depends, HTTPException

from intake.config import get_buffer

from buffer import Buffer, BufferException

service_router = APIRouter(tags=['Service endpoints'])


@service_router.get('/health', status_code=200)
async def health(buffer: Buffer = Depends(get_buffer)) -> int:
    try:
        await buffer.ping()
        return 200
    except BufferException as err:
        raise HTTPException(503, 'Failed connect to buffer') from err
