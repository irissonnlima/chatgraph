"""
Modelos de dados para arquivos do chatbot.

Este módulo contém as dataclasses e enums para representar arquivos,
incluindo imagens, vídeos, áudios e documentos.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SendType(Enum):
    """
    Tipo de envio de arquivo.

    Attributes:
        IMAGE: Arquivo de imagem
        VIDEO: Arquivo de vídeo
        AUDIO: Arquivo de áudio
        FILE: Arquivo genérico/documento
    """

    IMAGE = 'IMAGE'
    VIDEO = 'VIDEO'
    AUDIO = 'AUDIO'
    FILE = 'FILE'

    @classmethod
    def from_string(cls, value: str) -> 'SendType':
        """
        Cria SendType a partir de string.

        Args:
            value: String representando o tipo

        Returns:
            SendType correspondente

        Raises:
            ValueError: Se o valor não for válido
        """
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f'invalid send type: {value}')

    @classmethod
    def from_mime_type(cls, mime_type: str) -> 'SendType':
        """
        Determina o SendType baseado no MIME type.

        Args:
            mime_type: MIME type do arquivo

        Returns:
            SendType correspondente
        """
        if mime_type.startswith('image/'):
            return cls.IMAGE
        elif mime_type.startswith('video/'):
            return cls.VIDEO
        elif mime_type.startswith('audio/'):
            return cls.AUDIO
        else:
            return cls.FILE


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
    send_type: Optional[SendType] = None
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

        return cls(
            id=data.get('id', ''),
            url=data.get('url', ''),
            name=data.get('name', ''),
            mime_type=data.get('mime_type', ''),
            size=data.get('size', 0),
            object_key=data.get('object_key', ''),
            created_at=data.get('created_at', ''),
            expires_after_days=data.get('expires_after_days', 0),
            actualized_at=data.get('actualized_at', ''),
        )


# Instância vazia para comparação
EMPTY_FILE = File()
