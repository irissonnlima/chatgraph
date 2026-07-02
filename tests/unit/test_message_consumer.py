import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatgraph.auth.credentials import Credential
from chatgraph.messages.message_consumer import MessageConsumer
from chatgraph.types.usercall import UserCall


def make_consumer(**kwargs) -> MessageConsumer:
    defaults = dict(
        credential=Credential(username='user', password='pass'),
        amqp_url='rabbitmq.example.com:5672',
        router_url='http://router',
        router_token='token',
        queue_consume='test_queue',
    )
    defaults.update(kwargs)
    return MessageConsumer(**defaults)


@pytest.mark.unit
class TestMessageConsumerInit:
    def test_invalid_heartbeat_raises(self):
        with pytest.raises(ValueError, match='heartbeat'):
            make_consumer(heartbeat=-1)

    def test_invalid_reconnect_interval_raises(self):
        with pytest.raises(ValueError, match='reconnect_interval'):
            make_consumer(reconnect_interval=-1.0)


@pytest.mark.unit
class TestBuildAmqpUrl:
    def test_encodes_special_chars_in_credentials(self):
        consumer = make_consumer(
            credential=Credential(username='test@user', password='p@ss!'),
            amqp_url='rabbitmq.example.com:5672',
            virtual_host='/',
        )
        url = consumer._MessageConsumer__build_amqp_url()
        assert 'test%40user' in url
        assert 'p%40ss%21' in url

    def test_encodes_vhost(self):
        consumer = make_consumer(virtual_host='/myvhost')
        url = consumer._MessageConsumer__build_amqp_url()
        assert '%2Fmyvhost' in url


@pytest.mark.unit
class TestStartConsume:
    @pytest.mark.asyncio
    async def test_reconnects_after_exception(self):
        consumer = make_consumer()

        mock_connection = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        async def connect_side_effect(url, heartbeat):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception('connection refused')
            raise asyncio.CancelledError

        with patch(
            'chatgraph.messages.message_consumer.aio_pika.connect_robust',
            side_effect=connect_side_effect,
        ):
            with patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new_callable=AsyncMock,
            ):
                with patch.object(consumer, 'cleanup', new_callable=AsyncMock):
                    with pytest.raises(asyncio.CancelledError):
                        await consumer.start_consume(AsyncMock())

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cancelled_error_stops_loop(self):
        consumer = make_consumer()

        with patch(
            'chatgraph.messages.message_consumer.aio_pika.connect_robust',
            side_effect=asyncio.CancelledError,
        ):
            with patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new_callable=AsyncMock,
            ):
                with patch.object(consumer, 'cleanup', new_callable=AsyncMock):
                    with pytest.raises(asyncio.CancelledError):
                        await consumer.start_consume(AsyncMock())

    @pytest.mark.asyncio
    async def test_cleanup_called_once(self):
        consumer = make_consumer()
        mock_cleanup = AsyncMock()

        with patch(
            'chatgraph.messages.message_consumer.aio_pika.connect_robust',
            side_effect=asyncio.CancelledError,
        ):
            with patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new_callable=AsyncMock,
            ):
                with patch.object(consumer, 'cleanup', mock_cleanup):
                    with pytest.raises(asyncio.CancelledError):
                        await consumer.start_consume(AsyncMock())

        mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_passed_to_connect_robust(self):
        consumer = make_consumer(heartbeat=60)

        with patch(
            'chatgraph.messages.message_consumer.aio_pika.connect_robust',
            side_effect=asyncio.CancelledError,
        ) as mock_connect:
            with patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new_callable=AsyncMock,
            ):
                with patch.object(consumer, 'cleanup', new_callable=AsyncMock):
                    with pytest.raises(asyncio.CancelledError):
                        await consumer.start_consume(AsyncMock())

        mock_connect.assert_called_once()
        _, kwargs = mock_connect.call_args
        assert kwargs.get('heartbeat') == 60


@pytest.mark.unit
class TestDeclareQueue:
    @pytest.mark.asyncio
    async def test_declares_queue_with_durable_and_arguments(self):
        consumer = make_consumer(queue_consume='my_queue')
        mock_queue = MagicMock()
        mock_queue.bind = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        result = await consumer._MessageConsumer__declare_queue(mock_channel)

        mock_channel.declare_queue.assert_called_once_with(
            'my_queue',
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'log_error',
                'x-expires': 86400000,
                'x-message-ttl': 3600000,
            },
        )
        assert result is mock_queue

    @pytest.mark.asyncio
    async def test_declares_queue_with_custom_ttl_arguments(self):
        consumer = make_consumer(
            queue_consume='my_queue', x_expires=60000, x_message_ttl=10000
        )
        mock_queue = MagicMock()
        mock_queue.bind = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        await consumer._MessageConsumer__declare_queue(mock_channel)

        mock_channel.declare_queue.assert_called_once_with(
            'my_queue',
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'log_error',
                'x-expires': 60000,
                'x-message-ttl': 10000,
            },
        )

    @pytest.mark.asyncio
    async def test_binds_queue_with_expected_exchange_and_routing_key(self):
        consumer = make_consumer(
            queue_consume='my_queue', virtual_host='vhost'
        )

        mock_queue = MagicMock()
        mock_queue.bind = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        result = await consumer._MessageConsumer__declare_queue(mock_channel)

        mock_queue.bind.assert_called_once_with(
            exchange='vhost',
            routing_key='chatbot.my_queue',
        )
        assert result is mock_queue

    @pytest.mark.asyncio
    async def test_declare_queue_exception_is_not_masked(self):
        consumer = make_consumer(queue_consume='my_queue')
        mock_channel = AsyncMock()
        mock_channel.declare_queue = AsyncMock(
            side_effect=RuntimeError('precondition failed')
        )

        with pytest.raises(RuntimeError, match='precondition failed'):
            await consumer._MessageConsumer__declare_queue(mock_channel)


