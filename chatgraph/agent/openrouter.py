"""Cliente OpenRouter (implementação de LLMClient) via httpx.

Port de ``adapters/output/llm/openrouter/client.go`` do chatgraph-go,
com uma melhoria idiomática: a classificação de retry viaja em um erro
tipado (``LLMClientError``) em vez de texto de erro.
"""

import asyncio
import json
import logging
import os
import random
import time
from typing import Optional

import httpx
from dotenv import load_dotenv as _load_dotenv_file

from ..logger.user_logger import UserLoggerManager
from .errors import LLMClientError
from .types import (
    AgentMessage,
    AgentResponse,
    LLMRequest,
    Tool,
    ToolCall,
    Usage,
)

_logger = UserLoggerManager.get_system_logger()

DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'

# Teto para o Retry-After anunciado pelo provedor, para um header
# hostil ou errado não travar um turno de chat indefinidamente.
MAX_RETRY_AFTER = 30.0

# Corte do conteúdo no log DEBUG do raw. Folgado o bastante para caber
# o JSON inteiro do protocolo single-agent no caso comum.
RAW_LOG_MAX_LEN = 4000


async def _sleep(seconds: float) -> None:
    """Indireção de sleep (patchável em testes). Cancelamento do task
    propaga via CancelledError, equivalente ao sleepCtx do Go."""
    await asyncio.sleep(seconds)


class OpenRouterClient:
    """Cliente da API do OpenRouter (compatível com chat completions).

    ``http_client`` é injetável para testes (respx) e reuso de conexões;
    quando injetado, ``aclose()`` não o fecha.
    """

    def __init__(  # noqa: PLR0913
        self,
        api_key: str,
        base_url: str = '',
        *,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not api_key:
            raise ValueError('api_key é obrigatória para o OpenRouterClient.')
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)

    @classmethod
    def load_dotenv(
        cls,
        api_key_env: str = 'OPENROUTER_API_KEY',
        base_url_env: str = 'OPENROUTER_BASE_URL',
    ) -> 'OpenRouterClient':
        """Cria o cliente a partir de variáveis de ambiente (.env)."""
        _load_dotenv_file()
        api_key = os.getenv(api_key_env, '')
        if not api_key:
            raise ValueError(
                f'A variável de ambiente {api_key_env} é obrigatória '
                'para o OpenRouterClient.'
            )
        return cls(api_key=api_key, base_url=os.getenv(base_url_env, ''))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def generate(self, request: LLMRequest) -> AgentResponse:
        """Envia um chat completion e retorna a resposta do agente.

        Retry em erros transitórios (rede, HTTP 429, HTTP 5xx, choices
        vazio) e em finish_reason=error do LLM, com backoff exponencial
        e jitter.
        """
        last_err: Optional[LLMClientError] = None
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                delay = self._backoff_delay(attempt, last_err)
                _logger.warning(
                    f'LLM retry attempt {attempt}/{self.max_retries} '
                    f'| delay={delay:.2f}s | err={last_err}'
                )
                await _sleep(delay)

            started = time.monotonic()
            try:
                response = await self._do_generate(request)
            except LLMClientError as err:
                if err.retryable:
                    last_err = err
                    continue
                raise
            elapsed_ms = (time.monotonic() - started) * 1000

            # finish_reason=error é falha no nível do LLM.
            if response.finish_reason == 'error':
                last_err = LLMClientError(
                    'openrouter: LLM returned finish_reason=error '
                    f'(attempt {attempt + 1})',
                    retryable=True,
                )
                _logger.error(f'LLM call failed: {last_err}')
                continue

            _logger.info(
                f'LLM call completed | model={request.model} '
                f'| duration_ms={elapsed_ms:.0f} '
                f'| prompt_tokens={response.usage.prompt_tokens} '
                f'| completion_tokens='
                f'{response.usage.completion_tokens} '
                f'| total_tokens={response.usage.total_tokens} '
                f'| finish_reason={response.finish_reason}'
            )
            return response

        raise LLMClientError(
            f'openrouter: max retries ({self.max_retries}) exceeded: '
            f'{last_err}'
        )

    def _backoff_delay(
        self, attempt: int, last_err: Optional[LLMClientError]
    ) -> float:
        """Espera antes do retry.

        Um Retry-After anunciado pelo provedor vence a agenda local;
        rate limiting é o caso em que o servidor sabe mais que nós.
        Senão o delay é exponencial (1s, 2s, 4s) mais jitter, para
        sessões concorrentes falhando juntas não retentarem em
        sincronia.
        """
        if last_err is not None and last_err.retry_after:
            return min(last_err.retry_after, MAX_RETRY_AFTER)
        delay = self.retry_delay * (2 ** (attempt - 1))
        return delay + random.uniform(0, delay * 0.25)  # noqa: S311

    async def _do_generate(self, request: LLMRequest) -> AgentResponse:
        """Executa uma única requisição HTTP à API do OpenRouter."""
        payload: dict = {
            'model': request.model,
            'messages': _to_chat_messages(request.messages),
            'temperature': request.temperature,
            'max_tokens': request.max_tokens,
            'stream': False,
        }
        tools = _to_chat_tools(request.tools)
        if tools:
            payload['tools'] = tools
        if request.structured_output is not None:
            payload['response_format'] = {
                'type': 'json_schema',
                'json_schema': {
                    'name': 'response',
                    'schema': request.structured_output,
                },
            }

        try:
            response = await self._http.post(
                f'{self.base_url}/chat/completions',
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}',
                },
            )
        except httpx.TransportError as exc:
            raise LLMClientError(
                f'openrouter: request failed: {exc}', retryable=True
            ) from exc

        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            # Leva o Retry-After do provedor para o loop de retry
            # esperar o pedido em vez de chutar.
            raise LLMClientError(
                f'openrouter: API error (status 429): '
                f'{_truncate(response.text, 500)}',
                status_code=429,
                retry_after=_retry_after_from(response),
                retryable=True,
            )

        if response.status_code != httpx.codes.OK:
            raise LLMClientError(
                f'openrouter: API error '
                f'(status {response.status_code}): '
                f'{_truncate(response.text, 500)}',
                status_code=response.status_code,
                retryable=response.status_code >= 500,  # noqa: PLR2004
            )

        try:
            chat_response = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise LLMClientError(
                f'openrouter: failed to unmarshal response: {exc}'
            ) from exc

        api_error = chat_response.get('error')
        if api_error:
            _logger.error(
                f'OpenRouter API error | '
                f'message={api_error.get("message")} | '
                f'type={api_error.get("type")} | '
                f'code={api_error.get("code")}'
            )

        choices = chat_response.get('choices') or []
        if not choices:
            detail = ''
            if api_error:
                detail = f' (API error: {api_error.get("message")})'
            raise LLMClientError(
                f'openrouter: no choices in response{detail}',
                retryable=True,
            )

        if choices[0].get('finish_reason') == 'error':
            _logger.error(
                'LLM finish_reason=error | '
                f'raw_body={_truncate(response.text, 500)}'
            )

        agent_response = _to_agent_response(
            choices[0], request.structured_output
        )

        # Sem isso, uma ação malformada do modelo (transfer_menu sem
        # menu, target_route inexistente) só aparece como o erro que ela
        # causou lá na frente, sem o JSON que a originou. Fica em DEBUG
        # porque o conteúdo carrega dados da conversa.
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(
                'LLM raw response | '
                f'model={request.model} '
                f'| finish_reason={agent_response.finish_reason} '
                f'| tool_calls={len(agent_response.tool_calls)} '
                f'| content={_truncate(agent_response.text, RAW_LOG_MAX_LEN)}'
            )

        # Contabilidade de tokens. O model vem da resposta quando o
        # provedor o ecoa, já que o roteamento pode substituir o
        # modelo requisitado.
        usage = Usage(model=chat_response.get('model') or request.model)
        usage_block = chat_response.get('usage')
        if isinstance(usage_block, dict):
            usage.prompt_tokens = usage_block.get('prompt_tokens', 0)
            usage.completion_tokens = usage_block.get('completion_tokens', 0)
            usage.total_tokens = usage_block.get('total_tokens', 0)
        agent_response.usage = usage

        return agent_response


