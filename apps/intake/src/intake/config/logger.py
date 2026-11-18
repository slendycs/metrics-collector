import logging
import logging.config

from .config import settings


log_format = '[%(asctime)s][%(levelname)s]: %(message)s'

# Единая конфигурация для логов приложения и uvicorn: одинаковый формат,
# один обработчик на stdout. uvicorn использует её при запуске из `intake.__main__`.
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': log_format},
        # uvicorn дописывает use_colors в оба форматтера, если цвета включены
        'access': {'format': log_format},
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'handlers': ['default'],
        'level': settings.log_level,
    },
    'loggers': {
        'uvicorn': {
            'handlers': ['default'],
            'level': settings.log_level,
            'propagate': False,
        },
        'uvicorn.error': {
            'handlers': ['default'],
            'level': settings.log_level,
            'propagate': False,
        },
        'uvicorn.access': {
            'handlers': ['default'],
            'level': settings.log_level,
            'propagate': False,
        },
    },
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger('intake')
