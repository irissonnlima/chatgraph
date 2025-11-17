"""
Modelos de dados para mensagens do chatbot.

Este módulo contém as dataclasses e enums para representar mensagens,
botões, arquivos e seus tipos no sistema de chatbot.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


@dataclass
class File:
    """
    Representa um arquivo no sistema.

    Attributes:
        id: ID único do arquivo
        send_type: Tipo de envio (IMAGE, VIDEO, AUDIO, FILE)
        url: URL do arquivo
        name: Nome do arquivo (ex: "document.pdf")
        mime_type: Tipo MIME do arquivo
        size: Tamanho em bytes
        object_key: Chave do objeto no storage
        created_at: Data/hora de criação (ISO 8601)
        expires_after_days: Dias até expiração
        actualized_at: Data/hora de última atualização (ISO 8601)
    """

    id: str = ''
    send_type: Optional[str] = ''
    url: str = ''
    name: str = ''
    mime_type: str = ''
    size: int = 0
    object_key: str = ''
    created_at: str = ''
    expires_after_days: int = 0
    actualized_at: str = ''

    def is_empty(self) -> bool:
        """Verifica se o arquivo está vazio."""
        return not self.id and not self.url and not self.name

    def extension(self) -> str:
        """
        Retorna a extensão do arquivo em minúsculas.

        Returns:
            Extensão do arquivo (ex: ".pdf")
        """
        if not self.name or '.' not in self.name:
            return ''
        return self.name[self.name.rfind('.') :].lower()

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        data = {
            'id': self.id,
            'url': self.url,
            'name': self.name,
            'mime_type': self.mime_type,
            'size': self.size,
            'object_key': self.object_key,
            'created_at': self.created_at,
            'expires_after_days': self.expires_after_days,
            'actualized_at': self.actualized_at,
        }

        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'File':
        """Cria instância a partir de dicionário."""
        send_type = None

        return cls(
            id=data.get('id', ''),
            send_type=send_type,
            url=data.get('url', ''),
            name=data.get('name', ''),
            mime_type=data.get('mime_type', ''),
            size=data.get('size', 0),
            object_key=data.get('object_key', ''),
            created_at=data.get('created_at', ''),
            expires_after_days=data.get('expires_after_days', 0),
            actualized_at=data.get('actualized_at', ''),
        )


class ButtonType(Enum):
    """
    Tipo de botão de mensagem.

    Attributes:
        POSTBACK: Botão que envia dados de volta ao sistema
        URL: Botão que abre um link externo
    """

    POSTBACK = 'postback'
    URL = 'url'

    @classmethod
    def from_string(cls, value: str) -> 'ButtonType':
        """
        Cria ButtonType a partir de string.

        Args:
            value: String representando o tipo ("postback" ou "url")

        Returns:
            ButtonType correspondente

        Raises:
            ValueError: Se o valor não for válido
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f'invalid button type: {value}')


@dataclass
class TextMessage:
    """
    Mensagem de texto.

    Attributes:
        id: ID único da mensagem
        title: Título da mensagem
        detail: Conteúdo detalhado da mensagem
        caption: Legenda da mensagem
        mentioned_ids: IDs de usuários mencionados
    """

    id: str = ''
    title: str = ''
    detail: str = ''
    caption: str = ''
    mentioned_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            'id': self.id,
            'title': self.title,
            'detail': self.detail,
            'caption': self.caption,
            'mentioned_ids': self.mentioned_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TextMessage':
        """Cria instância a partir de dicionário."""
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            detail=data.get('detail', ''),
            caption=data.get('caption', ''),
            mentioned_ids=data.get('mentioned_ids', []),
        )


@dataclass
class Button:
    """
    Botão de mensagem interativa.

    Attributes:
        type: Tipo do botão (POSTBACK ou URL)
        title: Título do botão
        detail: Detalhe/payload do botão
    """

    title: str = ''
    detail: str = ''
    type: ButtonType = ButtonType.POSTBACK

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            'type': self.type.value,
            'title': self.title,
            'detail': self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Button':
        """Cria instância a partir de dicionário."""
        button_type = ButtonType.from_string(data.get('type', 'postback'))
        return cls(
            type=button_type,
            title=data.get('title', ''),
            detail=data.get('detail', ''),
        )


@dataclass
class Message:
    """
    Mensagem completa com texto, botões e anexos.

    Attributes:
        text_message: Conteúdo textual da mensagem
        buttons: Lista de botões interativos
        display_button: Botão de exibição principal
        date_time: Data e hora da mensagem
        file: Arquivo anexado (opcional)
    """

    def __init__(
        self,
        text_message: TextMessage | str,
        buttons: List[Button] = [],
        display_button: Optional[Button] = None,
        file: Optional[File] = None,
    ):
        self.text_message = text_message
        if isinstance(text_message, str):
            self.text_message = TextMessage(detail=text_message)

    text_message: TextMessage = field(default_factory=TextMessage)
    buttons: List[Button] = field(default_factory=list)
    display_button: Optional[Button] = None
    date_time: datetime = field(default_factory=datetime.now)
    file: Optional[File] = None

    def has_buttons(self) -> bool:
        """Verifica se a mensagem possui botões."""
        return len(self.buttons) > 0

    def has_file(self) -> bool:
        """Verifica se a mensagem possui arquivo anexado."""
        return self.file is not None

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        data = {
            'text_message': self.text_message.to_dict(),
            'buttons': [btn.to_dict() for btn in self.buttons],
            'date_time': self.date_time.isoformat(),
        }

        if self.display_button:
            data['display_button'] = self.display_button.to_dict()
        if self.file:
            data['file'] = self.file

        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """Cria instância a partir de dicionário."""
        text_message_data = data.get('text_message', {})
        buttons_data = data.get('buttons', [])
        display_button_data = data.get('display_button')

        date_time = datetime.now()
        if 'date_time' in data:
            try:
                date_time = datetime.fromisoformat(data['date_time'])
            except (ValueError, TypeError):
                pass

        return cls(
            text_message=TextMessage.from_dict(text_message_data),
            buttons=[Button.from_dict(btn) for btn in buttons_data],
            display_button=(
                Button.from_dict(display_button_data)
                if display_button_data
                else None
            ),
            date_time=date_time,
            file=data.get('file'),
        )
