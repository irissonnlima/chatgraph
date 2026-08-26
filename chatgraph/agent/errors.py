"""Exceções do módulo de agentes de IA."""

from typing import Optional


class AgentError(Exception):
    """Erro genérico do agente de IA."""


class AgentConfigurationError(AgentError):
    """Erro de configuração do agente (parâmetros ou env inválidos)."""


class LLMClientError(AgentError):
    """Erro na comunicação com o provedor de LLM.

    Attributes:
        status_code: Código HTTP da resposta, quando houver.
        retry_after: Segundos sugeridos pelo provedor para novo retry.
        retryable: Se o erro é elegível a retry.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
        self.retryable = retryable


class ToolExecutionError(AgentError):
    """Erro na execução de uma tool do agente."""


class AgentActionError(AgentError):
    """Ação do modelo inválida, recuperável via re-prompt corretivo.

    Attributes:
        feedback: Texto devolvido ao modelo no próximo ciclo (via
            ``AgentContext.last_action_error``) explicando o que
            corrigir — sem ele, o executor só saberia que algo falhou,
            não o que pedir de novo.
    """

    def __init__(self, message: str, *, feedback: str) -> None:
        super().__init__(message)
        self.feedback = feedback
