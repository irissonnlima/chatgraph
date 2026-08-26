"""Executor do protocolo single-agent com tool calling.

Port de ``ExecuteSingleAgent`` (``protocol_executor.go``), das
proteções de ``protocol_shared.go`` e do ``ExecuteResult``
(``core/domain/context/protocol.go``) do chatgraph-go.

Diferença estrutural: em vez de executar efeitos diretamente, o
executor devolve uma LISTA dos tipos de retorno já existentes do
framework (``Message``, ``Route``, ``RedirectResponse``,
``EndChatResponse``, ``TransferToMenu``) — o ``__process_func_response``
do pipeline processa a lista sem nenhuma alteração. A conversão para na
primeira ação terminal, preservando a semântica do Go.
"""

import json
import time
from typing import TYPE_CHECKING, Any, Optional

from ..logger.user_logger import UserLoggerManager
from ..models.message import Button, ButtonType, Message
from ..types.end_types import (
    EndChatResponse,
    RedirectResponse,
    TransferToMenu,
)
from .agent import Agent
from .context import build_agent_context, merge_observation
from .errors import AgentActionError, AgentError, ToolExecutionError
from .history_bridge import record_tool_exchange
from .protocol import (
    ACTION_CALL_TOOL,
    ACTION_END_SESSION,
    ACTION_NEXT_ROUTE,
    ACTION_REDIRECT,
    ACTION_SEND_MESSAGE,
    ACTION_SET_OBSERVATION,
    ACTION_TRANSFER_MENU,
    DEFAULT_END_ACTION_ID,
    AgentAction,
    AgentResult,
    ProtocolMessage,
    ToolCallRequest,
)
from .types import Usage

if TYPE_CHECKING:  # pragma: no cover
    from ..types.route import Route
    from ..types.usercall import UserCall

_logger = UserLoggerManager.get_system_logger()

# Teto de tentativas de uma mesma tool dentro de um turno. Sem ele, uma
# tool que insiste em falhar é re-requisitada pelo modelo a cada
# iteração até o orçamento inteiro do loop acabar, e o turno termina em
# erro genérico em vez de uma explicação acionável ao usuário.
MAX_ATTEMPTS_PER_TOOL = 2

# Teto de correções por turno para uma ação terminal inválida (ex.:
# transfer_menu/end_session com seletor que não existe). Consome uma
# iteração do orçamento compartilhado de max_tool_loops; sem teto
# próprio, um ping-pong de correções consumiria o turno inteiro só
# tentando a mesma ação de novo.
MAX_ACTION_CORRECTIONS = 1

# Enviada quando o modelo esgota as tentativas de corrigir uma ação
# terminal inválida. Deliberadamente NÃO é result.response: nesses
# casos o texto do modelo costuma ser a promessa da própria ação que
# acabou de falhar (ex.: "vou te transferir"), que não deve chegar ao
# usuário como se tivesse dado certo.
INVALID_ACTION_FALLBACK = (
    'Não consegui concluir essa ação agora. Pode repetir, por favor?'
)


class ToolLoopState:
    """Rastreia execuções de tool no turno para o loop decidir
    progresso."""

    def __init__(self) -> None:
        self.attempts: dict[str, int] = {}

    def record(self, name: str) -> int:
        self.attempts[name] = self.attempts.get(name, 0) + 1
        return self.attempts[name]

    def exhausted(self, name: str) -> bool:
        return self.attempts.get(name, 0) >= MAX_ATTEMPTS_PER_TOOL


