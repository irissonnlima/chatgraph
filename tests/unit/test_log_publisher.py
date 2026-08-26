from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_init_routing_key_default_is_queue_name(self):
        # Sem exchange nomeada o roteamento é pelo nome da fila.
        publisher = LogPublisher(
            amqp_url='amqp://localhost',
            queue_name='my_queue',
        )
        assert publisher._exchange == ''
        assert publisher._routing_key == 'my_queue'

    def test_init_routing_key_default_with_exchange(self):
        publisher = LogPublisher(
            amqp_url='amqp://localhost',
            exchange='chatbot',
            queue_name='my_queue',
        )
        assert publisher._routing_key == 'chatbot.my_queue'

    def test_init_exchange_slash_falls_back_to_default(self):
        publisher = LogPublisher(
            amqp_url='amqp://localhost',
            exchange='/',
            queue_name='my_queue',
        )
        assert publisher._exchange == ''

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
        monkeypatch.setenv('RABBIT_VHOST', 'chatbot')
        monkeypatch.delenv('LOG_RABBIT_ROUTING_KEY', raising=False)
        monkeypatch.delenv('LOG_RABBIT_EXCHANGE', raising=False)

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
class TestLogPublisherExchangeResolution:
    def _base_env(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'localhost:5672')
        monkeypatch.setenv('LOG_RABBIT_QUEUE', 'logs')
        monkeypatch.delenv('LOG_RABBIT_ROUTING_KEY', raising=False)

    def test_exchange_defaults_to_vhost(self, monkeypatch):
        self._base_env(monkeypatch)
        monkeypatch.delenv('LOG_RABBIT_EXCHANGE', raising=False)
        monkeypatch.setenv('RABBIT_VHOST', 'chatbot')

        result = LogPublisher.load_dotenv()
        assert result._exchange == 'chatbot'

    def test_explicit_exchange_wins_over_vhost(self, monkeypatch):
        self._base_env(monkeypatch)
        monkeypatch.setenv('LOG_RABBIT_EXCHANGE', 'chatbot-hml')
        monkeypatch.setenv('RABBIT_VHOST', 'chatbot')

        result = LogPublisher.load_dotenv()
        assert result._exchange == 'chatbot-hml'

    def test_root_vhost_falls_back_to_default_exchange(self, monkeypatch):
        # Vhost '/' não tem exchange homônima: cai na exchange default e o
        # roteamento passa a ser pelo nome da fila.
        self._base_env(monkeypatch)
        monkeypatch.delenv('LOG_RABBIT_EXCHANGE', raising=False)
        monkeypatch.setenv('RABBIT_VHOST', '/')

        result = LogPublisher.load_dotenv()
        assert result._exchange == ''
        assert result._routing_key == 'logs'

    def test_root_vhost_is_url_encoded(self, monkeypatch):
        self._base_env(monkeypatch)
        monkeypatch.setenv('RABBIT_VHOST', '/')

        result = LogPublisher.load_dotenv()
        assert result._amqp_url.endswith('/%2F')


@pytest.mark.unit
class TestLogPublisherPublishError:
    @pytest.mark.asyncio
    async def test_publish_error_fire_and_forget(self, log_envelope):
        publisher = LogPublisher(
            amqp_url='amqp://localhost', exchange='chatbot'
        )

        mock_channel = AsyncMock()
        mock_channel.is_closed = False
        mock_exchange = MagicMock()
        mock_exchange.publish = AsyncMock(
            side_effect=RuntimeError('connection lost')
        )
        mock_channel.get_exchange = AsyncMock(return_value=mock_exchange)
        mock_channel.declare_queue = AsyncMock()

        mock_connection = MagicMock()
        mock_connection.is_closed = False
        mock_connection.channel = AsyncMock(return_value=mock_channel)

        publisher._connection = mock_connection
        publisher._channel = mock_channel

        await publisher.publish_error(log_envelope)

    @pytest.mark.asyncio
    async def test_publish_error_sends_correct_headers(self, log_envelope):
        publisher = LogPublisher(
            amqp_url='amqp://localhost', exchange='chatbot'
        )

        mock_connection = MagicMock()
        mock_connection.is_closed = False
        mock_channel = AsyncMock()
        mock_channel.is_closed = False
        mock_exchange = MagicMock()
        mock_exchange.publish = AsyncMock()
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


def _live_channel() -> MagicMock:
    channel = MagicMock()
    channel.is_closed = False
    channel.close = AsyncMock()
    channel.declare_queue = AsyncMock()
    return channel


