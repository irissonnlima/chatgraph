import json
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


@pytest.fixture
def mock_log_publisher():
    publisher = MagicMock()
    publisher.publish_error = AsyncMock()
    return publisher


@pytest.fixture
def mock_usercall():
    usercall = MagicMock(spec=UserCall)
    usercall.user_id = 'user1'
    usercall.company_id = 'company1'
    usercall.session_id = 100
    usercall.route = 'start.test'
    usercall.menu = MagicMock()
    usercall.menu.id = 5
    usercall.menu.name = 'suporte'
    usercall.user_state = MagicMock()
    usercall.user_state.platform = 'whatsapp'
    return usercall


@pytest.mark.unit
class TestOnRequestPublishesError:
    @pytest.mark.asyncio
    async def test_on_request_publishes_error_with_usercall(
        self, mock_log_publisher, mock_usercall
    ):
        consumer = make_consumer()
        consumer.set_log_publisher(mock_log_publisher)

        process_message = AsyncMock(side_effect=RuntimeError('handler error'))

        body = json.dumps({
            'user_state': {'observation': '{}'},
            'message': {},
        }).encode()

        with patch.object(
            consumer,
            '_MessageConsumer__transform_message',
            new=AsyncMock(return_value=mock_usercall),
        ):
            with patch.object(
                consumer,
                '_MessageConsumer__initialize_router',
                new=AsyncMock(),
            ):
                await consumer.on_request(body, process_message)

        mock_log_publisher.publish_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_request_publishes_error_without_usercall(
        self, mock_log_publisher
    ):
        consumer = make_consumer()
        consumer.set_log_publisher(mock_log_publisher)

        process_message = AsyncMock()

        await consumer.on_request(b'not-json', process_message)

        mock_log_publisher.publish_error.assert_awaited_once()
        call_args = mock_log_publisher.publish_error.call_args
        envelope = call_args[0][0]
        assert envelope.origin == 'chatgraph:unknown'

    @pytest.mark.asyncio
    async def test_on_request_no_publisher_no_error(self):
        consumer = make_consumer()
        process_message = AsyncMock()

        await consumer.on_request(b'not-json', process_message)