async def execute_single_agent(
    usercall: 'UserCall', route: 'Route', agent: Agent
) -> Optional[list]:
    """Roda o protocolo single-agent do chatgraph.

    Uma chamada de LLM produz o texto de resposta e as ações. Tool
    calling: uma ação call_tool executa a tool, guarda o resultado na
    observation e volta ao topo para nova decisão.

    O retorno é a lista de tipos do framework que o handler devolve
    diretamente ao pipeline; ``None`` = permanece no nó (semântica
    "none" existente do ``__process_func_response``).
    """
    tool_state = ToolLoopState()
    turn_usage = Usage()
    started = time.monotonic()
    llm_calls = 0
    pending_correction: Optional[str] = None
    corrections_used = 0

    try:
        for _ in range(agent.max_tool_loops):
            agent_ctx = await build_agent_context(usercall, route, agent)
            agent_ctx.available_tools = agent.get_tools() or None
            agent_ctx.last_action_error = pending_correction
            pending_correction = None

            llm_calls += 1
            result = await agent.generate_protocol(agent_ctx, usage=turn_usage)
            if result is None:
                return None

            tool_call, remaining = split_tool_call_action(result.actions)
            if tool_call is not None:
                continue_loop, early_return = await _advance_after_tool_call(
                    usercall, agent, tool_call, remaining, result, tool_state
                )
                if early_return is not None:
                    return early_return
                if continue_loop:
                    # Loop de volta com o resultado na observation e
                    # histórico.
                    continue

            try:
                return await execute_result(result, usercall, route, agent)
            except AgentActionError as exc:
                if corrections_used >= MAX_ACTION_CORRECTIONS:
                    usercall.logger.error(
                        'Agent: ação inválida sem orçamento de correção, '
                        f'encerrando com fallback | err={exc}'
                    )
                    return [Message(INVALID_ACTION_FALLBACK)]
                corrections_used += 1
                usercall.logger.warning(
                    f'Agent: ação inválida, pedindo correção | err={exc}'
                )
                pending_correction = exc.feedback
                # Loop de volta pedindo a correção no próximo ciclo.
    finally:
        _log_turn_cost(usercall, started, llm_calls, turn_usage)

    usercall.logger.error(
        'Execute single agent: excedeu o máximo de tool loops | '
        f'max={agent.max_tool_loops}'
    )
    raise AgentError(
        'execute single agent: exceeded max tool call loops '
        f'({agent.max_tool_loops})'
    )


async def _advance_after_tool_call(  # noqa: PLR0913, PLR0917
    usercall: 'UserCall',
    agent: Agent,
    tool_call: ToolCallRequest,
    remaining: list[AgentAction],
    result: AgentResult,
    tool_state: ToolLoopState,
) -> tuple[bool, Optional[list]]:
    """Processa o tool_call da iteração atual do loop.

    Retorna ``(continue_loop, early_return)``: ``continue_loop=True``
    pede a próxima iteração (chamar o LLM de novo, resultado já na
    observation); ``early_return`` não-``None`` encerra
    ``execute_single_agent`` com esse valor. Quando nenhum dos dois se
    aplica — a tool já rodou em ciclo anterior (dedup por
    ``result_key``) — ``result.actions`` já sai ajustado e o chamador
    segue para ``execute_result`` na mesma iteração.
    """
    result_key = resolve_result_key(tool_call)
    if tool_result_already_exists(usercall.observation, result_key):
        usercall.logger.warning(
            'Tool call pulada - result_key já na observation | '
            f'result_key={result_key} | tool={tool_call.name}'
        )
        result.actions = remaining
        return False, None

    exhausted = await _execute_tool_call(
        usercall, agent, tool_call, tool_state
    )
    if not exhausted:
        return True, None

    usercall.logger.error(
        'Tool esgotou as tentativas, informando o usuário | '
        f'tool={tool_call.name} | attempts={MAX_ATTEMPTS_PER_TOOL}'
    )
    # A falha já está no histórico; a próxima chamada pode explicá-la.
    # Envia o texto que o modelo já produziu para o turno não ficar mudo.
    if result.response:
        return False, [Message(result.response)]
    raise ToolExecutionError(
        f"execute single agent: tool '{tool_call.name}' failed after "
        f'{MAX_ATTEMPTS_PER_TOOL} attempts'
    )


