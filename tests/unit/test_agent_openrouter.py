"""Testes para o cliente OpenRouter (retry, structured output, usage)."""

import logging

import httpx
import pytest
import respx

import chatgraph.agent.openrouter as openrouter_module
from chatgraph.agent.errors import LLMClientError
from chatgraph.agent.openrouter import MAX_RETRY_AFTER, OpenRouterClient
from chatgraph.agent.types import AgentMessage, LLMRequest, Tool, ToolCall

_URL = 'https://openrouter.ai/api/v1/chat/completions'


def _request(**overrides) -> LLMRequest:
    defaults = {
        'model': 'openai/gpt-4o-mini',
        'messages': [AgentMessage(role='user', content='oi')],
    }
    defaults.update(overrides)
    return LLMRequest(**defaults)


def _ok_body(
    content: str = 'ola!',
    model: str = 'openai/gpt-4o-mini',
    finish_reason: str = 'stop',
    **extra,
) -> dict:
    body = {
        'id': 'gen-1',
        'model': model,
        'choices': [
            {
                'message': {'role': 'assistant', 'content': content},
                'finish_reason': finish_reason,
            }
        ],
        'usage': {
            'prompt_tokens': 10,
            'completion_tokens': 5,
            'total_tokens': 15,
        },
    }
    body.update(extra)
    return body


@pytest.fixture
def client():
    return OpenRouterClient(api_key='sk-test', retry_delay=0.01)


@pytest.fixture
def sleep_spy(monkeypatch):
    """Captura os delays de retry sem dormir de verdade."""
    delays: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(openrouter_module, '_sleep', fake_sleep)
    return delays


