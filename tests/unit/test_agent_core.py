"""Testes para a classe Agent (tools, generate_protocol, config)."""

import json

import pytest
from pydantic import BaseModel

from chatgraph.agent.agent import Agent
from chatgraph.agent.errors import (
    AgentConfigurationError,
    ToolExecutionError,
)
from chatgraph.agent.protocol import (
    ACTION_NEXT_ROUTE,
    AgentContext,
    RouteInfo,
    RouteState,
    UserSummary,
)
from chatgraph.agent.types import (
    AgentMessage,
    AgentResponse,
    Tool,
    Usage,
)


class FakeLLMClient:
    """LLMClient roteirizado: devolve respostas na ordem da fila."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def _protocol_response(result: dict, **usage_overrides) -> AgentResponse:
    usage = Usage(
        model='fake-model',
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    for key, value in usage_overrides.items():
        setattr(usage, key, value)
    return AgentResponse(
        text=json.dumps(result),
        structured_output=result,
        finish_reason='stop',
        usage=usage,
    )


def _agent(**overrides) -> Agent:
    defaults = {
        'llm_client': FakeLLMClient(),
        'model': 'fake-model',
    }
    defaults.update(overrides)
    return Agent(**defaults)


def _context(**overrides) -> AgentContext:
    defaults = {
        'message': AgentMessage(role='user', content='oi'),
        'user': UserSummary(name='Ana', auth_level='read'),
        'route': RouteState(current='start'),
        'available_routes': [
            RouteInfo(name='start', description='Triage.'),
        ],
    }
    defaults.update(overrides)
    return AgentContext(**defaults)


@pytest.mark.unit
class TestAgentConfigScenario:
    def test_llm_client_e_model_obrigatorios(self):
        with pytest.raises(AgentConfigurationError):
            Agent(llm_client=None, model='x')
        with pytest.raises(AgentConfigurationError):
            Agent(llm_client=FakeLLMClient(), model='')

    def test_defaults_iguais_ao_go(self):
        agent = _agent()
        assert agent.temperature == 0.7
        assert agent.max_tokens == 2048
        assert agent.max_tool_loops == 5
        assert agent.history_limit == 20

    def test_system_prompt_file_lido_no_construtor(self, tmp_path):
        prompt_file = tmp_path / 'personalidade.md'
        prompt_file.write_text('Você é o Zé.', encoding='utf-8')
        agent = _agent(system_prompt_file=str(prompt_file))
        assert agent.system_prompt_text == 'Você é o Zé.'

    def test_system_prompt_file_ausente_falha_cedo(self):
        with pytest.raises(AgentConfigurationError):
            _agent(system_prompt_file='/nao/existe.md')

    def test_load_dotenv_exige_model(self, monkeypatch):
        env_name = 'AGENT_MODEL_TESTE_INEXISTENTE'
        monkeypatch.delenv(env_name, raising=False)
        with pytest.raises(ValueError):
            Agent.load_dotenv(FakeLLMClient(), model_env=env_name)

    def test_load_dotenv_le_overrides(self, monkeypatch):
        monkeypatch.setenv('AGENT_MODEL', 'openai/gpt-4o-mini')
        monkeypatch.setenv('AGENT_TEMPERATURE', '0.3')
        monkeypatch.setenv('AGENT_MAX_TOKENS', '4096')
        monkeypatch.setenv('AGENT_MAX_TOOL_LOOPS', '7')
        monkeypatch.setenv('AGENT_HISTORY_LIMIT', '10')
        agent = Agent.load_dotenv(FakeLLMClient())
        assert agent.model == 'openai/gpt-4o-mini'
        assert agent.temperature == 0.3
        assert agent.max_tokens == 4096
        assert agent.max_tool_loops == 7
        assert agent.history_limit == 10


@pytest.mark.unit
class TestAgentToolsScenario:
    def test_add_tool_normaliza_parameters_dict(self):
        agent = _agent()
        agent.add_tool(
            Tool(
                name='consultar',
                description='x',
                parameters={
                    'type': 'object',
                    'properties': {'cpf': {'type': 'string'}},
                },
            )
        )
        params = agent.get_tools()[0].parameters
        assert params['additionalProperties'] is False
        assert params['required'] == ['cpf']

    def test_add_tool_normaliza_parameters_pydantic(self):
        class Params(BaseModel):
            cpf: str

        agent = _agent()
        agent.add_tool(Tool(name='consultar', parameters=Params))
        params = agent.get_tools()[0].parameters
        assert params['additionalProperties'] is False
        assert 'cpf' in params['properties']

    def test_add_tool_substitui_homonima(self):
        agent = _agent()
        agent.add_tool(Tool(name='x', description='v1'))
        agent.add_tool(Tool(name='x', description='v2'))
        tools = agent.get_tools()
        assert len(tools) == 1
        assert tools[0].description == 'v2'

    def test_decorator_registra_com_nome_da_funcao(self):
        agent = _agent()

        @agent.tool(description='Consulta pedido')
        async def consultar_pedido(cpf: str) -> str:
            return cpf

        assert agent.get_tools()[0].name == 'consultar_pedido'

    @pytest.mark.asyncio
    async def test_call_tool_com_kwargs_e_handler_async(self):
        agent = _agent()

        @agent.tool()
        async def somar(a: int, b: int) -> str:
            return str(a + b)

        result = await agent.call_tool('somar', {'a': 2, 'b': 3})
        assert result == '5'

    @pytest.mark.asyncio
    async def test_call_tool_handler_sync_roda_em_executor(self):
        agent = _agent()

        @agent.tool()
        def eco(texto: str) -> str:
            return texto

        result = await agent.call_tool('eco', '{"texto": "oi"}')
        assert result == 'oi'

    @pytest.mark.asyncio
    async def test_call_tool_dict_resultado_vira_json(self):
        agent = _agent()

        @agent.tool()
        async def dados() -> dict:
            return {'status': 'Entregue'}

        result = await agent.call_tool('dados', None)
        assert json.loads(result) == {'status': 'Entregue'}

    @pytest.mark.asyncio
    async def test_call_tool_inexistente_falha(self):
        agent = _agent()
        with pytest.raises(ToolExecutionError):
            await agent.call_tool('nao_existe', {})

    @pytest.mark.asyncio
    async def test_call_tool_erro_do_handler_vira_tool_error(self):
        agent = _agent()

        @agent.tool()
        async def quebrada() -> str:
            raise RuntimeError('boom')

        with pytest.raises(ToolExecutionError) as exc_info:
            await agent.call_tool('quebrada', None)
        assert 'boom' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_resultado_none_falha(self):
        agent = _agent()

        @agent.tool()
        async def vazia():
            return None

        with pytest.raises(ToolExecutionError):
            await agent.call_tool('vazia', None)


@pytest.mark.unit
class TestGenerateProtocolScenario:
    @pytest.mark.asyncio
    async def test_composicao_das_mensagens(self, tmp_path):
        prompt_file = tmp_path / 'p.md'
        prompt_file.write_text('PERSONALIDADE-ARQUIVO', encoding='utf-8')
        client = FakeLLMClient([
            _protocol_response({'response': 'oi', 'actions': []}),
        ])
        agent = _agent(
            llm_client=client,
            system_prompt='PERSONALIDADE-PROGRAMATICA',
            system_prompt_file=str(prompt_file),
        )
        history = [
            AgentMessage(role='user', content='antes'),
            AgentMessage(role='assistant', content='resposta antiga'),
        ]
        await agent.generate_protocol(_context(history=history))

        request = client.requests[0]
        roles = [m.role for m in request.messages]
        assert roles == [
            'system',
            'system',
            'system',
            'user',
            'assistant',
            'user',
        ]
        assert request.messages[0].content == 'PERSONALIDADE-ARQUIVO'
        assert request.messages[1].content == (
            'PERSONALIDADE-PROGRAMATICA'
        )
        assert 'You are a chatbot router.' in request.messages[2].content
        # Última mensagem: AgentContext serializado (exclude_none).
        payload = json.loads(request.messages[-1].content)
        assert payload['message']['content'] == 'oi'
        assert 'observation' not in payload

    @pytest.mark.asyncio
    async def test_nao_envia_tools_nativas(self):
        client = FakeLLMClient([
            _protocol_response({'response': 'oi', 'actions': []}),
        ])
        agent = _agent(llm_client=client)
        agent.add_tool(Tool(name='x', description='d'))
        await agent.generate_protocol(_context())
        assert client.requests[0].tools == []
        assert client.requests[0].structured_output is not None

    @pytest.mark.asyncio
    async def test_parse_do_resultado(self):
        client = FakeLLMClient([
            _protocol_response({
                'response': 'indo',
                'actions': [
                    {
                        'type': ACTION_NEXT_ROUTE,
                        'target_route': 'faq',
                    },
                ],
            }),
        ])
        agent = _agent(llm_client=client)
        result = await agent.generate_protocol(_context())
        assert result.response == 'indo'
        assert result.actions[0].target_route == 'faq'

    @pytest.mark.asyncio
    async def test_fallback_para_texto_json(self):
        client = FakeLLMClient([
            AgentResponse(
                text='{"response": "oi", "actions": []}',
                structured_output=None,
                finish_reason='stop',
            ),
        ])
        agent = _agent(llm_client=client)
        result = await agent.generate_protocol(_context())
        assert result.response == 'oi'

    @pytest.mark.asyncio
    async def test_sem_saida_retorna_resultado_vazio(self):
        client = FakeLLMClient([
            AgentResponse(
                text='sem json',
                structured_output=None,
                finish_reason='stop',
            ),
        ])
        agent = _agent(llm_client=client)
        result = await agent.generate_protocol(_context())
        assert result.response == ''
        assert result.actions == []

    @pytest.mark.asyncio
    async def test_usage_acumulado_e_observer_notificado(self):
        observed = []
        client = FakeLLMClient([
            _protocol_response({'response': 'oi', 'actions': []}),
        ])
        agent = _agent(
            llm_client=client, usage_observer=observed.append
        )
        turn_usage = Usage()
        await agent.generate_protocol(_context(), usage=turn_usage)
        assert turn_usage.total_tokens == 15
        assert observed[0].total_tokens == 15

    @pytest.mark.asyncio
    async def test_observer_quebrado_nao_derruba_o_turno(self):
        def broken(usage):
            raise RuntimeError('boom')

        client = FakeLLMClient([
            _protocol_response({'response': 'oi', 'actions': []}),
        ])
        agent = _agent(llm_client=client, usage_observer=broken)
        result = await agent.generate_protocol(_context())
        assert result.response == 'oi'
