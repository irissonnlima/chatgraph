"""Classe pública Agent: tools locais + protocolo single-agent.

Port do subconjunto MVP de ``core/service/agent/agent.go`` do
chatgraph-go (GenerateProtocol, CallTool, AddTool/GetTools). As
functional options do Go viram kwargs; defaults idênticos.
"""

import asyncio
import inspect
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from dotenv import load_dotenv as _load_dotenv_file
from pydantic import BaseModel

from ..logger.user_logger import UserLoggerManager
from .errors import AgentConfigurationError, ToolExecutionError
from .prompts import build_protocol_system_prompt
from .protocol import (
    AgentContext,
    AgentResult,
    EndActionInfo,
    MenuInfo,
    ToolInfo,
    build_agent_result_schema,
    tolerant_validate,
)
from .schema import normalize
from .types import (
    AgentMessage,
    AgentResponse,
    LLMClient,
    LLMRequest,
    Tool,
    Usage,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..services.router_http_client import RouterHTTPClient
    from ..types.route import Route
    from ..types.usercall import UserCall

_logger = UserLoggerManager.get_system_logger()

# Opt-in para logar o AgentContext completo (inclui a observation, onde
# dados pessoais do usuário se acumulam). Sem ele, só o shape é logado.
LOG_AGENT_CONTEXT_ENV = 'LOG_AGENT_CONTEXT'


class Agent:
    """Agente de IA integrado ao protocolo chatgraph.

    Args:
        llm_client: Implementação de LLMClient (ex.: OpenRouterClient).
        model: Modelo a usar (ex.: 'openai/gpt-4o-mini').
        system_prompt: Prompt de personalidade programático.
        system_prompt_file: Caminho de arquivo com o prompt de
            personalidade (lido no construtor; erro claro se ausente).
        temperature/max_tokens/max_tool_loops: Defaults do Go
            (0.7 / 2048 / 5).
        tools: Tools locais registradas no construtor.
        menus: MenuInfo disponíveis para a ação transfer_menu (bot→bot).
        end_actions: EndActionInfo disponíveis para a ação end_session
            (encerrar atendimento OU transferir para atendente
            humano — no chatbot-router as duas são a mesma operação).
            Sem end_actions configuradas, end_action_id continua livre
            e DEFAULT_END_ACTION_ID cobre a omissão (retrocompatível).
        observation_model: Modelo pydantic da observation (gera o
            observation_schema do protocolo).
        history_limit: Janela de histórico enviada ao LLM.
        usage_observer: Callback chamado com o Usage de cada chamada.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        llm_client: LLMClient,
        model: str,
        system_prompt: str = '',
        system_prompt_file: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_tool_loops: int = 5,
        tools: Optional[list[Tool]] = None,
        menus: Optional[list[MenuInfo]] = None,
        end_actions: Optional[list[EndActionInfo]] = None,
        observation_model: Optional[type[BaseModel]] = None,
        history_limit: int = 20,
        usage_observer: Optional[Callable[[Usage], None]] = None,
    ) -> None:
        if llm_client is None:
            raise AgentConfigurationError(
                'llm_client é obrigatório para o Agent.'
            )
        if not model:
            raise AgentConfigurationError('model é obrigatório para o Agent.')
        self.llm_client = llm_client
        self.model = model
        self.system_prompt = system_prompt
        self.system_prompt_text = self._read_prompt_file(system_prompt_file)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_tool_loops = max_tool_loops
        self.menus = [
            menu
            if isinstance(menu, MenuInfo)
            else MenuInfo.model_validate(menu)
            for menu in (menus or [])
        ]
        self.end_actions = [
            end_action
            if isinstance(end_action, EndActionInfo)
            else EndActionInfo.model_validate(end_action)
            for end_action in (end_actions or [])
        ]
        self.observation_model = observation_model
        self.history_limit = history_limit
        self.usage_observer = usage_observer
        self._tools: list[Tool] = []
        for tool in tools or []:
            self.add_tool(tool)

    @classmethod
    def load_dotenv(  # noqa: PLR0913
        cls,
        llm_client: LLMClient,
        *,
        model_env: str = 'AGENT_MODEL',
        temperature_env: str = 'AGENT_TEMPERATURE',
        max_tokens_env: str = 'AGENT_MAX_TOKENS',
        max_tool_loops_env: str = 'AGENT_MAX_TOOL_LOOPS',
        history_limit_env: str = 'AGENT_HISTORY_LIMIT',
        system_prompt_file_env: str = 'AGENT_SYSTEM_PROMPT_FILE',
        **kwargs: Any,
    ) -> 'Agent':
        """Cria o Agent a partir de variáveis de ambiente (.env).
        ``model`` é obrigatório; o resto usa os defaults do Go."""
        _load_dotenv_file()
        model = os.getenv(model_env, '')
        if not model:
            raise ValueError(
                f'A variável de ambiente {model_env} é obrigatória '
                'para o Agent.'
            )
        if os.getenv(temperature_env):
            kwargs.setdefault(
                'temperature', float(os.environ[temperature_env])
            )
        if os.getenv(max_tokens_env):
            kwargs.setdefault('max_tokens', int(os.environ[max_tokens_env]))
        if os.getenv(max_tool_loops_env):
            kwargs.setdefault(
                'max_tool_loops', int(os.environ[max_tool_loops_env])
            )
        if os.getenv(history_limit_env):
            kwargs.setdefault(
                'history_limit', int(os.environ[history_limit_env])
            )
        if os.getenv(system_prompt_file_env):
            kwargs.setdefault(
                'system_prompt_file', os.environ[system_prompt_file_env]
            )
        return cls(llm_client=llm_client, model=model, **kwargs)

    @staticmethod
    def _read_prompt_file(path: Optional[str]) -> str:
        """Lê o prompt de personalidade do arquivo (equivalente ao
        panic do WithSystemPromptFile do Go: falha alto e cedo)."""
        if not path:
            return ''
        try:
            return Path(path).read_text(encoding='utf-8')
        except OSError as exc:
            raise AgentConfigurationError(
                f'system_prompt_file não pôde ser lido: {path} ({exc})'
            ) from exc

    # ------------------------------------------------------------------
    # Tools locais
    # ------------------------------------------------------------------

    def add_tool(self, tool: Tool) -> None:
        """Registra uma tool. Uma tool já registrada com o mesmo nome é
        substituída, não duplicada: duplicatas seriam anunciadas duas
        vezes no system prompt, gastando tokens e convidando o modelo a
        escolher entre entradas idênticas.

        Os parameters são normalizados aqui — o ponto único por onde
        toda tool passa (mesma estratégia do Go para tools de MCP).
        """
        tool.parameters = self._normalize_tool_parameters(tool)
        for index, existing in enumerate(self._tools):
            if existing.name == tool.name:
                self._tools[index] = tool
                return
        self._tools.append(tool)

    @staticmethod
    def _normalize_tool_parameters(tool: Tool) -> Optional[dict]:
        """Normaliza o schema de parâmetros no registro. Um schema
        inutilizável passa adiante em vez de ser derrubado: uma tool
        malformada não deve derrubar o agente."""
        params = tool.parameters
        if params is None:
            return None
        if isinstance(params, dict):
            return normalize(params)
        if isinstance(params, type) and issubclass(params, BaseModel):
            return normalize(params.model_json_schema())
        _logger.warning(
            f'Tool {tool.name}: parameters de tipo não suportado '
            f'({type(params).__name__}), usando como está'
        )
        return params

    def tool(
        self,
        name: Optional[str] = None,
        *,
        description: str = '',
        parameters: Any = None,
    ) -> Callable:
        """Decorator para registrar uma função como tool do agente::

        @agent.tool(description='Consulta pedido',
                    parameters={'type': 'object', ...})
        async def consultar_pedido(cpf: str) -> str: ...
        """

        def decorator(func: Callable) -> Callable:
            self.add_tool(
                Tool(
                    name=name or func.__name__,
                    description=description,
                    parameters=parameters,
                    handler=func,
                )
            )
            return func

        return decorator

    def get_tools(self) -> list[ToolInfo]:
        """Lista as tools disponíveis para a IA."""
        return [
            ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
            )
            for tool in self._tools
        ]

    async def call_tool(self, name: str, arguments: Any) -> str:
        """Executa uma tool local e retorna o resultado como string."""
        tool = next((t for t in self._tools if t.name == name), None)
        if tool is None or tool.handler is None:
            raise ToolExecutionError(
                f"agent: tool '{name}' não registrada ou sem handler"
            )

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except (ValueError, json.JSONDecodeError) as exc:
                raise ToolExecutionError(
                    f"agent: argumentos inválidos para a tool '{name}': {exc}"
                ) from exc

        preview = _truncate(json.dumps(arguments, default=str), 80)
        _logger.info(f'Agent Tool Call | name={name} | args={preview}')

        started = time.monotonic()
        try:
            result = await self._invoke_handler(tool.handler, arguments)
        except ToolExecutionError:
            raise
        except Exception as exc:
            elapsed_ms = (time.monotonic() - started) * 1000
            _logger.error(
                f'Agent Tool Failed | name={name} '
                f'| duration_ms={elapsed_ms:.0f} | err={exc}'
            )
            raise ToolExecutionError(
                f"agent: tool call '{name}' failed: {exc}"
            ) from exc
        elapsed_ms = (time.monotonic() - started) * 1000

        if result is None:
            raise ToolExecutionError(
                f"agent: tool call '{name}' returned no result"
            )
        if isinstance(result, (dict, list)):
            result = json.dumps(result, ensure_ascii=False)
        elif not isinstance(result, str):
            result = str(result)

        _logger.info(
            f'Agent Tool Result | name={name} '
            f'| duration_ms={elapsed_ms:.0f} | bytes={len(result)}'
        )
        return result

    @staticmethod
    async def _invoke_handler(handler: Callable, arguments: Any) -> Any:
        """Invoca o handler (sync roda em executor). Argumentos dict
        viram kwargs; outros valores viram argumento posicional."""
        if isinstance(arguments, dict):
            call = lambda: handler(**arguments)  # noqa: E731
        elif arguments is None:
            call = handler
        else:
            call = lambda: handler(arguments)  # noqa: E731

        if inspect.iscoroutinefunction(handler):
            return await call()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, call)

    # ------------------------------------------------------------------
    # Protocolo single-agent
    # ------------------------------------------------------------------

    async def generate_protocol(
        self,
        agent_ctx: AgentContext,
        usage: Optional[Usage] = None,
    ) -> AgentResult:
        """Uma chamada de LLM que produz o texto de resposta e as ações
        a executar (port de ``GenerateProtocol``).

        ``usage`` é um acumulador local do turno (passado pelo
        executor); nada de estado mutável fica no Agent.
        """
        protocol_prompt = build_protocol_system_prompt(
            agent_ctx.available_routes,
            agent_ctx.observation_schema,
            agent_ctx.available_tools,
            agent_ctx.available_menus,
            agent_ctx.available_end_actions,
        )

        # System prompts na ordem: arquivo → programático → protocolo.
        messages: list[AgentMessage] = []
        if self.system_prompt_text:
            messages.append(
                AgentMessage(role='system', content=self.system_prompt_text)
            )
        if self.system_prompt:
            messages.append(
                AgentMessage(role='system', content=self.system_prompt)
            )
        messages.append(AgentMessage(role='system', content=protocol_prompt))
        messages.extend(agent_ctx.history or [])

        ctx_json = agent_ctx.model_dump_json(exclude_none=True)
        messages.append(AgentMessage(role='user', content=ctx_json))

        # Tools NÃO são enviadas como function definitions nativas: o
        # protocolo espera tools requisitadas declarativamente via ação
        # call_tool, e tool_calls nativos na resposta eram descartados —
        # oferecer os dois convidava o modelo a responder na forma que
        # é jogada fora. As tools chegam pelo system prompt.
        request = LLMRequest(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            structured_output=build_agent_result_schema(
                tuple(menu.name for menu in self.menus),
                tuple(end_action.name for end_action in self.end_actions),
            ),
        )

        _logger.debug(
            f'LLM Request | model={self.model} '
            f'| messages={len(messages)} '
            f'| tools={len(agent_ctx.available_tools or [])} '
            f'| temperature={self.temperature} '
            f'| max_tokens={self.max_tokens}'
        )
        _log_agent_context(agent_ctx, ctx_json)

        response = await self.llm_client.generate(request)
        self._report_usage('protocol', response, usage)

        _logger.debug(
            f'LLM Response | finish_reason={response.finish_reason} '
            f'| text={bool(response.text)} '
            f'| structured_output='
            f'{response.structured_output is not None}'
        )

        raw = response.structured_output
        if raw is None and response.text:
            # Fallback: structured output ausente mas há texto — tenta
            # parsear o texto como o JSON do protocolo.
            try:
                raw = json.loads(response.text)
            except (ValueError, json.JSONDecodeError):
                _logger.warning(
                    'GenerateProtocol: resposta sem structured output '
                    'e texto não é JSON; retornando resultado vazio'
                )
        if raw is None:
            return AgentResult()

        return tolerant_validate(AgentResult, raw)

    def _report_usage(
        self,
        phase: str,
        response: AgentResponse,
        usage: Optional[Usage],
    ) -> None:
        """Registra o consumo da chamada no acumulador do turno e
        notifica o observer."""
        call_usage = response.usage
        _logger.debug(
            f'LLM usage | phase={phase} | model={call_usage.model} '
            f'| prompt={call_usage.prompt_tokens} '
            f'| completion={call_usage.completion_tokens} '
            f'| total={call_usage.total_tokens}'
        )
        if usage is not None:
            usage.add(call_usage)
        if self.usage_observer is not None:
            try:
                self.usage_observer(call_usage)
            except Exception as exc:
                _logger.warning(f'usage_observer falhou: {exc}')

    async def execute(
        self, usercall: 'UserCall', route: 'Route'
    ) -> Optional[list]:
        """Açúcar para ``execute_single_agent(usercall, route, self)``
        — espelha o ``ctx.ExecuteSingleAgent()`` do Go."""
        # Import tardio: o executor importa Agent para type hints.
        from .executor import execute_single_agent  # noqa: PLC0415

        return await execute_single_agent(usercall, route, self)

    async def validate_config(self, router_client: 'RouterHTTPClient') -> None:
        """Confirma que os menus e end actions configurados existem de
        verdade no chatbot-router.

        Opt-in — chame no boot do bot, fora do caminho de mensagem: são
        chamadas HTTP que não têm por que rodar a cada turno, e o
        objetivo é falhar cedo e alto (uma configuração errada nunca
        chegou a ser exercitada por um usuário) em vez de só aparecer
        quando o modelo tentar usar a transferência.
        """
        errors: list[str] = []

        if self.menus:
            try:
                existing_menus = await router_client.get_menus()
            except Exception as exc:
                errors.append(f'não foi possível listar os menus: {exc}')
            else:
                known = {
                    menu.name.strip().lower()
                    for menu in existing_menus
                    if menu.name
                }
                for menu in self.menus:
                    name = menu.name.strip()
                    if name and name.lower() not in known:
                        errors.append(
                            f'menu {name!r} não existe no chatbot-router'
                        )

        for end_action in self.end_actions:
            name = end_action.name.strip()
            if not name:
                continue
            try:
                await router_client.get_end_action(end_action.id or '', name)
            except Exception as exc:
                errors.append(
                    f'end action {name!r} não existe no chatbot-router: {exc}'
                )

        if errors:
            raise AgentConfigurationError(
                'agent: validate_config failed:\n- ' + '\n- '.join(errors)
            )


def _log_agent_context(agent_ctx: AgentContext, ctx_json: str) -> None:
    """Loga o AgentContext para diagnóstico.

    O contexto embute a observation da sessão — exatamente onde dados
    pessoais do usuário se acumulam. O payload completo exige opt-in
    via LOG_AGENT_CONTEXT=1; senão só o shape não-sensível é logado.
    """
    flag = os.getenv(LOG_AGENT_CONTEXT_ENV, '')
    if flag == '1' or flag.lower() == 'true':
        _logger.debug(f'LLM AgentContext | json={ctx_json}')
        return
    _logger.debug(
        'LLM AgentContext '
        f'| route={agent_ctx.route.current} '
        f'| previous_route={agent_ctx.route.previous} '
        f'| auth_level={agent_ctx.user.auth_level} '
        f'| history_messages={len(agent_ctx.history or [])} '
        f'| available_routes={len(agent_ctx.available_routes)} '
        f'| available_tools={len(agent_ctx.available_tools or [])} '
        f'| available_menus={len(agent_ctx.available_menus or [])} '
        f'| observation_fields='
        f'{_observation_field_names(agent_ctx.observation)} '
        f'| bytes={len(ctx_json)} '
        f'| hint={LOG_AGENT_CONTEXT_ENV}=1 para logar o contexto '
        'completo, incluindo dados do usuário'
    )


def _observation_field_names(observation: Any) -> list[str]:
    """Lista as chaves preenchidas da observation sem os valores, para
    o log mostrar o que foi coletado sem revelar o conteúdo."""
    if not isinstance(observation, dict):
        return []
    names = []
    for key, value in observation.items():
        if value is None:
            continue
        if isinstance(value, str) and value in {'', 'null'}:
            continue
        names.append(key)
    return sorted(names)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + '...'
