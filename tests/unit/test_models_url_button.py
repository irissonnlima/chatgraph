# ruff: noqa: PLR6301 - testes em classe, como nos demais arquivos de
# tests/unit.
"""
Testes para o modelo de mensagem com botão de URL.
"""

import importlib
import json

import pytest

import chatgraph
from chatgraph.models.message import (
    Button,
    ButtonType,
    File,
    SendType,
)
from chatgraph.models.platform_state import PlatformState
from chatgraph.models.url_button import (
    URLButtonInvalidError,
    URLButtonMessage,
)
from chatgraph.models.userstate import (
    AuthLevel,
    ChatID,
    Menu,
    User,
    UserData,
    UserIdentity,
    UserState,
)
from chatgraph.services.router_http_client import RouterHTTPClient

URL = 'https://exemplo.com.br/fatura/98765'
BODY = 'Sua fatura de novembro já está disponível.'

BASE = {
    'header': 'Sua fatura',
    'body': BODY,
    'footer': 'Verdecard',
    'label': 'Ver fatura',
    'url': URL,
}


def make(**changes) -> URLButtonMessage:
    return URLButtonMessage(**{**BASE, **changes})


OK_CASES = [
    pytest.param({}, id='base'),
    pytest.param(
        {'header': '', 'footer': ''}, id='so_body_label_e_url_sem_header'
    ),
    pytest.param({'header': None, 'footer': None}, id='header_footer_none'),
    pytest.param({'url': 'http://exemplo.com.br/a'}, id='url_http'),
    pytest.param({'url': 'HTTPS://EXEMPLO.COM.BR/x'}, id='url_maiuscula'),
    pytest.param(
        {'url': 'https://exemplo.com.br/' + 'a' * 477},
        id='url_de_500_caracteres',
    ),
    pytest.param({'url': 'https://:80'}, id='url_so_porta_paridade_go'),
    pytest.param({'label': 'á' * 20}, id='label_20_caracteres'),
    pytest.param({'body': 'á' * 1024}, id='body_1024_caracteres_nao_bytes'),
    pytest.param({'header': 'x' * 60}, id='header_60'),
    pytest.param({'footer': 'x' * 60}, id='footer_60'),
    pytest.param(
        {
            'header': '',
            'file': File(id='abc', send_type=SendType.IMAGE),
        },
        id='arquivo_imagem',
    ),
    pytest.param(
        {
            'header': '',
            'file': File(
                id='abc',
                send_type=SendType.FILE,
                mime_type='application/pdf',
            ),
        },
        id='arquivo_documento',
    ),
]

ERROR_CASES = [
    pytest.param(
        {'url': 'www.exemplo.com.br'}, 'url_invalid', id='url_sem_scheme'
    ),
    pytest.param(
        {'url': 'ftp://exemplo.com.br/a'}, 'url_invalid', id='url_ftp'
    ),
    pytest.param({'url': 'https://'}, 'url_invalid', id='url_sem_host'),
    pytest.param({'url': 'https://user@'}, 'url_invalid', id='url_so_usuario'),
    pytest.param({'url': ''}, 'url_invalid', id='url_vazia'),
    pytest.param(
        {'url': ' https://exemplo.com.br/a'},
        'url_invalid',
        id='url_com_espaco_inicial',
    ),
    pytest.param({'url': None}, 'url_invalid', id='url_none'),
    pytest.param(
        {'url': 'https://exemplo.com.br/a\n'},
        'url_invalid',
        id='url_com_caractere_de_controle',
    ),
    pytest.param(
        {'url': 'http://[::1'}, 'url_invalid', id='url_value_error_do_urlsplit'
    ),
    pytest.param({'label': 'á' * 21}, 'label_too_long', id='label_21'),
    pytest.param({'label': '   '}, 'label_empty', id='label_so_espacos'),
    pytest.param({'label': None}, 'label_empty', id='label_none'),
    pytest.param({'body': ''}, 'body_empty', id='body_vazio'),
    pytest.param({'body': '  '}, 'body_empty', id='body_so_espacos'),
    pytest.param({'body': None}, 'body_empty', id='body_none'),
    pytest.param({'body': 'á' * 1025}, 'body_too_long', id='body_1025'),
    pytest.param({'header': 'x' * 61}, 'header_too_long', id='header_61'),
    pytest.param({'footer': 'x' * 61}, 'footer_too_long', id='footer_61'),
    pytest.param(
        {'header': '', 'file': File(id='')},
        'file_without_id',
        id='arquivo_sem_id',
    ),
    pytest.param(
        {'header': 'x', 'file': File(id='abc')},
        'header_with_file',
        id='header_com_arquivo',
    ),
    pytest.param(
        {
            'header': '',
            'file': File(id='abc', send_type=SendType.AUDIO),
        },
        'file_type_unsupported',
        id='arquivo_audio_por_send_type',
    ),
    pytest.param(
        {
            'header': '',
            'file': File(
                id='abc', send_type=SendType.FILE, mime_type='Audio/OGG'
            ),
        },
        'file_type_unsupported',
        id='arquivo_audio_por_mime',
    ),
    pytest.param(
        {'header': 'x' * 61, 'file': File(id='abc')},
        'header_with_file',
        id='com_arquivo_tamanho_do_header_nao_e_conferido',
    ),
    pytest.param(
        {'url': 'www.exemplo.com.br', 'body': ''},
        'url_invalid',
        id='duas_falhas_vale_a_ordem',
    ),
]