@pytest.mark.unit
class TestLogPublisherChannelRecovery:
    @pytest.mark.asyncio
    async def test_ensure_connection_recreates_closed_channel(self):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        closed_channel = MagicMock()
        closed_channel.is_closed = True
        new_channel = _live_channel()
        connection = MagicMock()
        connection.is_closed = False
        connection.channel = AsyncMock(return_value=new_channel)

        publisher._connection = connection
        publisher._channel = closed_channel

        await publisher._ensure_connection()

        assert publisher._channel is new_channel
        connection.channel.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_connection_keeps_live_channel(self):
        publisher = LogPublisher(amqp_url='amqp://localhost')

        channel = _live_channel()
        connection = MagicMock()
        connection.is_closed = False
        connection.channel = AsyncMock()

        publisher._connection = connection
        publisher._channel = channel

        await publisher._ensure_connection()

        assert publisher._channel is channel
        connection.channel.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_publish_error_retries_with_new_channel(self, log_envelope):
        # Primeira tentativa cai no erro de canal (exchange inexistente);
        # a segunda precisa rodar em um canal novo, não no canal morto.
        publisher = LogPublisher(
            amqp_url='amqp://localhost', exchange='chatbot'
        )

        dead_channel = _live_channel()
        dead_channel.get_exchange = AsyncMock(
            side_effect=RuntimeError("NOT_FOUND - no exchange 'chatbot'")
        )

        exchange = MagicMock()
        exchange.publish = AsyncMock()
        live_channel = _live_channel()
        live_channel.get_exchange = AsyncMock(return_value=exchange)

        connection = MagicMock()
        connection.is_closed = False
        connection.channel = AsyncMock(return_value=live_channel)

        publisher._connection = connection
        publisher._channel = dead_channel

        await publisher.publish_error(log_envelope)

        dead_channel.close.assert_awaited_once()
        exchange.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publish_error_warns_once_when_both_attempts_fail(
        self, log_envelope
    ):
        publisher = LogPublisher(
            amqp_url='amqp://localhost', exchange='chatbot'
        )

        channel = _live_channel()
        channel.get_exchange = AsyncMock(side_effect=RuntimeError('NOT_FOUND'))
        connection = MagicMock()
        connection.is_closed = False
        connection.channel = AsyncMock(return_value=channel)

        publisher._connection = connection
        publisher._channel = channel

        with patch('chatgraph.messages.log_publisher._logger') as mock_logger:
            await publisher.publish_error(log_envelope)

        assert mock_logger.warning.call_count == 1


@pytest.mark.unit
class TestLogPublisherDefaultExchange:
    @pytest.mark.asyncio
    async def test_publish_uses_default_exchange_and_queue_routing_key(
        self, log_envelope
    ):
        publisher = LogPublisher(
            amqp_url='amqp://localhost', queue_name='logs'
        )

        default_exchange = MagicMock()
        default_exchange.publish = AsyncMock()
        channel = _live_channel()
        channel.default_exchange = default_exchange
        channel.get_exchange = AsyncMock(
            side_effect=AssertionError('não deve buscar exchange nomeada')
        )
        connection = MagicMock()
        connection.is_closed = False

        publisher._connection = connection
        publisher._channel = channel

        await publisher.publish_error(log_envelope)

        default_exchange.publish.assert_awaited_once()
        kwargs = default_exchange.publish.await_args.kwargs
        assert kwargs['routing_key'] == 'logs'

    @pytest.mark.asyncio
    async def test_ensure_queue_skips_bind_on_default_exchange(self):
        publisher = LogPublisher(
            amqp_url='amqp://localhost', queue_name='logs'
        )

        queue = MagicMock()
        queue.bind = AsyncMock()
        channel = _live_channel()
        # O declare passivo falha (fila inexistente) e o ativo devolve a fila.
        channel.declare_queue = AsyncMock(
            side_effect=[RuntimeError('NOT_FOUND'), queue]
        )
        connection = MagicMock()
        connection.is_closed = False
        connection.channel = AsyncMock(return_value=channel)

        publisher._connection = connection
        publisher._channel = channel

        await publisher._ensure_queue()

        queue.bind.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ensure_queue_binds_when_exchange_is_named(self):
        publisher = LogPublisher(
            amqp_url='amqp://localhost',
            exchange='chatbot',
            queue_name='logs',
        )

        queue = MagicMock()
        queue.bind = AsyncMock()
        exchange = MagicMock()
        channel = _live_channel()
        channel.declare_queue = AsyncMock(
            side_effect=[RuntimeError('NOT_FOUND'), queue]
        )
        channel.get_exchange = AsyncMock(return_value=exchange)
        connection = MagicMock()
        connection.is_closed = False
        connection.channel = AsyncMock(return_value=channel)

        publisher._connection = connection
        publisher._channel = channel

        await publisher._ensure_queue()

        queue.bind.assert_awaited_once_with(
            exchange=exchange,
            routing_key='chatbot.logs',
        )
