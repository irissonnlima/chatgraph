# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import threading

import pytest

from chatgraph.bot.chatbot_model import ChatbotApp
from chatgraph.messages.message_consumer import MessageConsumer
from chatgraph.messages.transport import (
    TRANSPORT_QUEUE,
    TRANSPORT_STREAM,
    consumer_from_env,
    read_transport,
)
from chatgraph.stream.consumer import StreamConsumer
from chatgraph.stream.runtime import THREAD_NAME

ENV_NAMES = (
    'ROUTER_TRANSPORT',
    'ROUTER_URL',
    'ROUTER_TOKEN',
    'ROUTER_MENUS',
    'RABBIT_USER',
    'RABBIT_PASS',
    'RABBIT_URI',
    'RABBIT_QUEUE',
    'LOG_RABBIT_QUEUE',
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def stream_env(monkeypatch):
    monkeypatch.setenv('ROUTER_TRANSPORT', 'stream')
    monkeypatch.setenv('ROUTER_URL', 'http://r:8085')
    monkeypatch.setenv('ROUTER_TOKEN', 'tok')
    monkeypatch.setenv('ROUTER_MENUS', 'rh')


@pytest.fixture
def queue_env(monkeypatch):
    monkeypatch.setenv('RABBIT_USER', 'user')
    monkeypatch.setenv('RABBIT_PASS', 'pass')
    monkeypatch.setenv('RABBIT_URI', 'rabbit:5672')
    monkeypatch.setenv('RABBIT_QUEUE', 'rh')
    monkeypatch.setenv('ROUTER_URL', 'http://r:8085')
    monkeypatch.setenv('ROUTER_TOKEN', 'tok')


@pytest.mark.unit
class TestReadTransport:
    def test_default_is_queue(self):
        assert read_transport() == TRANSPORT_QUEUE

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ('stream', TRANSPORT_STREAM),
            (' STREAM ', TRANSPORT_STREAM),
            ('Queue', TRANSPORT_QUEUE),
            ('   ', TRANSPORT_QUEUE),
        ],
    )
    def test_value_is_trimmed_and_lowercased(
        self, monkeypatch, value, expected
    ):
        monkeypatch.setenv('ROUTER_TRANSPORT', value)

        assert read_transport() == expected

    def test_unknown_value_raises(self, monkeypatch):
        monkeypatch.setenv('ROUTER_TRANSPORT', 'ws')

        with pytest.raises(ValueError, match="ROUTER_TRANSPORT inválido 'ws'"):
            read_transport()


@pytest.mark.unit
class TestConsumerFromEnv:
    def test_default_builds_message_consumer(self, queue_env):
        assert isinstance(consumer_from_env(), MessageConsumer)

    def test_stream_builds_stream_consumer_without_network(self, stream_env):
        consumer = consumer_from_env()

        assert isinstance(consumer, StreamConsumer)
        assert not [t for t in threading.enumerate() if t.name == THREAD_NAME]

    def test_stream_value_is_normalized(self, stream_env, monkeypatch):
        monkeypatch.setenv('ROUTER_TRANSPORT', ' STREAM ')

        assert isinstance(consumer_from_env(), StreamConsumer)

    def test_invalid_transport_raises(self, stream_env, monkeypatch):
        monkeypatch.setenv('ROUTER_TRANSPORT', 'ws')

        with pytest.raises(ValueError, match='ROUTER_TRANSPORT inválido'):
            consumer_from_env()


@pytest.mark.unit
class TestChatbotAppTransport:
    def test_stream_env_builds_app_without_rabbit_variables(self, stream_env):
        app = ChatbotApp()

        assert isinstance(app._ChatbotApp__message_consumer, StreamConsumer)

    def test_queue_default_without_rabbit_env_keeps_todays_error(self):
        with pytest.raises(ValueError, match='Corrija as variáveis'):
            ChatbotApp()

    def test_explicit_consumer_is_untouched(self, stream_env):
        explicit = StreamConsumer('http://other:8085', 'tok2', ['geral'])

        app = ChatbotApp(message_consumer=explicit)

        assert app._ChatbotApp__message_consumer is explicit