@pytest.mark.unit
class TestOpenRouterRawResponseLog:
    """O JSON cru do modelo só sai em DEBUG (carrega dados da conversa),
    mas é a única forma de diagnosticar uma ação malformada."""

    @pytest.mark.asyncio
    async def test_loga_conteudo_bruto_em_debug(
        self, respx_mock, client, caplog
    ):
        content = '{"response":"oi","actions":[{"type":"transfer_menu"}]}'
        respx.post(_URL).mock(
            return_value=httpx.Response(200, json=_ok_body(content=content))
        )
        with caplog.at_level(logging.DEBUG, logger='chatgraph.system'):
            await client.generate(_request())

        assert any(
            'LLM raw response' in record.message and content in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_nao_loga_conteudo_bruto_em_info(
        self, respx_mock, client, caplog
    ):
        respx.post(_URL).mock(
            return_value=httpx.Response(
                200, json=_ok_body(content='dado sensivel')
            )
        )
        with caplog.at_level(logging.INFO, logger='chatgraph.system'):
            await client.generate(_request())

        assert not any(
            'LLM raw response' in record.message for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_trunca_conteudo_longo(self, respx_mock, client, caplog):
        content = 'x' * (openrouter_module.RAW_LOG_MAX_LEN + 100)
        respx.post(_URL).mock(
            return_value=httpx.Response(200, json=_ok_body(content=content))
        )
        with caplog.at_level(logging.DEBUG, logger='chatgraph.system'):
            await client.generate(_request())

        raw = next(
            record.message
            for record in caplog.records
            if 'LLM raw response' in record.message
        )
        logged_content = raw.split('| content=', 1)[1]
        assert logged_content.endswith('...(truncated)')
        assert len(logged_content) < len(content)


@pytest.mark.unit
class TestOpenRouterSuccessScenario:
    @pytest.mark.asyncio
    async def test_sucesso_simples(self, respx_mock, client):
        route = respx.post(_URL).mock(
            return_value=httpx.Response(200, json=_ok_body())
        )
        response = await client.generate(_request())
        assert response.text == 'ola!'
        assert response.finish_reason == 'stop'
        assert response.usage.total_tokens == 15
        payload = route.calls[0].request.read()
        assert b'"stream": false' in payload or b'"stream":false' in payload

    @pytest.mark.asyncio
    async def test_structured_output_no_payload_e_na_resposta(
        self, respx_mock, client
    ):
        schema = {'type': 'object', 'properties': {}}
        route = respx.post(_URL).mock(
            return_value=httpx.Response(
                200, json=_ok_body(content='{"response": "oi"}')
            )
        )
        response = await client.generate(
            _request(structured_output=schema)
        )
        assert response.structured_output == {'response': 'oi'}

        import json as _json

        payload = _json.loads(route.calls[0].request.read())
        assert payload['response_format'] == {
            'type': 'json_schema',
            'json_schema': {'name': 'response', 'schema': schema},
        }
        assert 'strict' not in payload['response_format']['json_schema']

    @pytest.mark.asyncio
    async def test_structured_output_invalido_degrada_para_none(
        self, respx_mock, client
    ):
        respx.post(_URL).mock(
            return_value=httpx.Response(
                200, json=_ok_body(content='nao é json')
            )
        )
        response = await client.generate(
            _request(structured_output={'type': 'object'})
        )
        assert response.structured_output is None
        assert response.text == 'nao é json'

    @pytest.mark.asyncio
    async def test_model_ecoado_prevalece_no_usage(
        self, respx_mock, client
    ):
        respx.post(_URL).mock(
            return_value=httpx.Response(
                200, json=_ok_body(model='openai/gpt-4o-mini-2024')
            )
        )
        response = await client.generate(_request())
        assert response.usage.model == 'openai/gpt-4o-mini-2024'

    @pytest.mark.asyncio
    async def test_tool_calls_da_resposta_sao_mapeados(
        self, respx_mock, client
    ):
        body = _ok_body(content='')
        body['choices'][0]['message']['tool_calls'] = [
            {
                'id': 'call_1',
                'type': 'function',
                'function': {'name': 'consultar', 'arguments': '{}'},
            }
        ]
        respx.post(_URL).mock(return_value=httpx.Response(200, json=body))
        response = await client.generate(_request())
        assert response.tool_calls[0].name == 'consultar'

    @pytest.mark.asyncio
    async def test_mensagens_com_tool_calls_no_payload(
        self, respx_mock, client
    ):
        import json as _json

        messages = [
            AgentMessage(
                role='assistant',
                tool_calls=[
                    ToolCall(id='call_1', name='x', arguments='{}'),
                ],
            ),
            AgentMessage(role='tool', content='ok', tool_call_id='call_1'),
        ]
        route = respx.post(_URL).mock(
            return_value=httpx.Response(200, json=_ok_body())
        )
        await client.generate(_request(messages=messages))
        payload = _json.loads(route.calls[0].request.read())
        assistant, tool = payload['messages']
        assert assistant['tool_calls'][0]['function']['name'] == 'x'
        assert 'content' not in assistant
        assert tool['tool_call_id'] == 'call_1'

    @pytest.mark.asyncio
    async def test_tools_nativas_no_payload(self, respx_mock, client):
        import json as _json

        tools = [
            Tool(
                name='consultar',
                description='Consulta.',
                parameters={'type': 'object', 'properties': {}},
            )
        ]
        route = respx.post(_URL).mock(
            return_value=httpx.Response(200, json=_ok_body())
        )
        await client.generate(_request(tools=tools))
        payload = _json.loads(route.calls[0].request.read())
        assert payload['tools'][0]['function']['name'] == 'consultar'


@pytest.mark.unit
class TestOpenRouterRetryScenario:
    @pytest.mark.asyncio
    async def test_5xx_retry_e_sucesso(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            side_effect=[
                httpx.Response(500, text='oops'),
                httpx.Response(200, json=_ok_body()),
            ]
        )
        response = await client.generate(_request())
        assert response.text == 'ola!'
        assert len(sleep_spy) == 1

    @pytest.mark.asyncio
    async def test_429_honra_retry_after(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            side_effect=[
                httpx.Response(
                    429, text='slow down', headers={'Retry-After': '7'}
                ),
                httpx.Response(200, json=_ok_body()),
            ]
        )
        await client.generate(_request())
        assert sleep_spy == [7.0]

    @pytest.mark.asyncio
    async def test_retry_after_clampado_no_teto(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            side_effect=[
                httpx.Response(
                    429, text='x', headers={'Retry-After': '999'}
                ),
                httpx.Response(200, json=_ok_body()),
            ]
        )
        await client.generate(_request())
        assert sleep_spy == [MAX_RETRY_AFTER]

    @pytest.mark.asyncio
    async def test_no_choices_e_retryable(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            side_effect=[
                httpx.Response(200, json={'choices': []}),
                httpx.Response(200, json=_ok_body()),
            ]
        )
        response = await client.generate(_request())
        assert response.text == 'ola!'

    @pytest.mark.asyncio
    async def test_finish_reason_error_e_retryable(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            side_effect=[
                httpx.Response(
                    200, json=_ok_body(finish_reason='error')
                ),
                httpx.Response(200, json=_ok_body()),
            ]
        )
        response = await client.generate(_request())
        assert response.finish_reason == 'stop'

    @pytest.mark.asyncio
    async def test_erro_de_rede_e_retryable(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            side_effect=[
                httpx.ConnectError('connection refused'),
                httpx.Response(200, json=_ok_body()),
            ]
        )
        response = await client.generate(_request())
        assert response.text == 'ola!'

    @pytest.mark.asyncio
    async def test_400_falha_direto_sem_retry(
        self, respx_mock, client, sleep_spy
    ):
        route = respx.post(_URL).mock(
            return_value=httpx.Response(400, text='bad request')
        )
        with pytest.raises(LLMClientError) as exc_info:
            await client.generate(_request())
        assert exc_info.value.status_code == 400
        assert not exc_info.value.retryable
        assert route.call_count == 1
        assert sleep_spy == []

    @pytest.mark.asyncio
    async def test_max_retries_excedido(
        self, respx_mock, client, sleep_spy
    ):
        route = respx.post(_URL).mock(
            return_value=httpx.Response(500, text='oops')
        )
        with pytest.raises(LLMClientError) as exc_info:
            await client.generate(_request())
        assert 'max retries (3) exceeded' in str(exc_info.value)
        assert route.call_count == 4  # 1 tentativa + 3 retries

    @pytest.mark.asyncio
    async def test_backoff_exponencial_com_jitter(
        self, respx_mock, client, sleep_spy
    ):
        respx.post(_URL).mock(
            return_value=httpx.Response(500, text='oops')
        )
        with pytest.raises(LLMClientError):
            await client.generate(_request())
        base = client.retry_delay
        assert len(sleep_spy) == 3
        for attempt, delay in enumerate(sleep_spy, start=1):
            expected = base * (2 ** (attempt - 1))
            assert expected <= delay <= expected * 1.25


@pytest.mark.unit
class TestOpenRouterConfigScenario:
    def test_api_key_obrigatoria(self):
        with pytest.raises(ValueError):
            OpenRouterClient(api_key='')

    def test_load_dotenv_exige_api_key(self, monkeypatch):
        # Nome customizado para isolar do .env real do repositório.
        env_name = 'OPENROUTER_API_KEY_TESTE_INEXISTENTE'
        monkeypatch.delenv(env_name, raising=False)
        with pytest.raises(ValueError):
            OpenRouterClient.load_dotenv(api_key_env=env_name)

    def test_load_dotenv_com_base_url(self, monkeypatch):
        monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-x')
        monkeypatch.setenv(
            'OPENROUTER_BASE_URL', 'https://proxy.local/v1/'
        )
        client = OpenRouterClient.load_dotenv()
        assert client.base_url == 'https://proxy.local/v1'

    def test_base_url_default(self):
        client = OpenRouterClient(api_key='sk-x')
        assert client.base_url == 'https://openrouter.ai/api/v1'
