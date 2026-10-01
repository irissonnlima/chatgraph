from typing import Awaitable, Callable

from ..logger.user_logger import UserLoggerManager
from ..models.actions import EndAction
from ..models.http_responses import RouterResponses
from ..models.message import Message
from ..models.platform_state import PlatformState
from ..models.userstate import ChatID, Menu, UserState
from ..services.router_http_client import RouterHTTPClient

_logger = UserLoggerManager.get_system_logger()

CommandFn = Callable[[str, ChatID, dict, bool], Awaitable[None]]


class RouterStreamClient(RouterHTTPClient):
    """
    Cliente do router que executa as ações do UserCall pelo WebSocket.

    Só as cinco ações viram comandos de stream; arquivos, ID Positiva e
    consultas continuam no HTTP herdado.
    """

    def __init__(
        self,
        base_url: str,
        command: CommandFn,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(base_url, username, password, timeout)
        self._command = command

    async def _run(
        self,
        method: str,
        name: str,
        chat_id: ChatID,
        payload: dict,
        idempotent: bool,
    ) -> RouterResponses:
        _logger.debug(f'[{method}] stream command {name}')
        await self._command(name, chat_id, payload, idempotent)
        return RouterResponses(status=True, message='ok')

    async def send_message(
        self,
        message_data: Message,
        user_state: UserState,
        platform_state: PlatformState = PlatformState(),
    ) -> RouterResponses:
        payload = self.build_send_payload(
            message_data, user_state, platform_state
        )
        return await self._run(
            'send_message', 'send', user_state.chat_id, payload, False
        )

    async def set_session_route(
        self, chat_id: ChatID, route: str
    ) -> RouterResponses:
        return await self._run(
            'set_session_route', 'set_route', chat_id, {'route': route}, True
        )

    async def update_session_observation(
        self, chat_id: ChatID, observation: str
    ) -> RouterResponses:
        return await self._run(
            'update_session_observation',
            'set_observation',
            chat_id,
            {'observation': observation},
            True,
        )

    async def end_chat(
        self, chat_id: ChatID, end_action: EndAction, origin: str
    ) -> RouterResponses:
        payload = {'end_action': end_action.to_dict(), 'origin': origin}
        return await self._run(
            'end_chat', 'end_session', chat_id, payload, False
        )

    async def transfer_to_menu(
        self,
        chat_id: ChatID,
        menu: Menu,
        mensagem: Message,
        route: str = '',
    ) -> RouterResponses:
        payload = {'menu': menu.name, 'message': mensagem.to_dict()}
        if route:
            payload['route'] = route
        return await self._run(
            'transfer_to_menu', 'transfer_to_menu', chat_id, payload, False
        )
