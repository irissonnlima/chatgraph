import pytest

from chatbot.auth.credentials import Credential
from chatbot.chatbot_app import ChatbotApp
from chatbot.user_state import SimpleUserState


@pytest.fixture
def app():
    credentials = Credential(username='user', password='pass')
    user_state = SimpleUserState()
    return ChatbotApp(
        amqp_url='amqp://localhost',
        queue_consume='test_queue',
        credentials=credentials,
        user_state=user_state,
    )


@pytest.mark.xfail(
    reason='Isso é um método de classe e não deve ser acessível.'
)
def test_chatbot_app_initialization(app):
    assert app.amqp_url == 'amqp://localhost'
    assert app.queue_consume == 'test_queue'


def test_default_handler(app):
    assert app.default_handler('123', 'hello') == 'Transbordo para humano.'


def test_process_message_with_default_handler(app):
    message = '{"customer_id": "123", "text": "hello"}'
    response = app.process_message(message)
    assert response == 'Transbordo para humano.'
