"""Protocolo chatgraph: contrato JSON entre o bot e o LLM.

Entrada (chatgraph → IA): ``AgentContext``. Saída (IA → chatgraph):
``AgentResult`` com uma lista ordenada de ``AgentAction``.

Port de ``core/domain/agent/protocol.go`` do chatgraph-go, com uma
divergência consciente: ``transfer_menu`` seleciona o menu por ``menu``
(name) — o client Python só transfere por nome, sem queue/menu_id.
"""

import json
import types
from functools import lru_cache
from typing import Any, Optional, Union, get_args, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from ..logger.user_logger import UserLoggerManager
from .schema import normalize
from .types import AgentMessage

_logger = UserLoggerManager.get_system_logger()

# Tipos de ação válidos.
ACTION_SEND_MESSAGE = 'send_message'
ACTION_NEXT_ROUTE = 'next_route'
ACTION_REDIRECT = 'redirect'
ACTION_END_SESSION = 'end_session'
ACTION_TRANSFER_MENU = 'transfer_menu'
ACTION_SET_OBSERVATION = 'set_observation'
ACTION_CALL_TOOL = 'call_tool'

# Lista completa, para enums de schema e validação.
ACTION_TYPES = [
    ACTION_SEND_MESSAGE,
    ACTION_NEXT_ROUTE,
    ACTION_REDIRECT,
    ACTION_END_SESSION,
    ACTION_TRANSFER_MENU,
    ACTION_SET_OBSERVATION,
    ACTION_CALL_TOOL,
]

# Ações que encerram o fluxo de execução do turno.
TERMINAL_ACTIONS = frozenset({
    ACTION_NEXT_ROUTE,
    ACTION_REDIRECT,
    ACTION_END_SESSION,
    ACTION_TRANSFER_MENU,
})

# end_action_id default quando o modelo não especifica um, para manter
# compatibilidade com a API do chatbot-router (exige end_action_id).
DEFAULT_END_ACTION_ID = 'voll_ended'


def decode_json_string_maybe(value: Any) -> Any:
    """Decodifica ``value`` quando é uma string carregando um objeto ou
    array JSON. Strings comuns ficam como estão: um escalar não é um
    container serializado.

    Reverte a codificação string-JSON que o normalizador de schema
    aplica a campos ``Any`` (Structured Outputs não tem objeto aberto).
    """
    if not isinstance(value, str):
        return value
    trimmed = value.strip()
    if not trimmed or trimmed[0] not in '{[':
        return value
    try:
        return json.loads(trimmed)
    except (ValueError, TypeError):
        return value


class UserSummary(BaseModel):
    """Subconjunto seguro dos dados do usuário exposto à IA."""

    model_config = ConfigDict(extra='ignore')

    name: str = ''
    auth_level: str = ''


class RouteState(BaseModel):
    """Estado de navegação atual."""

    model_config = ConfigDict(extra='ignore')

    current: str = ''
    previous: Optional[str] = None
    # Últimos nós visitados (mais recente primeiro).
    history: Optional[list[str]] = None


class RouteInfo(BaseModel):
    """Rota disponível para navegação da IA."""

    model_config = ConfigDict(extra='ignore')

    name: str
    description: Optional[str] = None


class MenuInfo(BaseModel):
    """Menu disponível para a ação ``transfer_menu``.

    O seletor é ``name`` (o client Python transfere por nome de menu).
    """

    model_config = ConfigDict(extra='ignore')

    name: str
    # Rota inicial no menu de destino ('start' quando vazio).
    route: Optional[str] = None
    description: Optional[str] = None
    # Configuração interna (mensagem enviada na transferência);
    # não é enviada para a IA.
    message: str = Field(default='', exclude=True)


class EndActionInfo(BaseModel):
    """End action disponível para a ação ``end_session``.

    No chatbot-router, encerrar o atendimento e transferir para um
    atendente humano são a MESMA operação (uma tabulação de
    encerramento com ID próprio) — diferente de ``transfer_menu``, que
    é só bot→bot. O seletor é ``name``, pelo mesmo motivo do
    ``MenuInfo.name``: é o que o modelo consegue escolher com sentido.
    """

    model_config = ConfigDict(extra='ignore')

    name: str
    id: Optional[str] = None
    description: Optional[str] = None


class ToolInfo(BaseModel):
    """Tool disponível para a IA (via ação ``call_tool``)."""

    model_config = ConfigDict(extra='ignore')

    name: str
    description: str = ''
    parameters: Any = None


class ToolCallRequest(BaseModel):
    """Chamada de tool requisitada pelo modelo via protocolo."""

    model_config = ConfigDict(extra='ignore')

    name: str = ''
    arguments: Any = None
    # Campo da observation onde o resultado deve ser guardado.
    result_key: Optional[str] = None

    _decode_arguments = field_validator('arguments', mode='before')(
        decode_json_string_maybe
    )


