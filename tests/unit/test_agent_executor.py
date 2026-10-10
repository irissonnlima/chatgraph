"""Testes para o executor single-agent (loop de tools e execute_result)."""

import json
import logging
from types import SimpleNamespace

import pytest

from chatgraph.agent.agent import Agent
from chatgraph.agent.errors import AgentError, ToolExecutionError
from chatgraph.agent.executor import (
    INVALID_ACTION_FALLBACK,
    execute_single_agent,
    resolve_result_key,
    split_tool_call_action,
    tool_result_already_exists,
)
from chatgraph.agent.protocol import (
    ACTION_CALL_TOOL,
    ACTION_END_SESSION,
    ACTION_NEXT_ROUTE,
    ACTION_REDIRECT,
    ACTION_SEND_MESSAGE,
    ACTION_SET_OBSERVATION,
    ACTION_TRANSFER_MENU,
    AgentAction,
    EndActionInfo,
    MenuInfo,
    ToolCallRequest,
)
from chatgraph.agent.types import AgentResponse, Tool, Usage
from chatgraph.history.entry import HistoryEventType
from chatgraph.history.store import MemoryHistoryStore
from chatgraph.models.message import Message
from chatgraph.models.userstate import AuthLevel
from chatgraph.types.end_types import (
    EndChatResponse,
    RedirectResponse,
    TransferToMenu,
)
from chatgraph.types.route import Route

_ROUTES = ['start', 'atual', 'faq', 'exibe']


class FakeLLMClient:
    def __init__(self, results: list[dict]):
        self.results = list(results)
        self.calls = 0
        self.requests: list = []

    async def generate(self, request):
        self.calls += 1
        self.requests.append(request)
        result = self.results.pop(0)
        return AgentResponse(
            text=json.dumps(result),
            structured_output=result,
            finish_reason='stop',
            usage=Usage(model='fake', total_tokens=10),
        )


class FakeUserCall:
    def __init__(self, *, observation=None, store=None):
        self.route = 'start.atual'
        self.content_message = 'oi'
        self._observation = observation or {}
        self._store = store
        self.user = SimpleNamespace(
            data=SimpleNamespace(name='Ana'),
            identity=SimpleNamespace(auth_level=AuthLevel.READ),
        )
        self.user_id = 'u1'
        self.company_id = 'c1'
        self.session_id = 7
        self.logger = logging.getLogger('test.fake_usercall')
        self.added: list[dict] = []

    @property
    def observation(self):
        return self._observation

    @property
    def history(self):
        return self._store

    async def add_observation(self, observation: dict) -> None:
        self.added.append(observation)
        self._observation.update(observation)


def _route() -> Route:
    return Route('start.atual', _ROUTES)


def _agent(results: list[dict], **overrides) -> Agent:
    defaults = {
        'llm_client': FakeLLMClient(results),
        'model': 'fake',
    }
    defaults.update(overrides)
    return Agent(**defaults)


