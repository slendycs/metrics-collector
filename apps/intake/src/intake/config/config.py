from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from models import BufferTypes, LogLevel


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    buffer_type: BufferTypes = BufferTypes.REDIS
    buffer_capacity: int = Field(gt=0)
    redis_url: str | None = None
    stats_server_url:str
    log_level: LogLevel = LogLevel.INFO

    @model_validator(mode='after')
    def check_redis_link(self):
        if self.buffer_type == BufferTypes.REDIS and \
            self.redis_url is None:
                raise ValueError('The buffer type is set to Redis, but no connection url is specified')

        return self


settings = Settings()  # type: ignore
