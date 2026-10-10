"""Testes para o registro de rotas com metadados de IA e o limite de
redirects no pipeline."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatgraph.bot.chatbot_model import (
    MAX_REDIRECT_DEPTH,
    ChatbotApp,
)
from chatgraph.bot.chatbot_router import ChatbotRouter
from chatgraph.bot.route_registry import build_route_entry, route_infos
from chatgraph.types.end_types import RedirectResponse
from chatgraph.types.route import Route
from chatgraph.types.usercall import UserCall


def _make_app(**kwargs) -> ChatbotApp:
    kwargs.setdefault('message_consumer', MagicMock())
    return ChatbotApp(**kwargs)


def _make_usercall(route: str, content: str = 'oi') -> MagicMock:
    usercall = MagicMock()
    usercall.user_id = 'user123'
    usercall.company_id = 'c1'
    usercall.session_id = 1
    usercall.route = route
    usercall.content_message = content
    usercall.logger = MagicMock()
    usercall.set_route = AsyncMock()
    return usercall


@pytest.mark.unit
class TestRouteRegistryScenario:
    def test_build_route_entry_com_metadados(self):
        async def handler(usercall: UserCall):
            return None

        entry = build_route_entry(
            handler,
            auth_level='read',
            description='Order lookup.',
            ai_visible=True,
        )
        assert entry['function'] is handler
        assert entry['params'] == {UserCall: 'usercall'}
        assert entry['auth_level'] == 'read'
        assert entry['description'] == 'Order lookup.'
        assert entry['ai_visible'] is True

    def test_route_infos_extrai_metadados(self):
        routes = {
            'start': {'description': 'Triage.', 'ai_visible': True},
            'legada': {},
        }
        infos = route_infos(routes)
        assert infos == [
            {
                'name': 'start',
                'description': 'Triage.',
                'ai_visible': True,
            },
            {'name': 'legada', 'description': '', 'ai_visible': False},
        ]


@pytest.mark.unit
class TestRouteDecoratorScenario:
    def test_app_route_com_description_e_ai_visible(self):
        app = _make_app()

        @app.route('start', description='Triage.', ai_visible=True)
        async def start(usercall: UserCall):
            return None

        entry = app._ChatbotApp__routes['start']
        assert entry['description'] == 'Triage.'
        assert entry['ai_visible'] is True

    def test_app_route_defaults_retrocompativeis(self):
        app = _make_app()

        @app.route('start')
        async def start(usercall: UserCall):
            return None

        entry = app._ChatbotApp__routes['start']
        assert entry['description'] == ''
        assert entry['ai_visible'] is False
        assert entry['auth_level'] is None

    def test_router_route_e_include_router_propagam(self):
        router = ChatbotRouter()

        @router.route('faq', description='FAQ.', ai_visible=True)
        async def faq(usercall: UserCall):
            return None

        app = _make_app()
        app.include_router(router)
        entry = app._ChatbotApp__routes['faq']
        assert entry['description'] == 'FAQ.'
        assert entry['ai_visible'] is True


@pytest.mark.unit
class TestRouteInfosInjectionScenario:
    @pytest.mark.asyncio
    async def test_handler_recebe_route_com_infos(self):
        app = _make_app(history_store=None)
        captured = {}

        @app.route('start', description='Triage.', ai_visible=True)
        async def start(usercall: UserCall, route: Route):
            captured['route'] = route
            return None

        usercall = _make_usercall('start')
        await app.process_message(usercall)

        route = captured['route']
        assert route.routes == ['start']
        assert route.infos == [
            {
                'name': 'start',
                'description': 'Triage.',
                'ai_visible': True,
            },
        ]

    def test_route_infos_propagado_em_get_next(self):
        infos = [{'name': 'faq', 'description': '', 'ai_visible': True}]
        route = Route('start', ['start', 'faq'], infos=infos)
        assert route.get_next('faq').infos == infos
        assert route.get_previous().infos == infos

    def test_route_sem_infos_retrocompativel(self):
        route = Route('start', ['start'])
        assert route.infos is None


@pytest.mark.unit
class TestRedirectDepthScenario:
    @pytest.mark.asyncio
    async def test_redirect_em_ciclo_e_interrompido(self):
        app = _make_app()
        chamadas = []

        @app.route('pingue')
        async def pingue(usercall: UserCall):
            chamadas.append('pingue')
            return RedirectResponse('pongue')

        @app.route('pongue')
        async def pongue(usercall: UserCall):
            chamadas.append('pongue')
            return RedirectResponse('pingue')

        usercall = _make_usercall('pingue')

        async def set_route(new_route):
            usercall.route = new_route

        usercall.set_route = AsyncMock(side_effect=set_route)
        await app.process_message(usercall)

        # 1 execução inicial + MAX_REDIRECT_DEPTH reentradas.
        assert len(chamadas) == 1 + MAX_REDIRECT_DEPTH

    @pytest.mark.asyncio
    async def test_redirect_normal_continua_funcionando(self):
        app = _make_app()
        chamadas = []

        @app.route('inicio')
        async def inicio(usercall: UserCall):
            chamadas.append('inicio')
            return RedirectResponse('destino')

        @app.route('destino')
        async def destino(usercall: UserCall):
            chamadas.append('destino')
            return None

        usercall = _make_usercall('inicio')

        async def set_route(new_route):
            usercall.route = new_route

        usercall.set_route = AsyncMock(side_effect=set_route)
        await app.process_message(usercall)
        assert chamadas == ['inicio', 'destino']

    @pytest.mark.asyncio
    async def test_message_in_gravado_uma_vez_com_redirect(self):
        registros = []

        class _SpyStore:
            async def record(self, entry):
                registros.append(entry)
                return True

            async def get(self, chat_id, session_id, limit=100):
                return []

            async def clear(self, chat_id, session_id):
                return 0

        app = _make_app(history_store=_SpyStore())

        @app.route('inicio')
        async def inicio(usercall: UserCall):
            return RedirectResponse('destino')

        @app.route('destino')
        async def destino(usercall: UserCall):
            return None

        usercall = _make_usercall('inicio')
        usercall.message.to_dict.return_value = {
            'text_message': {'detail': 'oi'}
        }

        async def set_route(new_route):
            usercall.route = new_route

        usercall.set_route = AsyncMock(side_effect=set_route)
        await app.process_message(usercall)

        message_in = [
            r for r in registros if r.event_type.value == 'message_in'
        ]
        assert len(message_in) == 1
