import os

from ..stream.consumer import StreamConsumer
from ..stream.dual import DualConsumer
from .message_consumer import MessageConsumer

TRANSPORT_QUEUE = 'queue'
TRANSPORT_STREAM = 'stream'
TRANSPORT_DUAL = 'dual'


def read_transport(env: str = 'ROUTER_TRANSPORT') -> str:
    value = os.getenv(env, '').strip().lower()
    if not value:
        return TRANSPORT_QUEUE
    if value not in {TRANSPORT_QUEUE, TRANSPORT_STREAM, TRANSPORT_DUAL}:
        raise ValueError(
            f'ROUTER_TRANSPORT inválido {value!r}: use queue, stream ou dual'
        )
    return value


def consumer_from_env() -> MessageConsumer | StreamConsumer | DualConsumer:
    transport = read_transport()
    if transport == TRANSPORT_STREAM:
        return StreamConsumer.load_dotenv()
    if transport == TRANSPORT_DUAL:
        return DualConsumer.load_dotenv()
    return MessageConsumer.load_dotenv()
