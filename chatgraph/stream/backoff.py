import enum
from typing import Callable

from websockets.exceptions import ConnectionClosed, InvalidStatus

_MAX_BODY_BYTES = 1024
_MAX_SHIFT_ATTEMPT = 30
_CONFIG_STATUSES = (401, 403, 404)
_STATUS_UNAVAILABLE = 503
_CODE_POLICY_VIOLATION = 1008
_CODE_TRY_AGAIN_LATER = 1013


class FailureClass(enum.Enum):
    CONFIG = 'config'
    SHORT = 'short'
    NETWORK = 'network'


def full_jitter(
    attempt: int, base: float, cap: float, rand: Callable[[float], float]
) -> float:
    if attempt >= _MAX_SHIFT_ATTEMPT:
        ceiling = cap
    else:
        ceiling = min(cap, base * 2**attempt)
    return rand(ceiling)


def classify(exc: BaseException) -> FailureClass:
    if isinstance(exc, InvalidStatus):
        status = exc.response.status_code
        if status in _CONFIG_STATUSES:
            return FailureClass.CONFIG
        if status == _STATUS_UNAVAILABLE:
            return FailureClass.SHORT
    elif isinstance(exc, ConnectionClosed) and exc.rcvd is not None:
        if exc.rcvd.code == _CODE_POLICY_VIOLATION:
            return FailureClass.CONFIG
        if exc.rcvd.code == _CODE_TRY_AGAIN_LATER:
            return FailureClass.SHORT
    return FailureClass.NETWORK


def failure_detail(exc: BaseException) -> str:
    if isinstance(exc, InvalidStatus):
        body = exc.response.body[:_MAX_BODY_BYTES]
        reason = body.decode('utf-8', errors='replace')
        return f'status={exc.response.status_code} reason={reason}'
    if isinstance(exc, ConnectionClosed) and exc.rcvd is not None:
        return f'code={exc.rcvd.code} reason={exc.rcvd.reason}'
    return f'err={str(exc) or type(exc).__name__}'
