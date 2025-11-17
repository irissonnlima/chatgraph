"""
Testes para os modelos de Message.

Este módulo contém testes unitários para SendType, File, ButtonType,
TextMessage, Button e Message.
"""

import pytest
from datetime import datetime
from chatgraph.models.message import (
    File,
    ButtonType,
    TextMessage,
    Button,
    Message,
)

@pytest.mark.unit
class TestFile:
    """Testes para a classe File."""

    def test_file_initialization_defaults(self):
        """Testa inicialização com valores padrão."""
        file = File()

        assert file.id == ''
        assert file.url == ''
        assert file.name == ''
        assert file.mime_type == ''
        assert file.size == 0
        assert file.object_key == ''
        assert file.created_at == ''
        assert file.expires_after_days == 0
        assert file.actualized_at == ''

    def test_file_initialization_with_values(self):
        """Testa inicialização com valores."""
        file = File(
            id='file123',
            url='https://example.com/image.jpg',
            name='image.jpg',
            mime_type='image/jpeg',
            size=1024,
        )

        assert file.id == 'file123'
        assert file.url == 'https://example.com/image.jpg'
        assert file.name == 'image.jpg'
        assert file.mime_type == 'image/jpeg'
        assert file.size == 1024

    def test_file_is_empty_true(self):
        """Testa is_empty retorna True para arquivo vazio."""
        file = File()
        assert file.is_empty() is True

    def test_file_is_empty_false_with_id(self):
        """Testa is_empty retorna False quando tem ID."""
        file = File(id='file123')
        assert file.is_empty() is False

    def test_file_is_empty_false_with_url(self):
        """Testa is_empty retorna False quando tem URL."""
        file = File(url='https://example.com/file.pdf')
        assert file.is_empty() is False

    def test_file_extension(self):
        """Testa método extension."""
        file = File(name='document.pdf')
        assert file.extension() == '.pdf'

        file = File(name='image.PNG')
        assert file.extension() == '.png'

    def test_file_extension_no_extension(self):
        """Testa extension sem extensão."""
        file = File(name='filename')
        assert file.extension() == ''

    def test_file_to_dict(self):
        """Testa conversão para dicionário."""
        file = File(
            id='file123',
            url='https://example.com/image.jpg',
            name='image.jpg',
            size=1024,
        )
        result = file.to_dict()

        assert result['id'] == 'file123'
        assert result['url'] == 'https://example.com/image.jpg'
        assert result['name'] == 'image.jpg'
        assert result['size'] == 1024

    def test_file_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            'id': 'file123',
            'send_type': 'IMAGE',
            'url': 'https://example.com/image.jpg',
            'name': 'image.jpg',
            'mime_type': 'image/jpeg',
            'size': 1024,
        }
        file = File.from_dict(data)

        assert file.id == 'file123'
        assert file.url == 'https://example.com/image.jpg'
        assert file.name == 'image.jpg'
        assert file.size == 1024

@pytest.mark.unit
class TestButtonType:
    """Testes para o enum ButtonType."""

    def test_buttontype_values(self):
        """Testa valores do enum ButtonType."""
        assert ButtonType.POSTBACK.value == 'postback'
        assert ButtonType.URL.value == 'url'

    def test_buttontype_from_string(self):
        """Testa conversão de string para ButtonType."""
        assert ButtonType.from_string('postback') == ButtonType.POSTBACK
        assert ButtonType.from_string('URL') == ButtonType.URL
        assert ButtonType.from_string('PoStBaCk') == ButtonType.POSTBACK

    def test_buttontype_from_string_invalid(self):
        """Testa conversão de string inválida."""
        with pytest.raises(ValueError, match='invalid button type'):
            ButtonType.from_string('invalid')