@pytest.mark.unit
class TestOnRequest:
    @pytest.mark.asyncio
    async def test_valid_message_calls_process_message(self):
        consumer = make_consumer()
        mock_usercall = MagicMock(spec=UserCall)
        body = json.dumps({'user_state': {}, 'message': {}}).encode()
        process_message = AsyncMock()

        with patch.object(
            consumer,
            '_MessageConsumer__transform_message',
            new=AsyncMock(return_value=mock_usercall),
        ):
            await consumer.on_request(body, process_message)

        process_message.assert_awaited_once_with(mock_usercall)

    @pytest.mark.asyncio
    async def test_invalid_json_does_not_raise(self):
        consumer = make_consumer()
        process_message = AsyncMock()

        await consumer.on_request(b'not-json', process_message)

    @pytest.mark.asyncio
    async def test_exception_in_process_message_does_not_propagate(self):
        consumer = make_consumer()
        mock_usercall = MagicMock(spec=UserCall)
        body = json.dumps({'user_state': {}, 'message': {}}).encode()
        process_message = AsyncMock(side_effect=RuntimeError('boom'))

        with patch.object(
            consumer,
            '_MessageConsumer__transform_message',
            new=AsyncMock(return_value=mock_usercall),
        ):
            await consumer.on_request(body, process_message)


@pytest.mark.unit
class TestTransformMessage:
    @pytest.mark.asyncio
    async def test_builds_usercall_from_valid_dict(self):
        consumer = make_consumer()
        mock_user_state = MagicMock()
        mock_message = MagicMock()
        mock_router_client = AsyncMock()

        message_dict = {
            'user_state': {'observation': '{}'},
            'message': {},
        }

        with (
            patch(
                'chatgraph.messages.message_consumer.UserState.from_dict',
                return_value=mock_user_state,
            ),
            patch(
                'chatgraph.messages.message_consumer.Message.from_dict',
                return_value=mock_message,
            ),
            patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new=AsyncMock(return_value=mock_router_client),
            ),
        ):
            result = await consumer._MessageConsumer__transform_message(
                message_dict
            )

        assert isinstance(result, UserCall)
        assert result._UserCall__user_state is mock_user_state
        assert result._UserCall__message is mock_message

    @pytest.mark.asyncio
    async def test_observation_string_is_parsed_as_json(self):
        consumer = make_consumer()
        captured_args = {}

        def capture_from_dict(data):
            captured_args['user_state_data'] = data
            return MagicMock()

        mock_router_client = AsyncMock()
        message_dict = {
            'user_state': {'observation': '{"key": "value"}'},
            'message': {},
        }

        with (
            patch(
                'chatgraph.messages.message_consumer.UserState.from_dict',
                side_effect=capture_from_dict,
            ),
            patch(
                'chatgraph.messages.message_consumer.Message.from_dict',
                return_value=MagicMock(),
            ),
            patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new=AsyncMock(return_value=mock_router_client),
            ),
        ):
            await consumer._MessageConsumer__transform_message(message_dict)

        assert (
            captured_args['user_state_data']['observation']
            == '{"key": "value"}'
        )


@pytest.mark.unit
class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_with_no_client_does_not_raise(self):
        consumer = make_consumer()
        await consumer.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_closes_and_resets_client(self):
        consumer = make_consumer()
        mock_client = AsyncMock()
        consumer._MessageConsumer__router_client = mock_client

        await consumer.cleanup()

        mock_client.close.assert_awaited_once()
        assert consumer._MessageConsumer__router_client is None


@pytest.mark.unit
class TestLoadDotenv:
    def test_missing_env_raises_value_error(self, monkeypatch):
        for var in (
            'RABBIT_USER',
            'RABBIT_PASS',
            'RABBIT_URI',
            'RABBIT_QUEUE',
            'ROUTER_URL',
            'ROUTER_TOKEN',
        ):
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ValueError):
            MessageConsumer.load_dotenv()

    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'rabbitmq.example.com:5672')
        monkeypatch.setenv('RABBIT_QUEUE', 'test_queue')
        monkeypatch.setenv('ROUTER_URL', 'http://router')
        monkeypatch.setenv('ROUTER_TOKEN', 'token')
        monkeypatch.setenv('RABBIT_HEARTBEAT', '60')
        monkeypatch.setenv('RABBIT_RECONNECT_INTERVAL', '5.0')

        consumer = MessageConsumer.load_dotenv()

        assert consumer._MessageConsumer__heartbeat == 60
        assert consumer._MessageConsumer__reconnect_interval == 5.0
        assert consumer._MessageConsumer__x_expires == 86400000
        assert consumer._MessageConsumer__x_message_ttl == 3600000

    def test_loads_custom_ttl_from_env(self, monkeypatch):
        monkeypatch.setenv('RABBIT_USER', 'user')
        monkeypatch.setenv('RABBIT_PASS', 'pass')
        monkeypatch.setenv('RABBIT_URI', 'rabbitmq.example.com:5672')
        monkeypatch.setenv('RABBIT_QUEUE', 'test_queue')
        monkeypatch.setenv('ROUTER_URL', 'http://router')
        monkeypatch.setenv('ROUTER_TOKEN', 'token')
        monkeypatch.setenv('RABBIT_X_EXPIRES', '60000')
        monkeypatch.setenv('RABBIT_X_MESSAGE_TTL', '10000')

        consumer = MessageConsumer.load_dotenv()

        assert consumer._MessageConsumer__x_expires == 60000
        assert consumer._MessageConsumer__x_message_ttl == 10000
