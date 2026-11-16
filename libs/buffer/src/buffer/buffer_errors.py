class BufferException(Exception):
    def __init__(self, error_msg: str):
        super().__init__(error_msg)
        self.error_msg = error_msg


class BufferTimeoutError(BufferException):
    def __str__(self) -> str:
        return f'Time limit exceeded when accessing the buffer: {self.error_msg}'


class BufferConnectionError(BufferException):
    def __str__(self) -> str:
        return f'Problem when connecting to the buffer: {self.error_msg}'


class BufferResponseError(BufferException):
    def __str__(self) -> str:
        return f'An error occurred while executing the request: {self.error_msg}'
