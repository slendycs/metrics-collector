from enum import StrEnum


class ServerTypes(StrEnum):
    PRODUCTION = 'production'
    STAGING = 'staging'
    TEST = 'test'


class LogLevel(StrEnum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'
