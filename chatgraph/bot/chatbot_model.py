import asyncio
import inspect
import json
import re
from datetime import datetime
from functools import wraps
from typing import Callable, Optional

from ..error.chatbot_error import ChatbotMessageError
from ..history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)
from ..history.keys import generate_idempotency_key
from ..history.store import HistoryStore
from ..logger.user_logger import UserLoggerManager
from ..messages.message_consumer import MessageConsumer
from ..models.message import File, Message, MessageTypes
from ..types.background_task import BackgroundTask
from ..types.end_types import (
    EndChatResponse,
    RedirectResponse,
    TransferToMenu,
)
from ..types.route import Route
from ..types.usercall import UserCall
from .chatbot_router import ChatbotRouter
from .default_functions import voltar
from .default_guard import default_guard as _default_guard

_logger = UserLoggerManager.get_system_logger()

DEFAULT_FUNCTION: dict[str, Callable] = {
    r'^\s*(voltar)\s*$': voltar,
}


class ChatbotApp:
    """
    Classe principal para a aplicação do chatbot, gerencia as rotas e a lógica de processamento de mensagens.
    """

    def __init__(
        self,
        message_consumer: Optional[MessageConsumer] = None,
        default_functions: dict[str, Callable] = DEFAULT_FUNCTION,
        log_level: int | str | None = None,
        guard: Callable = _default_guard,
        history_store: Optional[HistoryStore] = None,
        log_publisher: Optional['LogPublisher'] = None,
    ):
        """
        Inicializa a classe ChatbotApp com um estado de usuário e um consumidor de mensagens.

        Args:
            message_consumer (MessageConsumer): O consumidor de mensagens que lida com a entrada de mensagens no sistema.
            default_functions (dict[str, callable]): Dicionário de funções padrão que podem ser usadas antes das rotas.
        """
        if log_level is not None:
            UserLoggerManager.set_level(log_level)

        if not message_consumer:
            message_consumer = MessageConsumer.load_dotenv()

        self.default_functions = default_functions
        self.__message_consumer = message_consumer
        self.__routes = {}
        self.__guard = guard
        self.__history_store = history_store
        self.__message_consumer.set_history_store(history_store)

        if log_publisher is None:
            from ..messages.log_publisher import LogPublisher

            log_publisher = LogPublisher.load_dotenv()
        if log_publisher is None:
            _logger.warning(
                'LogPublisher não configurado. Defina LOG_RABBIT_QUEUE '
                'no .env para ativar o envio de logs de erro para '
                'o RabbitMQ.'
            )
        self.__log_publisher = log_publisher
        self.__message_consumer.set_log_publisher(self.__log_publisher)

    def include_router(self, router: ChatbotRouter) -> None:
        """
        Inclui um roteador de chatbot com um prefixo nas rotas da aplicação.

        Args:
            router (ChatbotRouter): O roteador contendo as rotas a serem adicionadas.
        """
        self.__routes.update(router.routes)

    def route(
        self, route_name: str, auth_level: str | None = None
    ) -> Callable:
        """
        Decorador para adicionar uma função como uma rota na aplicação do chatbot.

        Args:
            route_name (str): O nome da rota para a qual a função deve ser associada.

        Returns:
            function: O decorador que adiciona a função à rota especificada.
        """
        route_name = route_name.strip().lower()

        def decorator(func):
            params = {}
            signature = inspect.signature(func)
            output_param = signature.return_annotation

            for name, param in signature.parameters.items():
                param_type = (
                    param.annotation
                    if param.annotation != inspect.Parameter.empty
                    else 'Any'
                )
                params[param_type] = name
                _logger.debug(f'Parameter: {name}, Type: {param_type}')

            self.__routes[route_name] = {
                'function': func,
                'params': params,
                'return': output_param,
                'auth_level': auth_level,
            }

            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def start(self):
        """
        Inicia o consumo de mensagens pelo chatbot,
        processando cada mensagem recebida.
        """
        self.__message_consumer.reprer()
        asyncio.run(
            self.__message_consumer.start_consume(self.process_message)
        )

    async def __record_message_in(
        self, usercall: UserCall, route: str
    ) -> None:
        """Registra entrada de histórico MESSAGE_IN com a mensagem
        completa (fire-and-forget: nunca propaga exceções)."""
        if self.__history_store is None:
            return
        try:
            chat_id = f'{usercall.user_id}:{usercall.company_id}'
            message_dict = usercall.message.to_dict()
            message_payload = (
                json.dumps(message_dict, sort_keys=True)
                if message_dict
                else ''
            )
            key = generate_idempotency_key(
                chat_id,
                usercall.session_id,
                HistoryRole.USER.value,
                HistoryEventType.MESSAGE_IN.value,
                route,
                message_payload,
            )
            entry = HistoryEntry(
                idempotency_key=key,
                chat_id=chat_id,
                session_id=usercall.session_id,
                role=HistoryRole.USER,
                event_type=HistoryEventType.MESSAGE_IN,
                timestamp=datetime.now(),
                route=route,
                message=message_dict,
            )
            await self.__history_store.record(entry)
        except BaseException as e:
            _logger.warning(f'Erro ao registrar histórico de entrada: {e}')

    async def process_message(self, usercall: UserCall) -> None:
        """
        Processa uma mensagem recebida, identificando a rota correspondente
        e executando a função associada.

        Args:
            usercall (UserCall): A mensagem a ser processada.

        Raises:
            ChatbotMessageError: Se nenhuma rota for encontrada para
            o menu atual do usuário.
        """
        user_id = usercall.user_id
        route = usercall.route.lower()
        route_handler = route.split('.')[-1]

        await self.__record_message_in(usercall, route)

        try:
            matchDefault = False

            for regex, func in self.default_functions.items():
                if re.match(regex, usercall.content_message):
                    matchDefault = True
                    usercall.logger.debug(
                        f'Função padrão encontrada: {func.__name__} para a rota {route}'
                    )
                    handler = {
                        'function': func,
                        'params': {UserCall: 'usercall', Route: 'route'},
                    }
                    break

            if not matchDefault:
                handler = self.__routes.get(route_handler, None)

            if not handler:
                raise ChatbotMessageError(
                    user_id, f'Rota não encontrada para {route}!'
                )

            auth_level = handler.get('auth_level')
            if not matchDefault and auth_level and self.__guard:
                if asyncio.iscoroutinefunction(self.__guard):
                    guard_response = await self.__guard(usercall, auth_level)
                else:
                    loop = asyncio.get_running_loop()
                    guard_response = await loop.run_in_executor(
                        None, lambda: self.__guard(usercall, auth_level)
                    )

                if guard_response is not None:
                    await self.__process_func_response(
                        guard_response, usercall, route=route
                    )
                    return

            func = handler['function']
            usercall_name = handler['params'].get(UserCall, None)
            route_state_name = handler['params'].get(Route, None)

            kwargs = {}
            if usercall_name:
                kwargs[usercall_name] = usercall
            if route_state_name:
                kwargs[route_state_name] = Route(
                    route, list(self.__routes.keys())
                )

            if asyncio.iscoroutinefunction(func):
                usercall_response = await func(**kwargs)
            else:
                loop = asyncio.get_running_loop()
                usercall_response = await loop.run_in_executor(
                    None, lambda: func(**kwargs)
                )

            if matchDefault:
                usercall.content_message = ''

            if isinstance(usercall_response, (list, tuple)):
                for response in usercall_response:
                    await self.__process_func_response(
                        response, usercall, route=route
                    )
            else:
                await self.__process_func_response(
                    usercall_response, usercall, route=route
                )
        except Exception as e:
            await self._publish_error_log(usercall, e)
            raise

    async def _publish_error_log(
        self, usercall: UserCall, exc: Exception
    ) -> None:
        if self.__log_publisher is None:
            return
        try:
            import traceback
            import uuid
            from datetime import datetime, timezone

            from ..models.log_envelope import (
                ErrorLogPayload,
                EventType,
                LogEnvelope,
                error_code_from_exception,
            )

            menu = usercall.menu
            menu_name = menu.name if menu and menu.name else 'unknown'

            payload = ErrorLogPayload(
                error_code=error_code_from_exception(exc),
                error_message=f'{exc}\n{traceback.format_exc()}',
                context_menu_id=menu.id if menu and menu.id else 0,
                context_menu_name=menu_name,
                context_route=usercall.route or '',
            )

            user_state = usercall.user_state
            platform = user_state.platform if user_state else ''

            envelope = LogEnvelope(
                event_id=str(uuid.uuid4()),
                event_type=EventType.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id='',
                session_id=usercall.session_id or 0,
                chat_user_id=usercall.user_id,
                chat_company_id=usercall.company_id,
                platform=platform,
                origin=f'chatgraph:{menu_name}',
                error=str(exc),
                payload=payload.to_dict(),
            )

            await self.__log_publisher.publish_error(envelope)
        except Exception as pub_err:
            _logger.warning(f'Falha ao publicar log_error: {pub_err}')

    async def __process_func_response(
        self,
        usercall_response,
        usercall: UserCall,
        route: str,
    ) -> None:
        """
        Processa a resposta de uma função associada a uma rota,
        enviando mensagens ou ajustando estados.

        Args:
            usercall_response:
                A resposta gerada pela função da rota.
            usercall (UserCall):
                O objeto UserCall associado à mensagem processada.
            route (str):
                O nome da rota atual.
        """
        loop = asyncio.get_running_loop()

        if isinstance(usercall_response, (MessageTypes, Message, File)):
            # Envia o resultado como mensagem (executando a chamada síncrona no executor)
            await usercall.send(usercall_response)
            return

        if isinstance(usercall_response, Route):
            await usercall.set_route(usercall_response.current_node)
            return

        if isinstance(usercall_response, EndChatResponse):
            await usercall.end_chat(
                usercall_response.end_chat_id,
                end_action_name=usercall_response.end_chat_name,
                observation=usercall_response.observations,
            )
            return

        if isinstance(usercall_response, TransferToMenu):
            await usercall.transfer_to_menu(
                usercall_response.menu,
                usercall_response.user_message,
                usercall_response.route,
            )
            return

        if isinstance(usercall_response, RedirectResponse):
            await usercall.set_route(usercall_response.route)
            await self.process_message(usercall)
            return

        if not usercall_response:
            route = route + '.' + route.split('.')[-1]
            await usercall.set_route(route)
            return

        if isinstance(usercall_response, BackgroundTask):
            response = await usercall_response.run()
            await self.__process_func_response(response, usercall, route=route)
            return

        _logger.error('Tipo de retorno inválido!')
        return None
