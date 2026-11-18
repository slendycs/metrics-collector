import uvicorn

from intake.config import settings
from intake.config.logger import logging_config


def main() -> None:
    """Запускает intake под uvicorn с общим форматом логов приложения и сервера."""
    uvicorn.run(
        'intake.main:app',
        host=settings.uvicorn_host,
        port=settings.uvicorn_port,
        log_level=settings.log_level,
        log_config=logging_config,
    )


if __name__ == '__main__':
    main()
