"""
Modelos de dados para ações do chatbot.

Este módulo contém as dataclasses e enums para representar ações
como transferências e encerramentos de chat.
"""

from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """
    Tipo de ação no sistema.

    Attributes:
        TRANSFER: Transferência para atendimento humano
        END_CHAT: Encerramento de chat
        MESSAGE: Mensagem
    """

    TRANSFER = "TRANSFER"
    END_CHAT = "END_CHAT"
    MESSAGE = "MESSAGE"

    @classmethod
    def from_string(cls, value: str) -> "ActionType":
        """
        Cria ActionType a partir de string.

        Args:
            value: String representando o tipo

        Returns:
            ActionType correspondente

        Raises:
            ValueError: Se o valor não for válido
        """
        try:
            return cls(value.upper())
        except ValueError:
            raise ValueError(f"invalid action type: {value}")


@dataclass
class EndAction:
    """
    Ação de encerramento de chat.

    Attributes:
        id: ID único da ação
        name: Nome da ação/tabulação
        department_id: ID do departamento
        observation: Observação sobre o encerramento
        last_update: Data/hora de última atualização (ISO 8601)
    """

    id: str = ""
    name: str = ""
    department_id: int = 0
    observation: str = ""
    last_update: str = ""

    def is_empty(self) -> bool:
        """Verifica se a ação está vazia."""
        return not self.id and not self.name

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "id": self.id,
            "name": self.name,
            "department_id": self.department_id,
            "observation": self.observation,
            "last_update": self.last_update,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EndAction":
        """Cria instância a partir de dicionário."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            department_id=data.get("department_id", 0),
            observation=data.get("observation", ""),
            last_update=data.get("last_update", ""),
        )


@dataclass
class TransferToHumanAction:
    """
    Ação de transferência para atendimento humano.

    Attributes:
        id: ID único da ação
        name: Nome da campanha/fila
        department_id: ID do departamento
        observation: Observação sobre a transferência
        last_update: Data/hora de última atualização (ISO 8601)
    """

    id: int = 0
    name: str = ""
    department_id: int = 0
    observation: str = ""
    last_update: str = ""

    def is_empty(self) -> bool:
        """Verifica se a ação está vazia."""
        return not self.id and not self.name

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "id": self.id,
            "name": self.name,
            "department_id": self.department_id,
            "observation": self.observation,
            "last_update": self.last_update,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TransferToHumanAction":
        """Cria instância a partir de dicionário."""
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            department_id=data.get("department_id", 0),
            observation=data.get("observation", ""),
            last_update=data.get("last_update", ""),
        )


# Instâncias vazias para comparação
EMPTY_END_ACTION = EndAction()
EMPTY_TRANSFER_TO_HUMAN_ACTION = TransferToHumanAction()