async def execute_result(  # noqa: PLR0912, PLR0915 - espelha o switch do Go
    result: AgentResult,
    usercall: 'UserCall',
    route: 'Route',
    agent: Agent,
) -> Optional[list]:
    """Converte as ações do AgentResult nos tipos de retorno do
    framework, executando ``set_observation`` inline.

    Se nenhuma ação enviou mensagem mas o resultado tem texto, o texto
    é emitido antes do retorno — sem esse fallback um modelo que
    preencheu "response" e não emitiu send_message deixaria o usuário
    sem resposta.
    """
    if result is None:
        return None

    # Resolve a primeira transferência/end action alcançável ANTES de
    # executar qualquer ação: send_message/set_observation não devem
    # produzir efeitos quando o terminal que os segue é inválido.
    resolved_transfer = _resolve_reachable_transfer(
        result.actions, result, agent
    )
    resolved_end_action = _resolve_reachable_end_action(result.actions, agent)

    returns: list = []
    message_sent = False

    for index, action in enumerate(result.actions):
        if action.is_terminal() and index != len(result.actions) - 1:
            usercall.logger.warning(
                'Agent: ação terminal fora da última posição, ações '
                f'seguintes ignoradas | type={action.type} '
                f'| position={index} '
                f'| ignored={len(result.actions) - index - 1}'
            )

        if action.type == ACTION_SEND_MESSAGE:
            message = _send_message_of(action, result)
            if message is not None:
                returns.append(message)
                message_sent = True

        elif action.type == ACTION_SET_OBSERVATION:
            usercall.logger.info('Agent action | type=set_observation')
            await merge_observation(usercall, action.observation)

        elif action.type == ACTION_NEXT_ROUTE:
            target = (action.target_route or '').strip().lower()
            usercall.logger.info(
                f'Agent action | type=next_route | target={target}'
            )
            if not _known_route(route, target):
                usercall.logger.warning(
                    'Agent: next_route para rota desconhecida, '
                    f'tratando como none | target={target}'
                )
                break
            message_sent = _append_pending_response(
                returns, result, message_sent
            )
            returns.append(route.get_next(target))
            break

        elif action.type == ACTION_REDIRECT:
            target = (action.target_route or '').strip().lower()
            usercall.logger.info(
                f'Agent action | type=redirect | target={target}'
            )
            if target == route.current_node:
                # Redirect para a própria rota é sempre erro de lógica:
                # o engine reentraria no mesmo handler sem resposta.
                usercall.logger.warning(
                    'Self-redirect detectado, convertendo para none | '
                    f'route={target}'
                )
                break
            if not _known_route(route, target):
                usercall.logger.warning(
                    'Agent: redirect para rota desconhecida, tratando '
                    f'como none | target={target}'
                )
                break
            # SILENT REDIRECT: a rota destino produz a própria
            # resposta, então o texto pendente NÃO é enviado aqui.
            returns.append(RedirectResponse(target))
            return returns or None

        elif action.type == ACTION_END_SESSION:
            end_action_name = ''
            if agent.end_actions:
                if resolved_end_action is None:
                    raise AgentError(
                        'agent: end_session failed: reachable end '
                        'action was not resolved'
                    )
                end_action_id, end_action_name = resolved_end_action
            else:
                end_action_id = action.end_action_id or ''
                if not end_action_id:
                    # A API do chatbot-router rejeita end_session sem ID.
                    end_action_id = DEFAULT_END_ACTION_ID
                    usercall.logger.warning(
                        'Agent decidiu end_session sem end_action_id, '
                        f'usando default | default={DEFAULT_END_ACTION_ID}'
                    )
            usercall.logger.info(
                f'Agent action | type=end_session | reason={end_action_id}'
            )
            message_sent = _append_pending_response(
                returns, result, message_sent
            )
            returns.append(
                EndChatResponse(
                    end_chat_id=end_action_id,
                    end_chat_name=end_action_name,
                )
            )
            break

        elif action.type == ACTION_TRANSFER_MENU:
            usercall.logger.info(
                f'Agent action | type=transfer_menu | menu={action.menu}'
            )
            if resolved_transfer is None:
                raise AgentError(
                    'agent: transfer_menu failed: reachable transfer '
                    'was not resolved'
                )
            message_sent = _append_pending_response(
                returns, result, message_sent
            )
            returns.append(resolved_transfer)
            break

        elif action.type == ACTION_CALL_TOOL:
            # A execução de tool acontece no executor do protocolo, que
            # já retirou o primeiro call_tool da lista; um remanescente
            # pertence a um ciclo futuro, não a este.
            tool_name = action.tool_call.name if action.tool_call else ''
            usercall.logger.info(
                'Agent action call_tool adiada para o próximo ciclo | '
                f'tool={tool_name}'
            )

        else:
            usercall.logger.warning(
                f'Agent: tipo de ação desconhecido, pulando | '
                f'type={action.type}'
            )

    _append_pending_response(returns, result, message_sent)
    return returns or None


def _send_message_of(
    action: AgentAction, result: AgentResult
) -> Optional[Message]:
    """Constrói a mensagem de uma ação send_message: o payload da ação
    (com botões) quando presente, senão o texto do response."""
    payload = action.message
    if payload is not None:
        return _protocol_message_to_message(payload)
    if result.response:
        return Message(result.response)
    return None


