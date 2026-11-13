"""
Modelo de dados para mensagens com botão de URL enviadas pelo chatbot.

Este módulo contém a dataclass, as constantes de tamanho, a exceção e as
regras de validação da mensagem `cta_url` da Voll (WhatsApp Enterprise), as
mesmas que o chatbot-router aplica ao montar o envio.
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

from chatgraph.models.message import (
    Button,
    ButtonType,
    File,
    Message,
    SendType,
    TextMessage,
)

URL_BUTTON_MAX_HEADER = 60
URL_BUTTON_MAX_BODY = 1024
URL_BUTTON_MAX_FOOTER = 60
URL_BUTTON_MAX_LABEL = 20


class URLButtonInvalidError(ValueError):
    """A mensagem com botão de URL não cumpre as regras do `cta_url`."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f'URL_BUTTON_INVALID: {reason}')


@dataclass(kw_only=True)
class URLButtonMessage:
    """
    Mensagem com exatamente 1 botão que abre um link.

    Attributes:
        header: Cabeçalho de texto (até 60 caracteres). Fica vazio quando
            `file` é informado
        body: Corpo da mensagem (obrigatório, até 1024 caracteres)
        footer: Rodapé (até 60 caracteres)
        label: Texto do botão (até 20 caracteres)
        url: Link completo com `http://` ou `https://`, enviado como está,
            com os parâmetros já codificados pelo bot (`urllib.parse.quote`)
        file: Imagem, vídeo ou documento que vira o cabeçalho
    """

    header: Optional[str] = ''
    body: str = ''
    footer: Optional[str] = ''
    label: str = ''
    url: str = ''
    file: Optional[File] = None

    def validate(self) -> None:
        """
        Confere as regras do `cta_url`, na ordem, e para na primeira falha.

        O erro nunca carrega o conteúdo da mensagem. Os tamanhos contam
        caracteres Unicode e nenhum valor é aparado.

        Raises:
            URLButtonInvalidError: A mensagem não cumpre alguma regra.
        """
        self._validate(require_file_id=True)

    def to_message(self) -> Message:
        """
        Converte para uma `Message` com 1 botão de URL.

        Não valida e não altera a instância.
        """
        return Message(
            text_message=TextMessage(
                title=self.header or '',
                detail=self.body,
                caption=self.footer or '',
            ),
            buttons=[
                Button(title=self.label, detail=self.url, type=ButtonType.URL)
            ],
            file=self.file,
        )

    def _validate(self, *, require_file_id: bool) -> None:
        if not _is_valid_url(self.url):
            raise URLButtonInvalidError('url_invalid')

        if not isinstance(self.label, str) or not self.label.strip():
            raise URLButtonInvalidError('label_empty')
        if len(self.label) > URL_BUTTON_MAX_LABEL:
            raise URLButtonInvalidError('label_too_long')

        if not isinstance(self.body, str) or not self.body.strip():
            raise URLButtonInvalidError('body_empty')
        if len(self.body) > URL_BUTTON_MAX_BODY:
            raise URLButtonInvalidError('body_too_long')

        header = self.header or ''
        footer = self.footer or ''

        if self.file is not None:
            if require_file_id and not self.file.id:
                raise URLButtonInvalidError('file_without_id')
            if header:
                raise URLButtonInvalidError('header_with_file')
            if self.file.send_type == SendType.AUDIO or (
                self.file.mime_type or ''
            ).lower().startswith('audio/'):
                raise URLButtonInvalidError('file_type_unsupported')
        elif len(header) > URL_BUTTON_MAX_HEADER:
            raise URLButtonInvalidError('header_too_long')

        if len(footer) > URL_BUTTON_MAX_FOOTER:
            raise URLButtonInvalidError('footer_too_long')


def _is_valid_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    # O urlsplit remove \t, \n, \r e o espaço inicial sem avisar; o Router
    # recusa.
    if any(c < ' ' or c == '\x7f' for c in url) or url.startswith(' '):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in {'http', 'https'}:
        return False
    # Host como no `u.Host` do Go: 'https://:80' vale, 'https://user@' não.
    return bool(parts.netloc.rpartition('@')[2])
