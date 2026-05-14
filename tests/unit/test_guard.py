from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatgraph.bot.chatbot_model import ChatbotApp
from chatgraph.types.end_types import TransferToMenu
from chatgraph.types.usercall import UserCall

_GUARD_NOT_SET = object()


@pytest.mark.unit
class TestChatbotAppGuard:

    @staticmethod
    def _make_app(guard=_GUARD_NOT_SET, default_functions=None):
        consumer = MagicMock()
        kwargs = {'message_consumer': consumer}
        if guard is not _GUARD_NOT_SET:
            kwargs['guard'] = guard
        if default_functions is not None:
            kwargs['default_functions'] = default_functions
        return ChatbotApp(**kwargs)

    @staticmethod
    def _make_usercall(route: str, content: str = 'mensagem_teste'):
        usercall = MagicMock()
        usercall.user_id = 'user123'
        usercall.route = route
        usercall.content_message = content
        usercall.logger = MagicMock()
        return usercall

    @staticmethod
    def _register_route(app, route_name: str, func, auth_level: str | None = None):
        app._ChatbotApp__routes[route_name] = {
            'function': func,
            'params': {UserCall: 'usercall'},
            'return': None,
            'auth_level': auth_level,
        }

    @pytest.mark.asyncio
    async def test_t1_route_no_auth_level_guard_not_called(self):
        guard = AsyncMock(return_value=None)
        app = self._make_app(guard=guard)

        route_func = AsyncMock(return_value=None)
        self._register_route(app, 'test_route', route_func, auth_level=None)

        usercall = self._make_usercall('test_route')

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            await app.process_message(usercall)

        guard.assert_not_called()
        route_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_t2_auth_level_read_guard_returns_none(self):
        guard = AsyncMock(return_value=None)
        app = self._make_app(guard=guard)

        route_func = AsyncMock(return_value=None)
        self._register_route(app, 'test_route', route_func, auth_level='read')

        usercall = self._make_usercall('test_route')

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            await app.process_message(usercall)

        guard.assert_called_once_with(usercall, 'read')
        route_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_t3_auth_level_read_guard_blocks_route(self):
        transfer = TransferToMenu(menu='main', user_message='Acesso negado')
        guard = AsyncMock(return_value=transfer)
        app = self._make_app(guard=guard)

        route_func = AsyncMock(return_value=None)
        self._register_route(app, 'test_route', route_func, auth_level='read')

        usercall = self._make_usercall('test_route')

        process_func_response_mock = AsyncMock()
        with patch.object(
            app,
            '_ChatbotApp__process_func_response',
            new=process_func_response_mock,
        ):
            await app.process_message(usercall)

        guard.assert_called_once_with(usercall, 'read')
        route_func.assert_not_called()
        process_func_response_mock.assert_called_once_with(
            transfer, usercall, route='test_route'
        )

    @pytest.mark.asyncio
    async def test_t4_auth_level_read_no_guard_executes(self):
        app = self._make_app(guard=None)

        route_func = AsyncMock(return_value=None)
        self._register_route(app, 'test_route', route_func, auth_level='read')

        usercall = self._make_usercall('test_route')

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            await app.process_message(usercall)

        route_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_t5_default_function_guard_not_called(self):
        guard = AsyncMock(return_value=None)
        mock_voltar = AsyncMock(return_value=None)
        app = self._make_app(
            guard=guard,
            default_functions={r'^\s*(voltar)\s*$': mock_voltar},
        )

        route_func = AsyncMock(return_value=None)
        self._register_route(app, 'test_route', route_func, auth_level='read')

        usercall = self._make_usercall('test_route', content='voltar')

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            await app.process_message(usercall)

        guard.assert_not_called()
        route_func.assert_not_called()
        mock_voltar.assert_called_once()

    @pytest.mark.asyncio
    async def test_t6_sync_guard_auth_level_read_executes(self):
        guard = MagicMock(return_value=None)
        app = self._make_app(guard=guard)

        route_func = AsyncMock(return_value=None)
        self._register_route(app, 'test_route', route_func, auth_level='read')

        usercall = self._make_usercall('test_route')

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            await app.process_message(usercall)

        guard.assert_called_once_with(usercall, 'read')
        route_func.assert_called_once()
