from unittest.mock import AsyncMock, MagicMock

import pytest

from chatgraph.messages.log_publisher import LogPublisher
from chatgraph.models.log_envelope import EventType, LogEnvelope


@pytest.fixture
def log_envelope():
    return LogEnvelope(
        event_id='abc-123',
        event_type=EventType.ERROR,
        timestamp='2025-01-01T00:00:00+00:00',
        session_id=100,
        chat_user_id='user1',
        chat_company_id='company1',
        platform='whatsapp',
        origin='chatgraph:suporte',
        error='something broke',
        payload={'error_code': 'CHATBOT_ERROR', 'error_message': 'boom'},
    )


@pytest.mark.unit
class TestLogPublisherInitRoutingKey:
    def test_init_routing_key_default(self):
        publisher = LogPublisher(
            amqp_url='amqp://localhost',
            queue_name='my_queue',
        )
        assert publisher._routing_key == 'chatbot.my_queue'

    def test_init_routing_key_custom(self):
        publisher = LogPublisher(
            amqp_url='amqp://localhost',
            routing_key='custom.key',
        )
        assert publisher._routing_key == 'custom.key'


@pytest.mark.unit
class TestLogPublisherLoadDotenv:
    def test_load_dotenv_returns_none_when_queue_not_set(self, monkeypatch):
        monkeypatch.delenv('LOG_RABBIT_QUEUE', raising=False)
        result = LogPublisher.load_dotenv()
        assert result is None

    def test_load_dotenv_returns_publisher_when_configured(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'localhost:5672')
        monkeypatch.setenv('LOG_RABBIT_QUEUE', 'log_queue')
        monkeypatch.setenv('RABBIT_HEARTBEAT', '30')
        monkeypatch.setenv('RABBIT_RECONNECT_INTERVAL', '10.0')

        result = LogPublisher.load_dotenv()
        assert result is not None
        assert result._queue_name == 'log_queue'
        assert result._heartbeat == 30
        assert result._reconnect_interval == 10.0

    def test_load_dotenv_routing_key_default(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'localhost:5672')
        monkeypatch.setenv('LOG_RABBIT_QUEUE', 'logs')
        monkeypatch.delenv('LOG_RABBIT_ROUTING_KEY', raising=False)

        result = LogPublisher.load_dotenv()
        assert result._routing_key == 'chatbot.logs'

    def test_load_dotenv_routing_key_custom(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'localhost:5672')
        monkeypatch.setenv('LOG_RABBIT_QUEUE', 'logs')
        monkeypatch.setenv('LOG_RABBIT_ROUTING_KEY', 'custom.routing.key')

        result = LogPublisher.load_dotenv()
        assert result._routing_key == 'custom.routing.key'

    def test_load_dotenv_uses_rabbit_vhost(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'localhost:5672')
        monkeypatch.setenv('LOG_RABBIT_QUEUE', 'logs')
        monkeypatch.setenv('RABBIT_VHOST', 'custom-vhost')

        result = LogPublisher.load_dotenv()
        assert 'custom-vhost' in result._amqp_url


@pytest.mark.unit
class TestLogPublisherPublishError:
    @pytest.mark.asyncio
    async def test_publish_error_fire_and_forget(self, log_envelope):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        mock_connection = MagicMock()
        mock_connection.is_closed = False
        mock_channel = AsyncMock()
        mock_exchange = MagicMock()
        mock_exchange.publish = MagicMock(
            side_effect=RuntimeError('connection lost')
        )
        mock_channel.get_exchange = AsyncMock(return_value=mock_exchange)
        mock_channel.declare_queue = AsyncMock()

        publisher._connection = mock_connection
        publisher._channel = mock_channel

        await publisher.publish_error(log_envelope)

    @pytest.mark.asyncio
    async def test_publish_error_sends_correct_headers(self, log_envelope):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        mock_connection = MagicMock()
        mock_connection.is_closed = False
        mock_channel = AsyncMock()
        mock_exchange = MagicMock()
        mock_exchange.publish = MagicMock()
        mock_channel.get_exchange = AsyncMock(return_value=mock_exchange)
        mock_channel.declare_queue = AsyncMock()

        publisher._connection = mock_connection
        publisher._channel = mock_channel

        await publisher.publish_error(log_envelope)

        call_args = mock_exchange.publish.call_args
        message_arg = call_args[0][0]
        assert message_arg.content_type == 'text/plain'
        assert message_arg.headers == {
            'type_message': 'log_error',
            'error': 'something broke',
        }


@pytest.mark.unit
class TestLogPublisherClose:
    @pytest.mark.asyncio
    async def test_close_cleans_up(self):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        mock_connection = AsyncMock()
        mock_connection.is_closed = False
        publisher._connection = mock_connection
        publisher._channel = MagicMock()

        await publisher.close()

        mock_connection.close.assert_awaited_once()
        assert publisher._connection is None
        assert publisher._channel is None

    @pytest.mark.asyncio
    async def test_close_when_already_closed_does_not_raise(self):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        mock_connection = MagicMock()
        mock_connection.is_closed = True
        publisher._connection = mock_connection

        await publisher.close()


@pytest.mark.unit
class TestLogPublisherContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_closes_connection(self):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        mock_connection = AsyncMock()
        mock_connection.is_closed = False
        publisher._connection = mock_connection
        publisher._channel = MagicMock()

        async with publisher:
            pass

        mock_connection.close.assert_awaited_once()