def _protocol_message_to_message(payload: ProtocolMessage) -> Message:
    buttons = [
        Button(
            title=button.title,
            detail=button.detail or button.title,
            type=ButtonType.POSTBACK,
        )
        for button in payload.buttons or []
    ]
    return Message(payload.detail, buttons=buttons)


def _append_pending_response(
    returns: list, result: AgentResult, message_sent: bool
) -> bool:
    """Emite result.response quando nenhuma ação enviou mensagem.
    No-op quando já houve mensagem ou não há texto."""
    if message_sent or not result.response:
        return message_sent
    _logger.info(
        'Agent response não coberta por nenhuma ação, enviando | '
        f'preview={_truncate(result.response, 80)}'
    )
    returns.append(Message(result.response))
    return True


def _known_route(route: 'Route', target: str) -> bool:
    routes = route.routes or []
    return bool(target) and target in routes


def _resolve_reachable_transfer(
    actions: list[AgentAction],
    result: AgentResult,
    agent: Agent,
) -> Optional[TransferToMenu]:
    """Resolve apenas a primeira ação terminal quando é transfer_menu.
    Terminais posteriores são inalcançáveis e intencionalmente
    ignorados. Falha levanta erro ANTES de qualquer side effect.

    Seletor: ``menu`` (name) casado contra ``agent.menus`` com o
    ``target_route`` copiado da entrada (divergência consciente do Go,
    que seleciona por queue/menu_id).
    """
    for action in actions:
        if not action.is_terminal():
            continue
        if action.type != ACTION_TRANSFER_MENU:
            return None

        name = (action.menu or '').strip()
        requested_route = (action.target_route or '').strip() or 'start'
        if not name:
            raise AgentActionError(
                'agent: transfer_menu failed: menu (name) is required',
                feedback=(
                    'transfer_menu requires "menu" set to one of the '
                    'AVAILABLE MENUS names.'
                ),
            )

        for menu in agent.menus:
            configured_route = (menu.route or '').strip() or 'start'
            if menu.name.strip() != name:
                continue
            if configured_route != requested_route:
                continue
            return TransferToMenu(
                menu=menu.name,
                user_message=menu.message or result.response,
                route=requested_route,
            )

        available = ', '.join(
            sorted({m.name.strip() for m in agent.menus if m.name.strip()})
        )
        raise AgentActionError(
            f'agent: transfer_menu failed: menu {name!r} with '
            f'target_route {requested_route!r} is not in the '
            'configured menus',
            feedback=(
                f'menu {name!r} with target_route {requested_route!r} '
                f'does not exist. Choose one of: {available or "(none)"}.'
            ),
        )

    return None


def _resolve_reachable_end_action(
    actions: list[AgentAction],
    agent: Agent,
) -> Optional[tuple[str, str]]:
    """Resolve a end action da primeira ação terminal end_session
    contra ``agent.end_actions``, quando configuradas.

    Sem end_actions configuradas, retorna None sempre — o chamador
    mantém o comportamento histórico (end_action_id livre, com
    DEFAULT_END_ACTION_ID como fallback). Com a lista configurada,
    ``end_action_id`` vira um SELETOR (por name, depois por id) em vez
    de um ID livre repassado direto ao router: end_session cobre tanto
    encerrar quanto transferir para atendente humano, então um
    seletor errado aqui é o mesmo tipo de erro que um menu errado no
    transfer_menu. Falha levanta erro ANTES de qualquer side effect.
    """
    if not agent.end_actions:
        return None

    for action in actions:
        if not action.is_terminal():
            continue
        if action.type != ACTION_END_SESSION:
            return None

        selector = (action.end_action_id or '').strip()
        if not selector:
            raise AgentActionError(
                'agent: end_session failed: end_action_id is required',
                feedback=(
                    'end_session requires "end_action_id" set to one '
                    'of the AVAILABLE END ACTIONS names.'
                ),
            )

        for info in agent.end_actions:
            if info.name.strip() == selector or (info.id or '') == selector:
                return info.id or '', info.name

        available = ', '.join(
            sorted({
                i.name.strip() for i in agent.end_actions if i.name.strip()
            })
        )
        raise AgentActionError(
            f'agent: end_session failed: end_action_id {selector!r} '
            'is not in the configured end actions',
            feedback=(
                f'end_action_id {selector!r} does not exist. Choose '
                f'one of: {available or "(none)"}.'
            ),
        )

    return None


