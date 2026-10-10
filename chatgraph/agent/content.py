"""Geração de conteúdo desacoplada do protocolo de chat.

Caso de uso: analisar dados internos do bot (ex.: uma consulta a
banco) e pedir um insight à IA — não é uma mensagem de cliente, não
tem rota, não tem menu, não é um turno de chat. Reaproveita a camada
genérica do protocolo single-agent (``LLMClient``, ``AgentMessage``,
``schema.normalize``, ``tolerant_validate``) sem tocar em
``AgentContext``, ``build_protocol_system_prompt`` ou
``build_agent_result_schema``, que são específicos do roteamento.

Sem equivalente no chatgraph-go — extensão própria do lado Python.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel

from ..logger.user_logger import UserLoggerManager
from .protocol import tolerant_validate
from .schema import normalize
from .types import AgentMessage, LLMClient, LLMRequest, Usage

_logger = UserLoggerManager.get_system_logger()


@dataclass
class ContentResult:
    """Resultado de ``generate_content``.

    ``data`` só é preenchido quando ``response_model`` foi passado e o
    provedor devolveu algo parseável; caso contrário fica ``None`` e
    ``text`` carrega a resposta livre do modelo.
    """

    text: str
    data: Optional[BaseModel] = None
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = ''


async def generate_content(  # noqa: PLR0913
    llm_client: LLMClient,
    model: str,
    content: str,
    *,
    system_prompt: str = '',
    response_model: Optional[type[BaseModel]] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    history: Optional[list[AgentMessage]] = None,
    usage_observer: Optional[Callable[[Usage], None]] = None,
) -> ContentResult:
    """Uma chamada de LLM para analisar ``content`` — um dado interno
    do bot, já serializado pelo chamador (linhas de banco, JSON, CSV).
    Esta função não sabe nada sobre a origem do dado: é uma folha, como
    ``schema.py``.

    Sem ``response_model``, a resposta é o texto livre do modelo. Com
    ``response_model``, o structured output vai como o schema fechado
    do modelo (``schema.normalize`` — a variante que garante raiz de
    objeto, exigida pelo Structured Outputs) e ``ContentResult.data``
    volta parseado por ``tolerant_validate``.

    ``history`` é opcional, para follow-up sobre o mesmo conteúdo (ex.:
    uma segunda pergunta sobre o mesmo relatório) — cada chamada é
    isolada por padrão, sem exigir um ``HistoryStore``.
    """
    messages: list[AgentMessage] = []
    if system_prompt:
        messages.append(AgentMessage(role='system', content=system_prompt))
    messages.extend(history or [])
    messages.append(AgentMessage(role='user', content=content))

    structured_output = (
        normalize(response_model.model_json_schema())
        if response_model is not None
        else None
    )
    request = LLMRequest(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        structured_output=structured_output,
    )

    _logger.debug(
        f'generate_content request | model={model} '
        f'| messages={len(messages)} '
        f'| structured_output={structured_output is not None}'
    )

    response = await llm_client.generate(request)

    _logger.debug(
        f'generate_content usage | model={response.usage.model} '
        f'| prompt={response.usage.prompt_tokens} '
        f'| completion={response.usage.completion_tokens} '
        f'| total={response.usage.total_tokens}'
    )
    if usage_observer is not None:
        try:
            usage_observer(response.usage)
        except Exception as exc:
            _logger.warning(f'usage_observer falhou: {exc}')

    return ContentResult(
        text=response.text,
        data=_parse_data(response_model, response),
        usage=response.usage,
        finish_reason=response.finish_reason,
    )


def _parse_data(
    response_model: Optional[type[BaseModel]], response: Any
) -> Optional[BaseModel]:
    """Resolve ``ContentResult.data``: prioriza o structured output do
    provedor; sem ele, tenta decodificar ``response.text`` como JSON —
    mesmo fallback do protocolo de ações (``Agent.generate_protocol``)
    para um provedor que não respeitou o schema."""
    if response_model is None:
        return None

    raw = response.structured_output
    if raw is None and response.text:
        try:
            raw = json.loads(response.text)
        except (ValueError, json.JSONDecodeError):
            _logger.warning(
                'generate_content: resposta sem structured output e '
                'texto não é JSON; data fica None'
            )
    if raw is None:
        return None
    return tolerant_validate(response_model, raw)