@pytest.mark.unit
class TestURLButtonValidate:
    @pytest.mark.parametrize('changes', OK_CASES)
    def test_valid_message_does_not_raise(self, changes):
        assert make(**changes).validate() is None

    @pytest.mark.parametrize(('changes', 'reason'), ERROR_CASES)
    def test_invalid_message_raises_with_reason(self, changes, reason):
        m = make(**changes)

        with pytest.raises(URLButtonInvalidError) as exc_info:
            m.validate()

        exc = exc_info.value
        assert exc.reason == reason
        assert str(exc) == f'URL_BUTTON_INVALID: {reason}'
        assert isinstance(exc, ValueError)
        for value in (m.url, m.label, m.body):
            if isinstance(value, str) and value.strip():
                assert value not in str(exc)

    def test_error_message_does_not_leak_content(self):
        m = make(url='ftp://exemplo.com.br/token-secreto')

        with pytest.raises(URLButtonInvalidError) as exc_info:
            m.validate()

        text = str(exc_info.value)
        assert 'token-secreto' not in text
        assert 'Ver fatura' not in text
        assert BODY not in text

    def test_validate_without_file_id_requirement_accepts_local_file(self):
        m = make(header='', file=File(name='fatura.png'))

        assert m._validate(require_file_id=False) is None

    def test_validate_with_file_id_requirement_rejects_local_file(self):
        m = make(header='', file=File(name='fatura.png'))

        with pytest.raises(URLButtonInvalidError) as exc_info:
            m._validate(require_file_id=True)

        assert exc_info.value.reason == 'file_without_id'

    def test_positional_construction_is_rejected(self):
        with pytest.raises(TypeError):
            URLButtonMessage('a')


@pytest.mark.unit
class TestURLButtonToMessage:
    def test_base_message_maps_fields(self):
        m = make()

        msg = m.to_message()

        assert msg.text_message.title == 'Sua fatura'
        assert msg.text_message.detail == BODY
        assert msg.text_message.caption == 'Verdecard'
        assert msg.buttons == [
            Button(title='Ver fatura', detail=URL, type=ButtonType.URL)
        ]
        assert msg.file is None
        assert 'file' not in msg.to_dict()

    def test_none_header_and_footer_become_empty(self):
        msg = make(header=None, footer=None).to_message()

        assert not msg.text_message.title
        assert not msg.text_message.caption

    def test_file_is_carried_to_message(self):
        file = File(id='abc', send_type=SendType.IMAGE, name='fatura.png')
        m = make(header='', file=file)

        msg = m.to_message()

        assert msg.file is m.file
        assert msg.has_file()

    def test_invalid_message_converts_without_error(self):
        msg = make(body='').to_message()

        assert not msg.text_message.detail
        assert len(msg.buttons) == 1

    def test_each_call_returns_a_new_buttons_list(self):
        m = make()

        assert m.to_message().buttons is not m.to_message().buttons

    def test_to_message_does_not_change_the_instance(self):
        m = make(header='', file=File(id='abc', send_type=SendType.IMAGE))
        before = make(header='', file=File(id='abc', send_type=SendType.IMAGE))

        m.to_message()

        assert m == before


@pytest.fixture
def user_state():
    return UserState(
        chat_id=ChatID(user_id='user123', company_id='company456'),
        platform='whatsapp',
        session_id=1,
        menu=Menu(name='Suporte'),
        user=User(
            data=UserData(name='João Silva'),
            identity=UserIdentity(auth_level=AuthLevel.READ),
        ),
        route='start',
    )


def build_payload(m: URLButtonMessage, user_state: UserState) -> dict:
    payload = RouterHTTPClient.build_send_payload(
        m.to_message(), user_state, PlatformState()
    )
    return json.loads(json.dumps(payload))


@pytest.mark.unit
class TestURLButtonPayload:
    def test_url_button_goes_as_url_type(self, user_state):
        m = make(url='https://exemplo.com.br/f?a=1&b=2')

        payload = build_payload(m, user_state)

        assert payload['message']['buttons'] == [
            {
                'type': 'url',
                'title': 'Ver fatura',
                'detail': 'https://exemplo.com.br/f?a=1&b=2',
            }
        ]

    def test_text_message_fields_in_payload(self, user_state):
        payload = build_payload(make(), user_state)

        text_message = payload['message']['text_message']
        assert text_message['title'] == 'Sua fatura'
        assert text_message['detail'] == BODY
        assert text_message['caption'] == 'Verdecard'

    def test_payload_without_file_has_no_file_key(self, user_state):
        payload = build_payload(make(), user_state)

        assert 'file' not in payload['message']

    def test_payload_with_file_carries_the_id(self, user_state):
        file = File(id='abc', send_type=SendType.IMAGE, name='fatura.png')

        payload = build_payload(make(header='', file=file), user_state)

        assert payload['message']['file']['id'] == 'abc'

    def test_long_url_is_not_truncated(self, user_state):
        url = 'https://exemplo.com.br/' + 'a' * 477

        payload = build_payload(make(url=url), user_state)

        assert payload['message']['buttons'][0]['detail'] == url


@pytest.mark.unit
class TestURLButtonExports:
    @pytest.mark.parametrize(
        ('name', 'module', 'attr'),
        [
            ('ButtonType', 'chatgraph.models.message', 'ButtonType'),
            ('URLButtonMessage', 'chatgraph.models.url_button', None),
            ('URLButtonInvalidError', 'chatgraph.models.url_button', None),
            ('URL_BUTTON_MAX_HEADER', 'chatgraph.models.url_button', None),
            ('URL_BUTTON_MAX_BODY', 'chatgraph.models.url_button', None),
            ('URL_BUTTON_MAX_FOOTER', 'chatgraph.models.url_button', None),
            ('URL_BUTTON_MAX_LABEL', 'chatgraph.models.url_button', None),
        ],
    )
    def test_name_is_exported_from_package(self, name, module, attr):
        origin = importlib.import_module(module)

        assert getattr(chatgraph, name) is getattr(origin, attr or name)
        assert name in chatgraph.__all__