def split_tool_call_action(
    actions: list[AgentAction],
) -> tuple[Optional[ToolCallRequest], list[AgentAction]]:
    """Retorna o primeiro call_tool da lista e as ações seguintes.

    Um tool call SUSPENDE o turno, então ações enfileiradas depois dele
    são reexecutadas no próximo ciclo em vez de rodarem contra um
    estado que a tool ainda não atualizou. Um terminal antes de
    qualquer call_tool devolve a lista intacta.
    """
    for index, action in enumerate(actions):
        if action.is_terminal():
            return None, actions
        if action.type != ACTION_CALL_TOOL:
            continue
        if action.tool_call is None:
            _logger.warning(
                'Agent action call_tool sem payload tool_call, ignorando'
            )
            continue
        return action.tool_call, actions[index + 1 :]
    return None, actions


def resolve_result_key(request: ToolCallRequest) -> str:
    """Campo da observation onde o resultado da tool é guardado.
    Default ``"<tool>_result"`` quando o modelo não especifica."""
    return request.result_key or f'{request.name}_result'


def tool_result_already_exists(observation: Any, key: str) -> bool:
    """Verifica se a chave já existe na observation com valor não-vazio
    (evita chamadas duplicadas de tool)."""
    if not isinstance(observation, dict):
        return False
    value = observation.get(key)
    if value is None:
        return False
    if isinstance(value, str) and not value:
        return False
    if isinstance(value, dict) and not value:
        return False
    return True


async def _execute_tool_call(
    usercall: 'UserCall',
    agent: Agent,
    request: ToolCallRequest,
    state: ToolLoopState,
) -> bool:
    """Executa um tool call requisitado pelo modelo e registra o
    desfecho.

    Falhas são reportadas de volta ao modelo pelo histórico da conversa
    em vez de engolidas: um modelo que não vê a falha simplesmente
    requisita a tool de novo. Retorna True (esgotado) quando a tool
    falhou MAX_ATTEMPTS_PER_TOOL vezes, dizendo ao chamador para parar
    de retentar e explicar a falha ao usuário.
    """
    result_key = resolve_result_key(request)
    attempt = state.record(request.name)

    try:
        result = await agent.call_tool(request.name, request.arguments)
    except Exception as exc:
        usercall.logger.error(
            f'Tool call falhou | tool={request.name} '
            f'| attempt={attempt} | err={exc}'
        )
        # Torna a falha visível ao modelo na próxima iteração.
        await record_tool_exchange(
            usercall,
            request.name,
            request.arguments,
            _tool_error_payload(exc),
        )
        return state.exhausted(request.name)

    await record_tool_exchange(
        usercall, request.name, request.arguments, result
    )
    await _store_tool_result(usercall, result_key, result)
    return False


async def _store_tool_result(
    usercall: 'UserCall', result_key: str, result: str
) -> None:
    """Faz merge do resultado da tool na observation sob result_key.
    O resultado entra como JSON parseado quando válido; senão como a
    string crua — o modelo o recebe de um jeito ou de outro."""
    try:
        parsed: Any = json.loads(result)
    except (ValueError, json.JSONDecodeError):
        parsed = result
    await merge_observation(usercall, {result_key: parsed})


def _tool_error_payload(exc: Exception) -> str:
    return json.dumps({'error': str(exc)}, ensure_ascii=False)


def _log_turn_cost(
    usercall: 'UserCall',
    started: float,
    llm_calls: int,
    usage: Usage,
) -> None:
    """Emite o consumo agregado de tokens e o tempo de um turno.

    Números por chamada não bastam para raciocinar sobre custo: uma
    única mensagem pode disparar vários loops de tool.
    """
    duration_ms = (time.monotonic() - started) * 1000
    usercall.logger.info(
        'Agent turn completed | protocol=single_agent '
        f'| route={usercall.route} '
        f'| session_id={usercall.session_id} '
        f'| duration_ms={duration_ms:.0f} '
        f'| llm_calls={llm_calls} '
        f'| prompt_tokens={usage.prompt_tokens} '
        f'| completion_tokens={usage.completion_tokens} '
        f'| total_tokens={usage.total_tokens}'
    )


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + '...'
