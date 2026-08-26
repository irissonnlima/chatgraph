"""Módulo de agentes de IA do chatgraph.

Requer o extra opcional ``agent``::

    pip install chatgraph[agent]
"""

try:
    import pydantic  # noqa: F401
except ImportError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        'O módulo chatgraph.agent requer o extra "agent". '
        'Instale com: pip install chatgraph[agent]'
    ) from exc

from .errors import (
    AgentConfigurationError,
    AgentError,
    LLMClientError,
    ToolExecutionError,
)

__all__ = [
    'AgentConfigurationError',
    'AgentError',
    'LLMClientError',
    'ToolExecutionError',
]