def _retry_after_from(response: httpx.Response) -> Optional[float]:
    """Extrai o Retry-After (forma delay-seconds) da resposta 429.
    HTTP-date é ignorado em favor da agenda local de backoff. Valores
    acima de MAX_RETRY_AFTER são clampados no consumo."""
    raw = response.headers.get('Retry-After', '').strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        return None
    if seconds <= 0:
        return None
    if seconds > MAX_RETRY_AFTER:
        _logger.warning(
            f'LLM Retry-After excede o teto, clampando | '
            f'requested={seconds}s | cap={MAX_RETRY_AFTER}s'
        )
        return MAX_RETRY_AFTER
    return seconds


def _to_chat_messages(messages: list[AgentMessage]) -> list[dict]:
    """Converte mensagens do domínio para o formato da API."""
    result = []
    for message in messages:
        chat_message: dict = {'role': message.role}
        if message.content:
            chat_message['content'] = message.content
        if message.tool_calls:
            chat_message['tool_calls'] = [
                {
                    'id': call.id,
                    'type': 'function',
                    'function': {
                        'name': call.name,
                        'arguments': call.arguments,
                    },
                }
                for call in message.tool_calls
            ]
        if message.tool_call_id:
            chat_message['tool_call_id'] = message.tool_call_id
        result.append(chat_message)
    return result


def _to_chat_tools(tools: list[Tool]) -> list[dict]:
    """Converte tools do domínio para o formato da API."""
    return [
        {
            'type': 'function',
            'function': {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters,
            },
        }
        for tool in tools
    ]


def _to_agent_response(
    choice: dict, structured_output: Optional[dict]
) -> AgentResponse:
    """Converte um choice da API em AgentResponse."""
    message = choice.get('message') or {}
    content = message.get('content') or ''
    response = AgentResponse(
        text=content,
        finish_reason=choice.get('finish_reason') or '',
    )

    for call in message.get('tool_calls') or []:
        function = call.get('function') or {}
        response.tool_calls.append(
            ToolCall(
                id=call.get('id', ''),
                name=function.get('name', ''),
                arguments=function.get('arguments', ''),
            )
        )

    if structured_output is not None and content:
        try:
            response.structured_output = json.loads(content)
        except (ValueError, json.JSONDecodeError) as exc:
            # StructuredOutput None faz o chamador cair no parse de
            # texto; sem este log a degradação seria invisível.
            _logger.warning(
                'OpenRouter: structured output requisitado mas o '
                f'content não é JSON válido | err={exc} | '
                f'content={_truncate(content, 200)}'
            )

    return response


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + '...(truncated)'
