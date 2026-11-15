from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

from models.enums import ServerTypes, LogLevel


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    server_name: str
    server_type: ServerTypes
    timeout_min: int
    timeout_max: int
    reception_service_url: str
    log_level: LogLevel = LogLevel.INFO

    @model_validator(mode='after')
    def check_timeouts(self):
        if self.timeout_min >= self.timeout_max:
            raise ValueError('The minimum timeout duration cannot be greater than or equal to the maximum')
        
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings() # type: ignore