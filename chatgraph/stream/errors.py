class StreamError(Exception):
    pass


class StreamConfigError(StreamError, ValueError):
    pass


class StreamRejectedError(StreamError):
    pass


class StreamClosedError(StreamError):
    pass


class SessionNotOwnedError(StreamError):
    pass


class CommandTimeoutError(StreamError):
    pass


class ConnectionLostError(StreamError):
    pass


class FrameTooLargeError(StreamError):
    pass


class CommandFailedError(StreamError):
    pass


class InvalidDeliveryError(StreamError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_MAX_CHAIN_DEPTH = 10


def is_session_not_owned(exc: BaseException) -> bool:
    """
    Procura um SessionNotOwnedError na cadeia de causas da exceção.

    O UserCall embrulha a exceção original em ValueError/Exception, então
    o erro tipado só é visível por __cause__ e __context__.
    """
    pending: list[tuple[BaseException | None, int]] = [(exc, 0)]
    seen: set[int] = set()
    while pending:
        current, depth = pending.pop()
        if current is None or depth >= _MAX_CHAIN_DEPTH:
            continue
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, SessionNotOwnedError):
            return True
        pending.append((current.__cause__, depth + 1))
        pending.append((current.__context__, depth + 1))
    return False