class ProtocolButton(BaseModel):
    """Botão no payload de ``send_message``."""

    model_config = ConfigDict(extra='ignore')

    title: str = ''
    detail: str = ''


class ProtocolMessage(BaseModel):
    """Mensagem no payload de ``send_message``."""

    model_config = ConfigDict(extra='ignore')

    detail: str = ''
    buttons: Optional[list[ProtocolButton]] = None


class AgentAction(BaseModel):
    """Uma ação que a IA quer que o chatgraph execute."""

    model_config = ConfigDict(extra='ignore')

    type: str = ''
    # Usado por next_route e redirect.
    target_route: Optional[str] = None
    # Usado por send_message.
    message: Optional[ProtocolMessage] = None
    # Usado por end_session.
    end_action_id: Optional[str] = None
    # Usado por transfer_menu (name do MenuInfo).
    menu: Optional[str] = None
    # Usado por set_observation.
    observation: Any = None
    # Usado por call_tool. O resultado é guardado na observation sob
    # ToolCallRequest.result_key e o agente é chamado de novo.
    tool_call: Optional[ToolCallRequest] = None

    _decode_observation = field_validator('observation', mode='before')(
        decode_json_string_maybe
    )

    def is_terminal(self) -> bool:
        """True se a ação encerra o fluxo de execução do turno."""
        return self.type in TERMINAL_ACTIONS


class AgentResult(BaseModel):
    """Saída da IA: texto de resposta + ações ordenadas."""

    model_config = ConfigDict(extra='ignore')

    response: str = ''
    actions: list[AgentAction] = Field(default_factory=list)

    @field_validator('actions', mode='before')
    @classmethod
    def _sanitize_actions(cls, value: Any) -> Any:
        """Remove itens sem ``type`` (alucinação do modelo) e tolera
        ``actions: null``."""
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return [
            item
            for item in value
            if not isinstance(item, dict) or item.get('type')
        ]


class AgentContext(BaseModel):
    """Entrada enviada do chatgraph para a IA: tudo que o modelo
    precisa para decidir roteamento e resposta.

    Serializar com ``model_dump_json(exclude_none=True)`` — campos
    vazios devem ser ``None`` (equivalente ao ``omitempty`` do Go).
    """

    model_config = ConfigDict(extra='ignore')

    message: AgentMessage
    user: UserSummary = Field(default_factory=UserSummary)
    route: RouteState = Field(default_factory=RouteState)
    observation: Any = None
    # Descreve campos e tipos da observation — diz à IA o que coletar.
    observation_schema: Optional[dict] = None
    available_tools: Optional[list[ToolInfo]] = None
    available_routes: list[RouteInfo] = Field(default_factory=list)
    available_menus: Optional[list[MenuInfo]] = None
    available_end_actions: Optional[list[EndActionInfo]] = None
    # Histórico da conversa (user/assistant/tool) prefixado à chamada.
    history: Optional[list[AgentMessage]] = None
    # Motivo pelo qual a ação anterior foi rejeitada, injetado pelo
    # executor para pedir correção no próximo ciclo (re-prompt
    # corretivo). None quando não há correção pendente.
    last_action_error: Optional[str] = None


def tolerant_validate(model_cls: type[BaseModel], raw: Any) -> BaseModel:
    """Valida ``raw`` no modelo com coerção de tipos tolerante.

    Port de ``tolerantUnmarshal``/``coerceValue`` do Go: campo str com
    valor objeto/array vira JSON string; campo numérico com valor str é
    parseado; campo dict/list/modelo com valor string JSON é
    decodificado. O modo lax do pydantic já cobre parte das coerções; o
    fallback cobre o resto.
    """
    if isinstance(raw, str):
        raw = json.loads(raw)
    try:
        return model_cls.model_validate(raw)
    except ValidationError:
        cleaned = _coerce_fields(model_cls, raw)
        return model_cls.model_validate(cleaned)


def _coerce_fields(model_cls: type[BaseModel], raw: Any) -> Any:
    """Coage os campos de primeiro nível de ``raw`` para os tipos
    declarados em ``model_cls`` (análogo campo a campo do coerceValue
    do Go; níveis internos ficam com o modo lax do pydantic)."""
    if not isinstance(raw, dict):
        return raw

    cleaned: dict[str, Any] = {}
    for name, value in raw.items():
        field_info = model_cls.model_fields.get(name)
        if field_info is None:
            cleaned[name] = value
            continue
        cleaned[name] = _coerce_value(value, field_info.annotation)
    return cleaned


def _coerce_value(value: Any, annotation: Any) -> Any:
    """Coage um valor para a anotação alvo, quando há conversão óbvia."""
    if value is None:
        return None

    target = _unwrap_optional(annotation)

    if target is str and not isinstance(value, str):
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return value

    if isinstance(value, str):
        return _coerce_from_str(value, target)

    return value


