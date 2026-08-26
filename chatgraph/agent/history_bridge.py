"""Ponte entre o módulo de histórico do chatgraph e as mensagens do LLM.

Port de ``core/domain/history/{entry,trim}.go`` (``ToAgentMessages`` e
``TrimSafe``) e do ``recordToolExchange`` de ``protocol_shared.go`` do
chatgraph-go.
"""

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from ..history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)
from ..history.keys import generate_idempotency_key
from .types import AgentMessage, ToolCall

if TYPE_CHECKING:  # pragma: no cover
    from ..types.usercall import UserCall

# Limita o recuo do trim_safe atrás da mensagem assistant dona de um
# resultado de tool. Um turno produz uma mensagem assistant por
# resultado, então o recuo normalmente para em um passo; o teto só
# protege contra um histórico patológico crescendo a janela sem limite.
MAX_TOOL_LOOKBACK = 32


def to_agent_messages(
    entries: list[HistoryEntry],
) -> list[AgentMessage]:
    """Converte entradas de histórico em mensagens do LLM.

    Filtra entradas sem conteúdo, exceto quando têm tool_calls
    (mensagens assistant com tool_calls podem ter content vazio).
    Eventos de navegação (ROUTE_CHANGE/TRANSFER/END_CHAT) são pulados.
    """
    messages: list[AgentMessage] = []
    for entry in entries:
        message = _entry_to_message(entry)
        if message is None:
            continue
        if not message.content and not message.tool_calls:
            continue
        messages.append(message)
    return messages


def _entry_to_message(entry: HistoryEntry) -> Optional[AgentMessage]:
    """Mapeia uma entrada de histórico para uma mensagem do LLM."""
    event = entry.event_type
    if event == HistoryEventType.MESSAGE_IN:
        return AgentMessage(role='user', content=_text_of(entry))
    if event == HistoryEventType.MESSAGE_OUT:
        return AgentMessage(role='assistant', content=_text_of(entry))
    if event == HistoryEventType.TOOL_CALL:
        tool_calls = [
            ToolCall.model_validate(call) for call in (entry.tool_calls or [])
        ]
        return AgentMessage(
            role='assistant', content='', tool_calls=tool_calls or None
        )
    if event == HistoryEventType.TOOL_RESULT:
        return AgentMessage(
            role='tool',
            content=str(entry.metadata.get('content', '')),
            tool_call_id=entry.tool_call_id,
        )
    return None


def _text_of(entry: HistoryEntry) -> str:
    """Extrai o texto de uma entrada MESSAGE_IN/MESSAGE_OUT."""
    message = entry.message or {}
    text_message = message.get('text_message') or {}
    return str(text_message.get('detail') or '')


def trim_safe(messages: list[AgentMessage], limit: int) -> list[AgentMessage]:
    """Retorna no máximo ``limit`` mensagens finais sem quebrar o
    pareamento de tools.

    Um corte simples das últimas N pode separar a mensagem assistant
    com tool_calls da mensagem role "tool" que a responde. A API do
    OpenAI/OpenRouter rejeita uma mensagem tool que não responde nada,
    então esse corte vira HTTP 400 na próxima chamada.

    O início da janela recua para incluir a assistant dona. Se não der
    dentro de MAX_TOOL_LOOKBACK, os resultados órfãos são descartados
    da frente — perder uma troca de tool é recuperável, uma lista de
    mensagens inválida não é.

    ``limit <= 0`` retorna tudo inalterado.
    """
    if limit <= 0 or len(messages) <= limit:
        return messages

    start = len(messages) - limit

    # Recua atrás dos resultados de tool para a janela incluir a
    # mensagem assistant que os requisitou.
    steps = 0
    while (
        start > 0
        and messages[start].role == 'tool'
        and steps < MAX_TOOL_LOOKBACK
    ):
        start -= 1
        steps += 1

    # Ainda começando em resultado de tool: a assistant dona está fora
    # de alcance, então descarta os órfãos em vez de emitir lista
    # inválida.
    while start < len(messages) and messages[start].role == 'tool':
        start += 1

    return messages[start:]


async def record_tool_exchange(
    usercall: 'UserCall',
    tool_name: str,
    arguments: Any,
    content: str,
) -> None:
    """Grava o par de mensagens assistant/tool de uma chamada de tool.

    A mensagem assistant com tool_calls precisa preceder a mensagem
    role "tool" — a API rejeita uma mensagem tool que não responde
    nada. O ID é sintetizado porque o modelo requisita tools de forma
    declarativa (não function calling nativo), então não existe ID do
    provedor.

    Fire-and-forget: falhas geram warning e nunca propagam.
    """
    store = usercall.history
    if store is None:
        return

    tool_call_id = f'call_{tool_name}_{time.time_ns()}'

    arguments_json = '{}'
    if arguments is not None:
        try:
            arguments_json = json.dumps(arguments, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            usercall.logger.warning(
                f'Tool exchange: falha ao serializar argumentos de '
                f'{tool_name}: {exc}'
            )

    chat_id = f'{usercall.user_id}:{usercall.company_id}'
    route = usercall.route

    call_entry = HistoryEntry(
        idempotency_key=generate_idempotency_key(
            chat_id,
            usercall.session_id,
            HistoryRole.BOT.value,
            HistoryEventType.TOOL_CALL.value,
            route,
            tool_call_id,
        ),
        chat_id=chat_id,
        session_id=usercall.session_id,
        role=HistoryRole.BOT,
        event_type=HistoryEventType.TOOL_CALL,
        timestamp=datetime.now(),
        route=route,
        tool_calls=[
            {
                'id': tool_call_id,
                'name': tool_name,
                'arguments': arguments_json,
            }
        ],
    )
    result_entry = HistoryEntry(
        idempotency_key=generate_idempotency_key(
            chat_id,
            usercall.session_id,
            HistoryRole.TOOL.value,
            HistoryEventType.TOOL_RESULT.value,
            route,
            tool_call_id,
        ),
        chat_id=chat_id,
        session_id=usercall.session_id,
        role=HistoryRole.TOOL,
        event_type=HistoryEventType.TOOL_RESULT,
        timestamp=datetime.now(),
        route=route,
        metadata={'content': content},
        tool_call_id=tool_call_id,
    )

    for entry in (call_entry, result_entry):
        try:
            await store.record(entry)
        except BaseException as exc:  # noqa: PLW1641 - fire-and-forget
            usercall.logger.warning(
                f'Tool exchange: falha ao registrar histórico '
                f'({entry.event_type.value}): {exc}'
            )
