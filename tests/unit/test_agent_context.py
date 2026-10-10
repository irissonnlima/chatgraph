"""Testes para build_agent_context e merge_observation."""

import logging
from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from chatgraph.agent.agent import Agent
from chatgraph.agent.context import build_agent_context, merge_observation
from chatgraph.agent.protocol import MenuInfo
from chatgraph.history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)
from chatgraph.history.store import MemoryHistoryStore
from chatgraph.models.userstate import AuthLevel


class _FakeLLM:
    async def generate(self, request):  # pragma: no cover
        raise AssertionError('não deve chamar o LLM')


class _FakeUserCall:
    def __init__(
        self,
        *,
        route: str = 'start',
        content: str = 'oi',
        observation: dict | None = None,
        store=None,
        name: str = 'Ana',
        auth_level: AuthLevel | None = AuthLevel.READ,
    ):
        self.route = route
        self.content_message = content
        self._observation = observation or {}
        self._store = store
        self.user = SimpleNamespace(
            data=SimpleNamespace(name=name),
            identity=SimpleNamespace(auth_level=auth_level),
        )
        self.user_id = 'u1'
        self.company_id = 'c1'
        self.session_id = 7
        self.logger = logging.getLogger('test.fake_usercall')
        self.added: list[dict] = []
        self.raise_on_add: Exception | None = None

    @property
    def observation(self):
        return self._observation

    @property
    def history(self):
        return self._store

    async def add_observation(self, observation: dict) -> None:
        if self.raise_on_add is not None:
            raise self.raise_on_add
        self.added.append(observation)
        self._observation.update(observation)


def _fake_route(infos=None, routes=None):
    return SimpleNamespace(
        current='start', routes=routes or ['start'], infos=infos
    )


def _agent(**overrides) -> Agent:
    defaults = {'llm_client': _FakeLLM(), 'model': 'fake'}
    defaults.update(overrides)
    return Agent(**defaults)


@pytest.mark.unit
class TestBuildAgentContextScenario:
    @pytest.mark.asyncio
    async def test_user_summary_e_message(self):
        usercall = _FakeUserCall(content='quero fatura')
        ctx = await build_agent_context(
            usercall, _fake_route(), _agent()
        )
        assert ctx.message.content == 'quero fatura'
        assert ctx.user.name == 'Ana'
        assert ctx.user.auth_level == 'read'

    @pytest.mark.asyncio
    async def test_route_state_com_dedup(self):
        usercall = _FakeUserCall(route='start.busca.exibe.exibe')
        ctx = await build_agent_context(
            usercall, _fake_route(), _agent()
        )
        assert ctx.route.current == 'exibe'
        assert ctx.route.previous == 'busca'
        assert ctx.route.history == ['exibe', 'busca', 'start']

    @pytest.mark.asyncio
    async def test_observation_vazia_vira_none(self):
        usercall = _FakeUserCall(observation={})
        ctx = await build_agent_context(
            usercall, _fake_route(), _agent()
        )
        assert ctx.observation is None

    @pytest.mark.asyncio
    async def test_observation_schema_default_e_de_modelo(self):
        class Obs(BaseModel):
            cpf: str = ''

        usercall = _FakeUserCall()
        ctx = await build_agent_context(
            usercall, _fake_route(), _agent()
        )
        assert ctx.observation_schema == {'type': 'object'}

        ctx = await build_agent_context(
            usercall, _fake_route(), _agent(observation_model=Obs)
        )
        assert 'cpf' in ctx.observation_schema['properties']
        assert ctx.observation_schema['additionalProperties'] is False

    @pytest.mark.asyncio
    async def test_available_routes_filtra_ai_visible(self):
        infos = [
            {
                'name': 'start',
                'description': 'Triage.',
                'ai_visible': True,
            },
            {'name': 'oculta', 'description': '', 'ai_visible': False},
        ]
        ctx = await build_agent_context(
            _FakeUserCall(), _fake_route(infos=infos), _agent()
        )
        assert [r.name for r in ctx.available_routes] == ['start']
        assert ctx.available_routes[0].description == 'Triage.'

    @pytest.mark.asyncio
    async def test_available_menus_filtra_e_normaliza_route(self):
        agent = _agent(
            menus=[
                MenuInfo(name='cartoes', route=''),
                MenuInfo(name='  '),
            ]
        )
        ctx = await build_agent_context(
            _FakeUserCall(), _fake_route(), agent
        )
        assert len(ctx.available_menus) == 1
        assert ctx.available_menus[0].route == 'start'

    @pytest.mark.asyncio
    async def test_historico_convertido_e_limitado(self):
        store = MemoryHistoryStore()
        for index in range(5):
            await store.record(
                HistoryEntry(
                    idempotency_key=f'k{index}',
                    chat_id='u1:c1',
                    session_id=7,
                    role=HistoryRole.USER,
                    event_type=HistoryEventType.MESSAGE_IN,
                    timestamp=datetime(2026, 1, 1, 12, 0, index),
                    route='start',
                    message={'text_message': {'detail': f'm{index}'}},
                )
            )
        usercall = _FakeUserCall(store=store)
        ctx = await build_agent_context(
            usercall, _fake_route(), _agent(history_limit=2)
        )
        assert [m.content for m in ctx.history] == ['m3', 'm4']

    @pytest.mark.asyncio
    async def test_sem_store_history_none(self):
        ctx = await build_agent_context(
            _FakeUserCall(store=None), _fake_route(), _agent()
        )
        assert ctx.history is None


@pytest.mark.unit
class TestMergeObservationScenario:
    @pytest.mark.asyncio
    async def test_merge_filtra_valores_vazios(self):
        usercall = _FakeUserCall(observation={'antigo': 'x'})
        await merge_observation(
            usercall,
            {
                'cpf': '123',
                'vazio': '',
                'nulo': None,
                'literal': 'null',
            },
        )
        assert usercall.added == [{'cpf': '123'}]
        assert usercall.observation == {'antigo': 'x', 'cpf': '123'}

    @pytest.mark.asyncio
    async def test_merge_aceita_string_json(self):
        usercall = _FakeUserCall()
        await merge_observation(usercall, '{"pedido": "42"}')
        assert usercall.added == [{'pedido': '42'}]

    @pytest.mark.asyncio
    async def test_merge_aceita_modelo_pydantic(self):
        class Obs(BaseModel):
            cpf: str = '123'

        usercall = _FakeUserCall()
        await merge_observation(usercall, Obs())
        assert usercall.added == [{'cpf': '123'}]

    @pytest.mark.asyncio
    async def test_merge_ignora_nao_dict(self):
        usercall = _FakeUserCall()
        await merge_observation(usercall, 'texto solto')
        await merge_observation(usercall, None)
        await merge_observation(usercall, {'so_vazio': ''})
        assert usercall.added == []

    @pytest.mark.asyncio
    async def test_merge_filtra_aninhado(self):
        usercall = _FakeUserCall()
        await merge_observation(
            usercall,
            {'dados': {'cpf': '1', 'vazio': 'null'}, 'oco': {'x': ''}},
        )
        assert usercall.added == [{'dados': {'cpf': '1'}}]

    @pytest.mark.asyncio
    async def test_falha_do_add_observation_nao_propaga(self):
        usercall = _FakeUserCall()
        usercall.raise_on_add = ValueError('api fora')
        await merge_observation(usercall, {'cpf': '123'})
        assert usercall.added == []
