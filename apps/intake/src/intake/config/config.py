from pydantic_settings import BaseSettings, SettingsConfigDict

from models.enums import LogLevel


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    redis_url:str
    log_level:LogLevel = LogLevel.INFO


settings = Settings() # type: ignore