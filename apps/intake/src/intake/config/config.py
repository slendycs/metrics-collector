from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional

from models import LogLevel, BufferTypes


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    buffer_type: BufferTypes = BufferTypes.REDIS
    buffer_capacity:int
    redis_url:Optional[str]
    log_level:LogLevel = LogLevel.INFO

    @model_validator(mode='after')
    def check_redis_link(self):
        if self.buffer_type == BufferTypes.REDIS and \
            self.redis_url is None:
                raise ValueError('The buffer type is set to Redis, but no connection url is specified')

        return self



settings = Settings() # type: ignore