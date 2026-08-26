"""Testes para Agent.validate_config (checagem opt-in no boot)."""

import httpx
import pytest

from chatgraph.agent.agent import Agent
from chatgraph.agent.errors import AgentConfigurationError
from chatgraph.agent.protocol import EndActionInfo, MenuInfo
from chatgraph.services.router_http_client import RouterHTTPClient


class _FakeLLM:
    async def generate(self, request):  # pragma: no cover
        raise AssertionError('não deve chamar o LLM')


def _agent(**overrides) -> Agent:
    defaults = {'llm_client': _FakeLLM(), 'model': 'fake'}
    defaults.update(overrides)
    return Agent(**defaults)


@pytest.mark.unit
class TestValidateConfigScenario:
    @pytest.mark.asyncio
    async def test_sem_menus_nem_end_actions_nao_toca_o_router(self):
        agent = _agent()
        # router_client=None: se o método tentasse usá-lo, estouraria
        # AttributeError em vez de passar silenciosamente.
        await agent.validate_config(None)

    @pytest.mark.asyncio
    async def test_menu_configurado_existe_passa(
        self, http_client_base_url, respx_mock, sample_menu_data
    ):
        respx_mock.get(f'{http_client_base_url}/menus/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'ok',
                    'data': [sample_menu_data],
                },
            )
        )
        agent = _agent(menus=[MenuInfo(name='suporte')])
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            await agent.validate_config(client)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_menu_configurado_nao_existe_falha(
        self, http_client_base_url, respx_mock, sample_menu_data
    ):
        respx_mock.get(f'{http_client_base_url}/menus/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'ok',
                    'data': [sample_menu_data],
                },
            )
        )
        agent = _agent(menus=[MenuInfo(name='inexistente')])
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            with pytest.raises(AgentConfigurationError, match='inexistente'):
                await agent.validate_config(client)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_end_action_configurada_existe_passa(
        self, http_client_base_url, respx_mock
    ):
        respx_mock.get(f'{http_client_base_url}/end_actions/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'ok',
                    'data': {'id': 'ea1', 'name': 'humano'},
                },
            )
        )
        agent = _agent(end_actions=[EndActionInfo(name='humano')])
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            await agent.validate_config(client)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_end_action_configurada_nao_existe_falha(
        self, http_client_base_url, respx_mock
    ):
        respx_mock.get(f'{http_client_base_url}/end_actions/').mock(
            return_value=httpx.Response(
                200,
                json={'status': False, 'message': 'not found', 'data': None},
            )
        )
        agent = _agent(end_actions=[EndActionInfo(name='humano')])
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            with pytest.raises(AgentConfigurationError, match='humano'):
                await agent.validate_config(client)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_acumula_erros_de_menu_e_end_action(
        self, http_client_base_url, respx_mock, sample_menu_data
    ):
        respx_mock.get(f'{http_client_base_url}/menus/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'ok',
                    'data': [sample_menu_data],
                },
            )
        )
        respx_mock.get(f'{http_client_base_url}/end_actions/').mock(
            return_value=httpx.Response(
                200,
                json={'status': False, 'message': 'not found', 'data': None},
            )
        )
        agent = _agent(
            menus=[MenuInfo(name='inexistente')],
            end_actions=[EndActionInfo(name='humano')],
        )
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            with pytest.raises(AgentConfigurationError) as exc_info:
                await agent.validate_config(client)
        finally:
            await client.close()
        message = str(exc_info.value)
        assert 'inexistente' in message
        assert 'humano' in message
