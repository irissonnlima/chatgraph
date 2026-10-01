import os

from ..stream.consumer import StreamConsumer
from .message_consumer import MessageConsumer

TRANSPORT_QUEUE = 'queue'
TRANSPORT_STREAM = 'stream'


def read_transport(env: str = 'ROUTER_TRANSPORT') -> str:
    value = os.getenv(env, '').strip().lower()
    if not value:
        return TRANSPORT_QUEUE
    if value not in {TRANSPORT_QUEUE, TRANSPORT_STREAM}:
        raise ValueError(
            f'ROUTER_TRANSPORT inválido {value!r}: use queue ou stream'
        )
    return value


def consumer_from_env() -> MessageConsumer | StreamConsumer:
    if read_transport() == TRANSPORT_STREAM:
        return StreamConsumer.load_dotenv()
    return MessageConsumer.load_dotenv()
