import logging

from config.config import get_settings


log_format = '[%(asctime)s][%(levelname)s]: %(message)s'

logging.basicConfig(level=get_settings().log_level, format=log_format)
logger = logging.getLogger('agent')
