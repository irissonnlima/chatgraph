"""Testes para generate_content (análise de conteúdo desacoplada do
turno de chat: sem UserCall, sem Route, sem AgentContext)."""

import json

import pytest
from pydantic import BaseModel

from chatgraph.agent.content import ContentResult, generate_content
from chatgraph.agent.types import AgentMessage, AgentResponse, Usage


class FakeLLMClient:
    def __init__(self, response: AgentResponse):
        self.response = response
        self.requests: list = []

    async def generate(self, request):
        self.requests.append(request)
        return self.response


def _response(**overrides) -> AgentResponse:
    defaults = {
        'text': 'ola',
        'finish_reason': 'stop',
        'usage': Usage(
            model='fake', prompt_tokens=1, completion_tokens=2, total_tokens=3
        ),
    }
    defaults.update(overrides)
    return AgentResponse(**defaults)


class Insight(BaseModel):
    resumo: str
    anomalias: list[str] = []


@pytest.mark.unit
class TestGenerateContentMessagesScenario:
    @pytest.mark.asyncio
    async def test_mensagens_montadas_na_ordem_certa(self):
        client = FakeLLMClient(_response())
        history = [AgentMessage(role='assistant', content='oi de novo')]
        await generate_content(
            client,
            'fake-model',
            'dados aqui',
            system_prompt='Você é um analista.',
            history=history,
        )
        messages = client.requests[0].messages
        assert [m.role for m in messages] == ['system', 'assistant', 'user']
        assert messages[0].content == 'Você é um analista.'
        assert messages[1].content == 'oi de novo'
        assert messages[2].content == 'dados aqui'

    @pytest.mark.asyncio
    async def test_sem_system_prompt_nem_history(self):
        client = FakeLLMClient(_response())
        await generate_content(client, 'fake-model', 'dados')
        messages = client.requests[0].messages
        assert [m.role for m in messages] == ['user']

    @pytest.mark.asyncio
    async def test_history_vazia_nao_quebra(self):
        client = FakeLLMClient(_response())
        await generate_content(client, 'fake-model', 'dados', history=[])
        messages = client.requests[0].messages
        assert [m.role for m in messages] == ['user']


@pytest.mark.unit
class TestGenerateContentResponseModelScenario:
    @pytest.mark.asyncio
    async def test_sem_response_model_data_e_none(self):
        client = FakeLLMClient(_response(text='texto livre'))
        result = await generate_content(client, 'fake-model', 'dados')
        assert isinstance(result, ContentResult)
        assert result.text == 'texto livre'
        assert result.data is None

    @pytest.mark.asyncio
    async def test_com_response_model_e_structured_output_populado(self):
        parsed = {'resumo': 'tudo ok', 'anomalias': ['x']}
        client = FakeLLMClient(
            _response(text=json.dumps(parsed), structured_output=parsed)
        )
        result = await generate_content(
            client, 'fake-model', 'dados', response_model=Insight
        )
        assert isinstance(result.data, Insight)
        assert result.data.resumo == 'tudo ok'
        assert result.data.anomalias == ['x']

    @pytest.mark.asyncio
    async def test_response_model_com_fallback_de_texto_json(self):
        parsed = {'resumo': 'via fallback', 'anomalias': []}
        client = FakeLLMClient(
            _response(text=json.dumps(parsed), structured_output=None)
        )
        result = await generate_content(
            client, 'fake-model', 'dados', response_model=Insight
        )
        assert result.data.resumo == 'via fallback'

    @pytest.mark.asyncio
    async def test_response_model_com_texto_invalido_data_none(self):
        client = FakeLLMClient(
            _response(text='não é json', structured_output=None)
        )
        result = await generate_content(
            client, 'fake-model', 'dados', response_model=Insight
        )
        assert result.data is None

    @pytest.mark.asyncio
    async def test_schema_enviado_e_raiz_fechada(self):
        client = FakeLLMClient(
            _response(structured_output={'resumo': 'x', 'anomalias': []})
        )
        await generate_content(
            client, 'fake-model', 'dados', response_model=Insight
        )
        schema = client.requests[0].structured_output
        assert schema['type'] == 'object'
        assert schema['additionalProperties'] is False
        assert set(schema['required']) == {'resumo', 'anomalias'}

    @pytest.mark.asyncio
    async def test_sem_response_model_structured_output_e_none(self):
        client = FakeLLMClient(_response())
        await generate_content(client, 'fake-model', 'dados')
        assert client.requests[0].structured_output is None


@pytest.mark.unit
class TestGenerateContentUsageScenario:
    @pytest.mark.asyncio
    async def test_usage_observer_chamado(self):
        usage = Usage(model='fake', total_tokens=42)
        client = FakeLLMClient(_response(usage=usage))
        seen: list[Usage] = []
        await generate_content(
            client, 'fake-model', 'dados', usage_observer=seen.append
        )
        assert seen == [usage]

    @pytest.mark.asyncio
    async def test_usage_observer_com_excecao_nao_propaga(self):
        client = FakeLLMClient(_response())

        def falha(usage):
            raise RuntimeError('boom')

        result = await generate_content(
            client, 'fake-model', 'dados', usage_observer=falha
        )
        assert result.text == 'ola'

    @pytest.mark.asyncio
    async def test_finish_reason_e_usage_propagados(self):
        usage = Usage(model='fake', total_tokens=7)
        client = FakeLLMClient(_response(finish_reason='length', usage=usage))
        result = await generate_content(client, 'fake-model', 'dados')
        assert result.finish_reason == 'length'
        assert result.usage == usage
