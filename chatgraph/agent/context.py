"""Montagem do AgentContext e merge aditivo da observation.

Port de ``core/domain/context/protocol.go`` (``BuildAgentContext``,
``MergeObservation``, ``availableMenusForAgent``) do chatgraph-go,
adaptado às superfícies do Python: ``UserCall`` + ``Route``.
"""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel

from .agent import Agent
from .history_bridge import (
    MAX_TOOL_LOOKBACK,
    to_agent_messages,
    trim_safe,
)
from .protocol import (
    AgentContext,
    EndActionInfo,
    MenuInfo,
    RouteInfo,
    RouteState,
    UserSummary,
    decode_json_string_maybe,
)
from .schema import normalize_subschema
from .types import AgentMessage

if TYPE_CHECKING:  # pragma: no cover
    from ..types.route import Route
    from ..types.usercall import UserCall


async def build_agent_context(
    usercall: 'UserCall', route: 'Route', agent: Agent
) -> AgentContext:
    """Monta o AgentContext a partir do estado da conversa.

    ``available_tools`` fica por conta do executor (que injeta
    ``agent.get_tools()`` a cada iteração, como no Go).
    """
    observation = usercall.observation or None

    return AgentContext(
        message=AgentMessage(
            role='user', content=usercall.content_message or ''
        ),
        user=_user_summary(usercall),
        route=_route_state(usercall.route),
        observation=observation,
        observation_schema=_observation_schema(agent),
        available_routes=_available_routes(route),
        available_menus=_available_menus(agent.menus),
        available_end_actions=_available_end_actions(agent.end_actions),
        history=await _history_messages(usercall, agent),
    )


def _user_summary(usercall: 'UserCall') -> UserSummary:
    """Subconjunto seguro do usuário (name + auth_level, como no Go)."""
    user = usercall.user
    data = getattr(user, 'data', None)
    name = getattr(data, 'name', None) or ''
    identity = getattr(user, 'identity', None)
    auth_level = getattr(identity, 'auth_level', None)
    return UserSummary(
        name=name,
        auth_level=auth_level.value if auth_level else '',
    )


def _route_state(accumulated: str) -> RouteState:
    """Estado de navegação a partir do caminho acumulado
    ('start.a.b'): nó atual, anterior (dedup) e histórico com o mais
    recente primeiro."""
    parts = [part for part in (accumulated or '').split('.') if part]
    if not parts:
        return RouteState(current='')
    deduped = list(dict.fromkeys(parts))
    previous = deduped[-2] if len(deduped) >= 2 else None  # noqa: PLR2004
    return RouteState(
        current=parts[-1],
        previous=previous,
        history=list(reversed(deduped)),
    )


def _observation_schema(agent: Agent) -> dict:
    """Schema da observation a partir do modelo pydantic do agente
    (substitui a reflection do Go); sem modelo, objeto genérico."""
    if agent.observation_model is None:
        return {'type': 'object'}
    return normalize_subschema(agent.observation_model.model_json_schema())


def _available_routes(route: 'Route') -> list[RouteInfo]:
    """Rotas AI-visíveis com description, vindas do registro
    (``Route.infos``)."""
    infos = getattr(route, 'infos', None) or []
    return [
        RouteInfo(
            name=info['name'], description=info.get('description') or None
        )
        for info in infos
        if info.get('ai_visible')
    ]


def _available_menus(
    menus: list[MenuInfo],
) -> Optional[list[MenuInfo]]:
    """Filtra os menus expostos à IA (port adaptado de
    ``availableMenusForAgent``: descarta entradas sem name; route vazio
    vira 'start' — o seletor aqui é name)."""
    available = [
        menu.model_copy(update={'route': menu.route or 'start'})
        for menu in menus
        if menu.name.strip()
    ]
    return available or None


def _available_end_actions(
    end_actions: list[EndActionInfo],
) -> Optional[list[EndActionInfo]]:
    """Filtra as end actions expostas à IA (mesmo critério de
    ``_available_menus``: descarta entradas sem name)."""
    available = [
        end_action for end_action in end_actions if end_action.name.strip()
    ]
    return available or None


async def _history_messages(
    usercall: 'UserCall', agent: Agent
) -> Optional[list[AgentMessage]]:
    """Histórico convertido para mensagens do LLM, com corte que
    preserva o pareamento assistant/tool."""
    store = usercall.history
    if store is None:
        return None
    chat_id = f'{usercall.user_id}:{usercall.company_id}'
    # Janela maior que o limite para o trim ter margem de recuo.
    fetch_limit = agent.history_limit + MAX_TOOL_LOOKBACK
    try:
        entries = await store.get(
            chat_id, usercall.session_id, limit=fetch_limit
        )
    except BaseException as exc:
        usercall.logger.warning(f'Histórico indisponível para o agente: {exc}')
        return None
    messages = trim_safe(to_agent_messages(entries), agent.history_limit)
    return messages or None


async def merge_observation(usercall: 'UserCall', incoming: Any) -> None:
    """Faz merge ADITIVO de ``incoming`` na observation da sessão.

    Aceita dict, modelo pydantic ou string JSON. Valores vazios
    (``None``, ``''``, a string literal ``'null'``) são ignorados por
    chave — o modelo às vezes devolve campos anulados que não devem
    apagar dados já coletados. Chaves desconhecidas são preservadas
    por construção (``add_observation`` só atualiza o delta).

    Falha vira warning e o turno segue (comportamento do Go).
    """
    delta = _observation_delta(incoming)
    if not delta:
        return
    try:
        await usercall.add_observation(delta)
    except ValueError as exc:
        usercall.logger.warning(
            f'Merge da observation falhou (turno segue): {exc}'
        )


def _observation_delta(incoming: Any) -> Optional[dict]:
    """Normaliza a entrada do merge para um dict filtrado."""
    if incoming is None:
        return None
    if isinstance(incoming, BaseModel):
        incoming = incoming.model_dump(exclude_none=True)
    if isinstance(incoming, str):
        incoming = decode_json_string_maybe(incoming)
    if not isinstance(incoming, dict):
        return None
    filtered = _filter_empty_values(incoming)
    return filtered or None


def _filter_empty_values(value: dict) -> dict:
    """Remove recursivamente valores vazios (None/''/'null' literal),
    port do FilterNullStrings do Go."""
    result = {}
    for key, item in value.items():
        if _is_empty_value(item):
            continue
        cleaned = (
            _filter_empty_values(item) if isinstance(item, dict) else item
        )
        if isinstance(item, dict) and not cleaned:
            continue
        result[key] = cleaned
    return result


def _is_empty_value(value: Any) -> bool:
    return value is None or (
        isinstance(value, str) and value.strip() in {'', 'null'}
    )
