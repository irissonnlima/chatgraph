"""Tipos base do módulo de agentes.

Port de ``core/domain/agent/types.go`` e da interface ``ILLMClient``
(``core/ports/adapters/output/llm_client.go``) do chatgraph-go.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Union

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    """Uma chamada de tool emitida pelo modelo (function calling)."""

    model_config = ConfigDict(extra='ignore')

    id: str = ''
    name: str = ''
    arguments: str = ''  # JSON string, como no Go


class AgentMessage(BaseModel):
    """Mensagem de conversa no formato do LLM (user/assistant/tool)."""

    model_config = ConfigDict(extra='ignore')

    role: str
    content: str = ''
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None


class Usage(BaseModel):
    """Consumo de tokens de uma chamada (ou agregado de um turno)."""

    model_config = ConfigDict(extra='ignore')

    model: str = ''
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def is_zero(self) -> bool:
        return (
            self.prompt_tokens == 0
            and self.completion_tokens == 0
            and self.total_tokens == 0
        )

    def add(self, other: 'Usage') -> None:
        """Acumula ``other`` neste Usage. O campo ``model`` não é
        copiado: o agregado pode misturar modelos."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens


class AgentResponse(BaseModel):
    """Resposta bruta de uma chamada ao LLM."""

    model_config = ConfigDict(extra='ignore')

    text: str = ''
    tool_calls: list[ToolCall] = Field(default_factory=list)
    structured_output: Any = None
    finish_reason: str = ''
    usage: Usage = Field(default_factory=Usage)


# Handler de tool local: recebe os argumentos e retorna o resultado.
# Pode ser síncrono ou assíncrono; dict/list de retorno vira JSON.
ToolHandler = Callable[..., Any]


@dataclass
class Tool:
    """Uma tool registrável no agente.

    ``parameters`` aceita um JSON Schema (dict) ou um modelo pydantic
    (a classe, não a instância) — ambos são normalizados no registro.
    """

    name: str
    description: str = ''
    parameters: Union[dict, type, None] = None
    handler: Optional[ToolHandler] = None


@dataclass
class LLMRequest:
    """Requisição a um provedor de LLM (port de ``LLMRequest`` do Go)."""

    model: str
    messages: list[AgentMessage]
    tools: list[Tool] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2048
    structured_output: Optional[dict] = None


class LLMClient(Protocol):
    """Contrato de provedor de LLM (port de ``ILLMClient`` do Go).

    Trocar de provedor = nova implementação deste Protocol.
    """

    async def generate(self, request: LLMRequest) -> AgentResponse: ...
