from contextlib import asynccontextmanager

from fastapi import FastAPI

from intake.config import create_buffer, logger
from intake.routes import intake_router, service_router
from buffer.buffer_errors import BufferException


@asynccontextmanager
async def lifespan(app: FastAPI):
    buffer = create_buffer()
    try:
        await buffer.ping()
        app.state.buffer = buffer
        yield
    except BufferException as err:
        logger.critical(f'Failed to connect to Buffer: {err}')
        raise
    finally:
        await buffer.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(intake_router)
app.include_router(service_router)
