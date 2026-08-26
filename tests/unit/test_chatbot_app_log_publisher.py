from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatgraph.bot.chatbot_model import ChatbotApp
from chatgraph.error.chatbot_error import ChatbotMessageError
from chatgraph.models.log_envelope import is_error_logged
from chatgraph.models.userstate import Menu
from chatgraph.types.usercall import UserCall


@pytest.fixture
def mock_message_consumer():
    return MagicMock()


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
    usercall.content_message = ''
    usercall.menu = Menu(id=5, name='suporte')
    usercall.user_state = MagicMock()
    usercall.user_state.platform = 'whatsapp'
    return usercall


@pytest.mark.unit
class TestProcessMessagePublishesError:
    @pytest.mark.asyncio
    async def test_process_message_publishes_error_on_exception(
        self, mock_message_consumer, mock_log_publisher, mock_usercall
    ):
        app = ChatbotApp(
            message_consumer=mock_message_consumer,
            log_publisher=mock_log_publisher,
        )

        with pytest.raises(ChatbotMessageError):
            await app.process_message(mock_usercall)

        mock_log_publisher.publish_error.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_message_no_publisher_no_error(
        self, mock_message_consumer, mock_usercall
    ):
        app = ChatbotApp(
            message_consumer=mock_message_consumer,
            log_publisher=None,
        )

        with pytest.raises(ChatbotMessageError):
            await app.process_message(mock_usercall)


@pytest.mark.unit
class TestPublishErrorLogMarksException:
    @pytest.mark.asyncio
    async def test_published_exception_is_marked(
        self, mock_message_consumer, mock_log_publisher, mock_usercall
    ):
        app = ChatbotApp(
            message_consumer=mock_message_consumer,
            log_publisher=mock_log_publisher,
        )

        with pytest.raises(ChatbotMessageError) as exc_info:
            await app.process_message(mock_usercall)

        assert is_error_logged(exc_info.value)

    @pytest.mark.asyncio
    async def test_exception_not_marked_without_publisher(
        self, mock_message_consumer, mock_usercall
    ):
        app = ChatbotApp(
            message_consumer=mock_message_consumer,
            log_publisher=None,
        )

        with pytest.raises(ChatbotMessageError) as exc_info:
            await app.process_message(mock_usercall)

        assert not is_error_logged(exc_info.value)


@pytest.mark.unit
class TestPublishErrorLog:
    @pytest.mark.asyncio
    async def test_publish_error_log_menu_none(
        self, mock_message_consumer, mock_log_publisher, mock_usercall
    ):
        mock_usercall.menu = None
        app = ChatbotApp(
            message_consumer=mock_message_consumer,
            log_publisher=mock_log_publisher,
        )

        with pytest.raises(ChatbotMessageError):
            await app.process_message(mock_usercall)

        mock_log_publisher.publish_error.assert_awaited_once()
        call_args = mock_log_publisher.publish_error.call_args
        envelope = call_args[0][0]
        assert envelope.origin == 'chatgraph:unknown'


@pytest.mark.unit
class TestChatbotAppWarnsNoLogPublisher:
    def test_chatbot_app_warns_when_no_log_publisher(
        self, mock_message_consumer, monkeypatch
    ):
        monkeypatch.delenv('LOG_RABBIT_QUEUE', raising=False)

        with patch('chatgraph.bot.chatbot_model._logger') as mock_logger:
            ChatbotApp(
                message_consumer=mock_message_consumer,
                log_publisher=None,
            )

        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if 'LogPublisher não configurado' in str(c)
        ]
        assert len(warning_calls) == 1


@pytest.mark.unit
class TestSetLogPublisherOnConsumer:
    def test_set_log_publisher_called_on_consumer(
        self, mock_message_consumer, mock_log_publisher
    ):
        ChatbotApp(
            message_consumer=mock_message_consumer,
            log_publisher=mock_log_publisher,
        )

        mock_message_consumer.set_log_publisher.assert_called_once_with(
            mock_log_publisher
        )