@pytest.mark.unit
class TestExecuteResultScenario:
    @pytest.mark.asyncio
    async def test_so_response_vira_message(self):
        agent = _agent([{'response': 'ola!', 'actions': []}])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], Message)
        assert returns[0].text_message.detail == 'ola!'

    @pytest.mark.asyncio
    async def test_sem_response_e_sem_actions_permanece_no_no(self):
        agent = _agent([{'response': '', 'actions': []}])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert returns is None

    @pytest.mark.asyncio
    async def test_send_message_com_botoes(self):
        agent = _agent([
            {
                'response': 'escolha',
                'actions': [
                    {
                        'type': ACTION_SEND_MESSAGE,
                        'message': {
                            'detail': 'Escolha uma opção:',
                            'buttons': [
                                {'title': 'Fatura', 'detail': 'fatura'},
                                {'title': 'Pedido', 'detail': ''},
                            ],
                        },
                    },
                ],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        message = returns[0]
        assert message.text_message.detail == 'Escolha uma opção:'
        assert [b.title for b in message.buttons] == ['Fatura', 'Pedido']
        # Botão sem detail usa o próprio título como payload.
        assert message.buttons[1].detail == 'Pedido'

    @pytest.mark.asyncio
    async def test_next_route_com_response_pendente_antes(self):
        agent = _agent([
            {
                'response': 'indo para o faq',
                'actions': [
                    {'type': ACTION_NEXT_ROUTE, 'target_route': 'faq'},
                ],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert isinstance(returns[0], Message)
        assert isinstance(returns[1], Route)
        assert returns[1].current_node == 'faq'
        assert returns[1].current == 'start.atual.faq'

    @pytest.mark.asyncio
    async def test_next_route_desconhecida_vira_none(self):
        agent = _agent([
            {
                'response': 'tentando',
                'actions': [
                    {
                        'type': ACTION_NEXT_ROUTE,
                        'target_route': 'inventada',
                    },
                ],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], Message)

    @pytest.mark.asyncio
    async def test_redirect_e_silencioso(self):
        agent = _agent([
            {
                'response': 'vou te encaminhar',
                'actions': [
                    {'type': ACTION_REDIRECT, 'target_route': 'faq'},
                ],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], RedirectResponse)
        assert returns[0].route == 'faq'

    @pytest.mark.asyncio
    async def test_self_redirect_vira_none(self):
        agent = _agent([
            {
                'response': 'hmm',
                'actions': [
                    {'type': ACTION_REDIRECT, 'target_route': 'atual'},
                ],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], Message)

    @pytest.mark.asyncio
    async def test_end_session_sem_id_usa_default(self):
        agent = _agent([
            {
                'response': 'até logo!',
                'actions': [{'type': ACTION_END_SESSION}],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert isinstance(returns[0], Message)
        assert isinstance(returns[1], EndChatResponse)
        assert returns[1].end_chat_id == 'voll_ended'

    @pytest.mark.asyncio
    async def test_terminal_para_a_execucao_das_acoes_seguintes(self):
        agent = _agent([
            {
                'response': 'indo',
                'actions': [
                    {'type': ACTION_NEXT_ROUTE, 'target_route': 'faq'},
                    {
                        'type': ACTION_SET_OBSERVATION,
                        'observation': {'nao_deve': 'entrar'},
                    },
                ],
            },
        ])
        usercall = FakeUserCall()
        returns = await execute_single_agent(usercall, _route(), agent)
        assert isinstance(returns[-1], Route)
        assert usercall.added == []

    @pytest.mark.asyncio
    async def test_set_observation_executa_inline(self):
        agent = _agent([
            {
                'response': 'anotado',
                'actions': [
                    {
                        'type': ACTION_SET_OBSERVATION,
                        'observation': {'cpf': '123'},
                    },
                ],
            },
        ])
        usercall = FakeUserCall()
        returns = await execute_single_agent(usercall, _route(), agent)
        assert usercall.added == [{'cpf': '123'}]
        assert isinstance(returns[0], Message)

    @pytest.mark.asyncio
    async def test_acao_desconhecida_e_pulada(self):
        agent = _agent([
            {
                'response': 'ok',
                'actions': [{'type': 'acao_inventada'}],
            },
        ])
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], Message)


@pytest.mark.unit
class TestTransferMenuScenario:
    @staticmethod
    def _menus() -> list[MenuInfo]:
        return [
            MenuInfo(
                name='cartoes',
                route='bloqueio',
                description='Cartões.',
                message='Transferindo para cartões...',
            ),
        ]

    @pytest.mark.asyncio
    async def test_transfer_resolvido_por_name(self):
        agent = _agent(
            [
                {
                    'response': 'te transferindo',
                    'actions': [
                        {
                            'type': ACTION_TRANSFER_MENU,
                            'menu': 'cartoes',
                            'target_route': 'bloqueio',
                        },
                    ],
                },
            ],
            menus=self._menus(),
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert isinstance(returns[0], Message)
        transfer = returns[1]
        assert isinstance(transfer, TransferToMenu)
        assert transfer.menu == 'cartoes'
        assert transfer.user_message == 'Transferindo para cartões...'
        assert transfer.route == 'bloqueio'

    @pytest.mark.asyncio
    async def test_transfer_sem_message_usa_response(self):
        menus = [MenuInfo(name='humano', route='start')]
        agent = _agent(
            [
                {
                    'response': 'te passando para um atendente',
                    'actions': [
                        {
                            'type': ACTION_TRANSFER_MENU,
                            'menu': 'humano',
                        },
                    ],
                },
            ],
            menus=menus,
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        transfer = returns[-1]
        assert transfer.user_message == 'te passando para um atendente'
        assert transfer.route == 'start'

    @pytest.mark.asyncio
    async def test_transfer_desconhecido_pede_correcao_e_depois_resolve(
        self,
    ):
        agent = _agent(
            [
                {
                    'response': 'indo',
                    'actions': [
                        {
                            'type': ACTION_SET_OBSERVATION,
                            'observation': {'cpf': '123'},
                        },
                        {
                            'type': ACTION_TRANSFER_MENU,
                            'menu': 'inexistente',
                        },
                    ],
                },
                {
                    'response': 'te transferindo',
                    'actions': [
                        {
                            'type': ACTION_TRANSFER_MENU,
                            'menu': 'cartoes',
                            'target_route': 'bloqueio',
                        },
                    ],
                },
            ],
            menus=self._menus(),
        )
        usercall = FakeUserCall()
        returns = await execute_single_agent(usercall, _route(), agent)

        # A falha na 1ª tentativa não produz side effect algum.
        assert usercall.added == []
        # A 2ª chamada ao LLM recebeu o motivo da rejeição no contexto.
        second_ctx_json = agent.llm_client.requests[1].messages[-1].content
        assert 'inexistente' in second_ctx_json
        assert 'last_action_error' in second_ctx_json
        # E a correção resolveu a transferência.
        transfer = returns[-1]
        assert isinstance(transfer, TransferToMenu)
        assert transfer.menu == 'cartoes'

    @pytest.mark.asyncio
    async def test_transfer_sem_menu_pede_correcao(self):
        agent = _agent(
            [
                {
                    'response': 'indo',
                    'actions': [{'type': ACTION_TRANSFER_MENU}],
                },
                {
                    'response': 'ok',
                    'actions': [
                        {'type': ACTION_NEXT_ROUTE, 'target_route': 'faq'},
                    ],
                },
            ],
            menus=self._menus(),
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert isinstance(returns[-1], Route)
        assert agent.llm_client.calls == 2

    @pytest.mark.asyncio
    async def test_transfer_invalido_duas_vezes_usa_fallback(self):
        agent = _agent(
            [
                {
                    'response': 'indo',
                    'actions': [
                        {'type': ACTION_TRANSFER_MENU, 'menu': 'inexistente'},
                    ],
                },
                {
                    'response': 'ainda tentando',
                    'actions': [
                        {
                            'type': ACTION_TRANSFER_MENU,
                            'menu': 'tambem_inexistente',
                        },
                    ],
                },
            ],
            menus=self._menus(),
        )
        usercall = FakeUserCall()
        returns = await execute_single_agent(usercall, _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], Message)
        assert returns[0].text_message.detail == INVALID_ACTION_FALLBACK
        assert usercall.added == []
        assert agent.llm_client.calls == 2


@pytest.mark.unit
class TestEndActionScenario:
    """end_session cobre tanto encerrar quanto transferir para humano;
    com ``end_actions`` configuradas, end_action_id vira um seletor
    validado (por name, depois por id) em vez de um ID livre."""

    @staticmethod
    def _end_actions() -> list[EndActionInfo]:
        return [
            EndActionInfo(
                name='humano', id='42', description='Atendente humano.'
            ),
            EndActionInfo(name='resolvido'),
        ]

    @pytest.mark.asyncio
    async def test_resolvido_por_name(self):
        agent = _agent(
            [
                {
                    'response': 'te transferindo',
                    'actions': [
                        {
                            'type': ACTION_END_SESSION,
                            'end_action_id': 'humano',
                        },
                    ],
                },
            ],
            end_actions=self._end_actions(),
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        end = returns[-1]
        assert isinstance(end, EndChatResponse)
        assert end.end_chat_id == '42'
        assert end.end_chat_name == 'humano'

    @pytest.mark.asyncio
    async def test_resolvido_por_id(self):
        agent = _agent(
            [
                {
                    'response': 'encerrando',
                    'actions': [
                        {'type': ACTION_END_SESSION, 'end_action_id': '42'},
                    ],
                },
            ],
            end_actions=self._end_actions(),
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        end = returns[-1]
        assert end.end_chat_id == '42'
        assert end.end_chat_name == 'humano'

    @pytest.mark.asyncio
    async def test_seletor_vazio_pede_correcao(self):
        agent = _agent(
            [
                {
                    'response': 'encerrando',
                    'actions': [{'type': ACTION_END_SESSION}],
                },
                {
                    'response': 'encerrado',
                    'actions': [
                        {
                            'type': ACTION_END_SESSION,
                            'end_action_id': 'resolvido',
                        },
                    ],
                },
            ],
            end_actions=self._end_actions(),
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        assert isinstance(returns[-1], EndChatResponse)
        assert returns[-1].end_chat_name == 'resolvido'
        assert agent.llm_client.calls == 2

    @pytest.mark.asyncio
    async def test_seletor_desconhecido_falha_antes_de_side_effects(self):
        agent = _agent(
            [
                {
                    'response': 'indo',
                    'actions': [
                        {
                            'type': ACTION_SET_OBSERVATION,
                            'observation': {'cpf': '123'},
                        },
                        {
                            'type': ACTION_END_SESSION,
                            'end_action_id': 'inexistente',
                        },
                    ],
                },
                {
                    'response': 'ok',
                    'actions': [
                        {
                            'type': ACTION_END_SESSION,
                            'end_action_id': 'resolvido',
                        },
                    ],
                },
            ],
            end_actions=self._end_actions(),
        )
        usercall = FakeUserCall()
        returns = await execute_single_agent(usercall, _route(), agent)
        assert usercall.added == []
        assert isinstance(returns[-1], EndChatResponse)

    @pytest.mark.asyncio
    async def test_sem_end_actions_configuradas_mantem_comportamento_livre(
        self,
    ):
        """Sem end_actions, end_action_id continua um valor livre
        repassado direto (retrocompatibilidade)."""
        agent = _agent(
            [
                {
                    'response': 'até logo!',
                    'actions': [
                        {
                            'type': ACTION_END_SESSION,
                            'end_action_id': 'motivo_qualquer',
                        },
                    ],
                },
            ],
        )
        returns = await execute_single_agent(FakeUserCall(), _route(), agent)
        end = returns[-1]
        assert end.end_chat_id == 'motivo_qualquer'
        assert end.end_chat_name == ''


@pytest.mark.unit
class TestToolLoopScenario:
    @staticmethod
    def _call_tool_result(result_key: str = 'dados') -> dict:
        return {
            'response': 'consultando...',
            'actions': [
                {
                    'type': ACTION_CALL_TOOL,
                    'tool_call': {
                        'name': 'consultar',
                        'arguments': {'cpf': '123'},
                        'result_key': result_key,
                    },
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_tool_loop_feliz(self):
        store = MemoryHistoryStore()
        agent = _agent([
            self._call_tool_result(),
            {
                'response': 'achei seu pedido!',
                'actions': [
                    {'type': ACTION_NEXT_ROUTE, 'target_route': 'exibe'},
                ],
            },
        ])

        @agent.tool()
        async def consultar(cpf: str) -> dict:
            return {'status': 'Entregue', 'cpf': cpf}

        usercall = FakeUserCall(store=store)
        returns = await execute_single_agent(usercall, _route(), agent)

        # Resultado da tool na observation sob result_key.
        assert usercall.observation['dados'] == {
            'status': 'Entregue',
            'cpf': '123',
        }
        # Duas chamadas de LLM (decisão + pós-tool).
        assert agent.llm_client.calls == 2
        # Histórico com o par assistant/tool pareado.
        entries = await store.get('u1:c1', 7)
        events = [e.event_type for e in entries]
        assert HistoryEventType.TOOL_CALL in events
        assert HistoryEventType.TOOL_RESULT in events
        # Turno termina com a navegação decidida pós-tool.
        assert isinstance(returns[-1], Route)
        assert returns[-1].current_node == 'exibe'

    @pytest.mark.asyncio
    async def test_dedup_por_result_key_nao_repete_tool(self):
        agent = _agent([
            {
                'response': 'já tenho os dados',
                'actions': [
                    {
                        'type': ACTION_CALL_TOOL,
                        'tool_call': {
                            'name': 'consultar',
                            'arguments': {},
                            'result_key': 'dados',
                        },
                    },
                    {'type': ACTION_NEXT_ROUTE, 'target_route': 'exibe'},
                ],
            },
        ])
        chamadas = []

        @agent.tool()
        async def consultar() -> str:
            chamadas.append(1)
            return 'x'

        usercall = FakeUserCall(observation={'dados': {'ok': True}})
        returns = await execute_single_agent(usercall, _route(), agent)
        assert chamadas == []
        # As ações restantes (next_route) são executadas.
        assert isinstance(returns[-1], Route)

    @pytest.mark.asyncio
    async def test_exaustao_com_response_envia_texto(self):
        agent = _agent([
            self._call_tool_result(),
            self._call_tool_result(),
        ])

        @agent.tool()
        async def consultar(cpf: str) -> str:
            raise RuntimeError('api fora do ar')

        usercall = FakeUserCall(store=MemoryHistoryStore())
        returns = await execute_single_agent(usercall, _route(), agent)
        assert len(returns) == 1
        assert isinstance(returns[0], Message)
        assert returns[0].text_message.detail == 'consultando...'
        # A falha fica registrada no histórico para o modelo ver.
        entries = await usercall.history.get('u1:c1', 7)
        results = [
            e
            for e in entries
            if e.event_type == HistoryEventType.TOOL_RESULT
        ]
        assert 'api fora do ar' in results[0].metadata['content']

    @pytest.mark.asyncio
    async def test_exaustao_sem_response_levanta_erro(self):
        sem_texto = self._call_tool_result()
        sem_texto['response'] = ''
        agent = _agent([self._call_tool_result(), sem_texto])

        @agent.tool()
        async def consultar(cpf: str) -> str:
            raise RuntimeError('boom')

        with pytest.raises(ToolExecutionError):
            await execute_single_agent(FakeUserCall(), _route(), agent)

    @pytest.mark.asyncio
    async def test_max_tool_loops_excedido(self):
        agent = _agent(
            [
                self._call_tool_result('k1'),
                self._call_tool_result('k2'),
            ],
            max_tool_loops=2,
        )

        @agent.tool()
        async def consultar(cpf: str) -> str:
            return 'ok'

        with pytest.raises(AgentError) as exc_info:
            await execute_single_agent(FakeUserCall(), _route(), agent)
        assert 'max tool call loops' in str(exc_info.value)


@pytest.mark.unit
class TestSplitToolCallScenario:
    def test_terminal_antes_do_call_tool_devolve_lista_intacta(self):
        actions = [
            AgentAction(type=ACTION_NEXT_ROUTE, target_route='faq'),
            AgentAction(
                type=ACTION_CALL_TOOL,
                tool_call=ToolCallRequest(name='x'),
            ),
        ]
        tool_call, remaining = split_tool_call_action(actions)
        assert tool_call is None
        assert remaining == actions

    def test_extrai_primeiro_call_tool_e_adia_o_resto(self):
        actions = [
            AgentAction(type=ACTION_SEND_MESSAGE),
            AgentAction(
                type=ACTION_CALL_TOOL,
                tool_call=ToolCallRequest(name='x'),
            ),
            AgentAction(type=ACTION_NEXT_ROUTE, target_route='faq'),
        ]
        tool_call, remaining = split_tool_call_action(actions)
        assert tool_call.name == 'x'
        assert [a.type for a in remaining] == [ACTION_NEXT_ROUTE]

    def test_call_tool_sem_payload_e_ignorado(self):
        actions = [AgentAction(type=ACTION_CALL_TOOL)]
        tool_call, remaining = split_tool_call_action(actions)
        assert tool_call is None
        assert remaining == actions

    def test_resolve_result_key_default(self):
        assert (
            resolve_result_key(ToolCallRequest(name='consultar'))
            == 'consultar_result'
        )
        assert (
            resolve_result_key(
                ToolCallRequest(name='x', result_key='dados')
            )
            == 'dados'
        )

    def test_tool_result_already_exists(self):
        assert tool_result_already_exists({'k': {'a': 1}}, 'k')
        assert tool_result_already_exists({'k': 'valor'}, 'k')
        assert not tool_result_already_exists({'k': ''}, 'k')
        assert not tool_result_already_exists({'k': {}}, 'k')
        assert not tool_result_already_exists({'k': None}, 'k')
        assert not tool_result_already_exists({}, 'k')
        assert not tool_result_already_exists(None, 'k')