def _coerce_from_str(value: str, target: Any) -> Any:
    """Coage uma string para o tipo alvo (número ou container JSON)."""
    if target in {int, float}:
        try:
            number = float(value)
        except ValueError:
            return value
        return int(number) if target is int else number

    is_container = (
        target in {dict, list}
        or get_origin(target) in {dict, list}
        or (isinstance(target, type) and issubclass(target, BaseModel))
    )
    if is_container:
        decoded = decode_json_string_maybe(value)
        if decoded is not value:
            return decoded

    return value


def _unwrap_optional(annotation: Any) -> Any:
    """Reduz ``Optional[X]``/``X | None`` para ``X``. Genéricos que não
    são união (list[int], dict[str, Any]) voltam inalterados."""
    origin = get_origin(annotation)
    if origin is not Union and origin is not types.UnionType:
        return annotation
    non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(non_none) == 1:
        return non_none[0]
    return annotation


@lru_cache(maxsize=32)
def build_agent_result_schema(
    menu_names: tuple[str, ...] = (),
    end_action_names: tuple[str, ...] = (),
) -> dict:
    """Gera o JSON Schema de ``AgentResult`` com enum nos tipos de ação,
    garantindo que o LLM só retorne tipos válidos.

    ``menu_names``/``end_action_names`` restringem ``menu`` e
    ``end_action_id`` aos nomes configurados no ``Agent`` — reduz a
    chance do modelo inventar um seletor, mas não elimina: os dois
    campos continuam opcionais (``null`` é sempre uma resposta válida),
    então a resolução em ``executor.py`` continua sendo a única
    garantia. Tuplas vazias (nenhum menu/end action configurado) não
    injetam enum — um enum vazio viraria ``[None]`` e proibiria a ação
    inteira.

    Port de ``buildAgentResultSchema`` do Go, com cache por combinação
    de nomes (``maxsize=1`` faria thrash com mais de um Agent no
    processo). O resultado deve ser tratado como somente leitura.
    """
    schema = AgentResult.model_json_schema()
    action_properties = _schema_node_at(
        schema, 'properties', 'actions', 'items', 'properties'
    )

    if action_properties is None:
        # A travessia depende do shape gerado pelo pydantic; se mudar,
        # o modelo perde as restrições de enum silenciosamente. Avise.
        _logger.warning(
            'build_agent_result_schema: actions[].properties não '
            'encontrado, enums de ações não aplicados'
        )
    else:
        _set_enum(action_properties.get('type'), list(ACTION_TYPES))
        _set_enum(action_properties.get('menu'), list(menu_names))
        _set_enum(
            action_properties.get('end_action_id'), list(end_action_names)
        )

    # A instrução "não pode ser vazio" fica em prosa: minLength não é
    # suportado e required é preenchido pelo normalizador.
    properties = schema.get('properties')
    if isinstance(properties, dict):
        response_field = properties.get('response')
        if isinstance(response_field, dict):
            response_field['description'] = (
                'Response text to send to the user. MUST NOT be empty. '
                'Always include a friendly message in Portuguese.'
            )

    return normalize(schema)


def _set_enum(field: Optional[dict], values: list[str]) -> None:
    """Injeta ``enum`` num campo de schema, quando há valores.

    Campos ``Optional[str]`` (``menu``, ``end_action_id``) chegam do
    pydantic como ``anyOf: [{type: string}, {type: null}]`` — o enum
    precisa ir no branch de string, nunca no nó ``anyOf`` (que exigiria
    o valor casar com enum E anyOf ao mesmo tempo, quebrando o branch
    null). Campos não opcionais (``type``) são um nó plano e recebem o
    enum diretamente, como antes. Nó ausente ou lista vazia deixam o
    campo como está.
    """
    if field is None or not values:
        return
    branches = field.get('anyOf')
    if isinstance(branches, list):
        for branch in branches:
            if isinstance(branch, dict) and branch.get('type') == 'string':
                branch['enum'] = values
        return
    field['enum'] = values


def _schema_node_at(schema: dict, *path: str) -> Optional[dict]:
    """Percorre um JSON Schema ao longo de ``path``, resolvendo $refs
    locais (``#/$defs/Nome``) — o pydantic gera modelos aninhados via
    $defs, diferente da reflection inline do Go."""
    defs = schema.get('$defs', {})
    current: Any = schema
    for key in path:
        current = _resolve_local_ref(current, defs)
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    current = _resolve_local_ref(current, defs)
    return current if isinstance(current, dict) else None


def _resolve_local_ref(node: Any, defs: dict) -> Any:
    """Resolve um nó ``{'$ref': '#/$defs/Nome'}`` para sua definição."""
    while isinstance(node, dict) and '$ref' in node:
        ref = node['$ref']
        prefix = '#/$defs/'
        if not isinstance(ref, str) or not ref.startswith(prefix):
            return node
        resolved = defs.get(ref[len(prefix) :])
        if not isinstance(resolved, dict):
            return node
        node = resolved
    return node
