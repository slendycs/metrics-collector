import logging

from .config import settings


log_format = '[%(asctime)s][%(levelname)s]: %(message)s'

logging.basicConfig(level=settings.log_level, format=log_format)
logger = logging.getLogger('intake')