@pytest.mark.unit
class TestTextMessage:
    """Testes para a classe TextMessage."""

    def test_textmessage_initialization_defaults(self):
        """Testa inicialização com valores padrão."""
        text_msg = TextMessage()

        assert text_msg.id == ''
        assert text_msg.title == ''
        assert text_msg.detail == ''
        assert text_msg.caption == ''
        assert text_msg.mentioned_ids == []

    def test_textmessage_initialization_with_values(self):
        """Testa inicialização com valores."""
        text_msg = TextMessage(
            id='msg123',
            title='Olá',
            detail='Bem-vindo',
            caption='Saudação',
            mentioned_ids=['user1', 'user2'],
        )

        assert text_msg.id == 'msg123'
        assert text_msg.title == 'Olá'
        assert text_msg.detail == 'Bem-vindo'
        assert text_msg.caption == 'Saudação'
        assert text_msg.mentioned_ids == ['user1', 'user2']

    def test_textmessage_to_dict(self):
        """Testa conversão para dicionário."""
        text_msg = TextMessage(id='msg123', title='Olá', detail='Bem-vindo')
        result = text_msg.to_dict()

        assert result == {
            'id': 'msg123',
            'title': 'Olá',
            'detail': 'Bem-vindo',
            'caption': '',
            'mentioned_ids': [],
        }

    def test_textmessage_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            'id': 'msg123',
            'title': 'Olá',
            'detail': 'Bem-vindo',
            'mentioned_ids': ['user1'],
        }
        text_msg = TextMessage.from_dict(data)

        assert text_msg.id == 'msg123'
        assert text_msg.title == 'Olá'
        assert text_msg.detail == 'Bem-vindo'
        assert text_msg.mentioned_ids == ['user1']

@pytest.mark.unit
class TestButton:
    """Testes para a classe Button."""

    def test_button_initialization(self):
        """Testa inicialização do Button."""
        button = Button(
            type=ButtonType.POSTBACK, title='Sim', detail='confirm_yes'
        )

        assert button.type == ButtonType.POSTBACK
        assert button.title == 'Sim'
        assert button.detail == 'confirm_yes'

    def test_button_to_dict(self):
        """Testa conversão para dicionário."""
        button = Button(
            type=ButtonType.URL, title='Site', detail='https://example.com'
        )
        result = button.to_dict()

        assert result == {
            'type': 'url',
            'title': 'Site',
            'detail': 'https://example.com',
        }

    def test_button_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {'type': 'postback', 'title': 'Sim', 'detail': 'confirm_yes'}
        button = Button.from_dict(data)

        assert button.type == ButtonType.POSTBACK
        assert button.title == 'Sim'
        assert button.detail == 'confirm_yes'

@pytest.mark.unit
class TestMessage:
    """Testes para a classe Message."""

    def test_message_initialization_defaults(self):
        """Testa inicialização com valores padrão."""
        message = Message()

        assert isinstance(message.text_message, TextMessage)
        assert message.buttons == []
        assert message.display_button is None
        assert isinstance(message.date_time, datetime)
        assert message.file is None

    def test_message_has_buttons_false(self):
        """Testa has_buttons retorna False."""
        message = Message()
        assert message.has_buttons() is False

    def test_message_has_buttons_true(self):
        """Testa has_buttons retorna True."""
        button = Button(type=ButtonType.POSTBACK, title='Sim')
        message = Message(buttons=[button])
        assert message.has_buttons() is True

    def test_message_has_file_false(self):
        """Testa has_file retorna False."""
        message = Message()
        assert message.has_file() is False

    def test_message_has_file_true(self):
        """Testa has_file retorna True."""
        file = File(id='file123')
        message = Message(file=file)
        assert message.has_file() is True

    def test_message_to_dict(self):
        """Testa conversão para dicionário."""
        text_msg = TextMessage(title='Olá')
        button = Button(type=ButtonType.POSTBACK, title='Sim')
        message = Message(text_message=text_msg, buttons=[button])
        result = message.to_dict()

        assert 'text_message' in result
        assert 'buttons' in result
        assert 'date_time' in result
        assert len(result['buttons']) == 1

    def test_message_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            'text_message': {'title': 'Olá', 'detail': 'Bem-vindo'},
            'buttons': [{'type': 'postback', 'title': 'Sim'}],
            'date_time': '2025-11-14T10:00:00',
        }
        message = Message.from_dict(data)

        assert message.text_message.title == 'Olá'
        assert len(message.buttons) == 1
        assert message.buttons[0].title == 'Sim'
        assert isinstance(message.date_time, datetime)
