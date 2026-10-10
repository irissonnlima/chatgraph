# ruff: noqa: F822 - os símbolos do agente em __all__ resolvem via
# __getattr__ (PEP 562, import lazy); o ruff não os enxerga.
from .auth.credentials import Credential
from .bot.chatbot_model import ChatbotApp
from .bot.chatbot_router import ChatbotRouter
from .bot.default_guard import default_guard
from .container.container import Container
from .logger import logger, set_level
from .messages.log_publisher import LogPublisher
from .messages.message_consumer import MessageConsumer
from .models.log_envelope import (
    ErrorLogPayload,
    EventType,
    LogEnvelope,
)
from .models.message import Button, File, Message, SendType, TextMessage
from .models.platform_state import PlatformState, VollStateData
from .models.userstate import (
    AuthLevel,
    ChatID,
    Menu,
    User,
    UserData,
    UserIdentity,
    UserInternal,
    UserState,
)
from .stream import (
    CommandTimeoutError,
    ConnectionLostError,
    SessionNotOwnedError,
    StreamClosedError,
    StreamConsumer,
    StreamRejectedError,
    is_session_not_owned,
)
from .types.background_task import BackgroundTask
from .types.end_types import (
    EndChatResponse,
    RedirectResponse,
    TransferToMenu,
)
from .types.route import Route
from .types.usercall import UserCall

# Símbolos do módulo de agentes de IA (extra opcional `agent`).
# Import lazy via PEP 562: quem não instalou pydantic não paga o custo
# nem quebra; o erro amigável vem do guard em chatgraph/agent/__init__.
_AGENT_EXPORTS = {
    'Agent': 'chatgraph.agent.agent',
    'AgentAction': 'chatgraph.agent.protocol',
    'AgentActionError': 'chatgraph.agent.errors',
    'AgentContext': 'chatgraph.agent.protocol',
    'AgentError': 'chatgraph.agent.errors',
    'AgentResult': 'chatgraph.agent.protocol',
    'ContentResult': 'chatgraph.agent.content',
    'EndActionInfo': 'chatgraph.agent.protocol',
    'LLMClientError': 'chatgraph.agent.errors',
    'MenuInfo': 'chatgraph.agent.protocol',
    'OpenRouterClient': 'chatgraph.agent.openrouter',
    'RouteInfo': 'chatgraph.agent.protocol',
    'Tool': 'chatgraph.agent.types',
    'ToolExecutionError': 'chatgraph.agent.errors',
    'ToolInfo': 'chatgraph.agent.protocol',
    'Usage': 'chatgraph.agent.types',
    'execute_single_agent': 'chatgraph.agent.executor',
    'generate_content': 'chatgraph.agent.content',
}


def __getattr__(name: str):
    if name in _AGENT_EXPORTS:
        import importlib  # noqa: PLC0415 - import lazy proposital

        module = importlib.import_module(_AGENT_EXPORTS[name])
        return getattr(module, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


__all__ = [
    'Agent',
    'AgentAction',
    'AgentActionError',
    'AgentContext',
    'AgentError',
    'AgentResult',
    'ContentResult',
    'EndActionInfo',
    'LLMClientError',
    'MenuInfo',
    'OpenRouterClient',
    'RouteInfo',
    'Tool',
    'ToolExecutionError',
    'ToolInfo',
    'Usage',
    'execute_single_agent',
    'generate_content',
    'set_level',
    'ChatbotApp',
    'Credential',
    'UserCall',
    'ChatbotRouter',
    'RedirectResponse',
    'MessageConsumer',
    'StreamConsumer',
    'StreamRejectedError',
    'SessionNotOwnedError',
    'CommandTimeoutError',
    'ConnectionLostError',
    'StreamClosedError',
    'is_session_not_owned',
    'LogPublisher',
    'LogEnvelope',
    'ErrorLogPayload',
    'EventType',
    'Route',
    'EndChatResponse',
    'TransferToMenu',
    'UserState',
    'ChatID',
    'Menu',
    'AuthLevel',
    'User',
    'UserData',
    'UserIdentity',
    'UserInternal',
    'Message',
    'Button',
    'File',
    'TextMessage',
    'SendType',
    'BackgroundTask',
    'Container',
    'logger',
    'default_guard',
    'PlatformState',
    'VollStateData',
]
