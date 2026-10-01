import random
from dataclasses import dataclass, field
from typing import Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

from ..services.router_http_client import router_v1_base
from .errors import StreamConfigError
from .frames import CONNECT_PATH

_DEFAULT_USERNAME = 'chatgraph'
_DEFAULT_QUEUE_SIZE = 100
_DEFAULT_DRAIN_TIMEOUT = 15.0
_WS_SCHEMES = {'http': 'ws', 'https': 'wss'}


@dataclass(frozen=True)
class StreamOptions:
    router_url: str
    token: str
    menus: tuple[str, ...]
    username: str = _DEFAULT_USERNAME
    queue_size: int = _DEFAULT_QUEUE_SIZE
    drain_timeout: float = _DEFAULT_DRAIN_TIMEOUT


@dataclass
class _Settings:
    dial_timeout: float = 5.0
    welcome_timeout: float = 5.0
    command_timeout: float = 10.0
    auth_retry_delay: float = 30.0
    close_timeout: float = 2.0
    backoff_base: float = 0.5
    backoff_cap: float = 30.0
    short_backoff_cap: float = 5.0
    default_heartbeat_s: float = 5.0
    heartbeat_unit: float = 1.0
    dead_factor: int = 3
    dedupe_capacity: int = 2048
    max_read_bytes: int = 4 * 1024 * 1024
    max_frame_bytes: int = 1024 * 1024
    rand: Callable[[float], float] = field(
        default=lambda ceiling: random.uniform(0, ceiling)
    )


def connect_url(router_url: str) -> str:
    parts = urlsplit(router_url.strip())
    scheme = _WS_SCHEMES.get(parts.scheme)
    if scheme is None or not parts.netloc:
        raise StreamConfigError(
            f'ROUTER_URL inválida {router_url!r}: use http(s)://host'
        )
    base = router_v1_base(
        urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
    )
    return scheme + base[len(parts.scheme) :] + CONNECT_PATH


def normalize_menus(menus: Iterable[str]) -> tuple[str, ...]:
    normalized: dict[str, None] = {}
    for menu in menus:
        name = menu.strip()
        if name:
            normalized.setdefault(name)
    return tuple(normalized)


def normalize_options(opts: StreamOptions) -> StreamOptions:
    if not opts.token.strip():
        raise StreamConfigError('ROUTER_TOKEN vazio')
    menus = normalize_menus(opts.menus)
    if not menus:
        raise StreamConfigError('nenhum menu declarado (ROUTER_MENUS)')
    connect_url(opts.router_url)
    return StreamOptions(
        router_url=opts.router_url,
        token=opts.token,
        menus=menus,
        username=opts.username.strip() or _DEFAULT_USERNAME,
        queue_size=opts.queue_size
        if opts.queue_size > 0
        else _DEFAULT_QUEUE_SIZE,
        drain_timeout=opts.drain_timeout
        if opts.drain_timeout > 0
        else _DEFAULT_DRAIN_TIMEOUT,
    )
