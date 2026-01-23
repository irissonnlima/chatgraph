import asyncio
import inspect
import re
from functools import wraps
from logging import debug, error
from typing import Optional, Callable

from ..error.chatbot_error import ChatbotMessageError
from ..messages.message_consumer import MessageConsumer
from ..models.message import MessageTypes, Message, File
from ..types.usercall import UserCall
from ..types.end_types import (
    RedirectResponse,
    EndChatResponse,
    TransferToMenu,
)
from ..types.route import Route
from .chatbot_router import ChatbotRouter
from ..types.background_task import BackgroundTask
from .default_functions import voltar

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
    ):
        """
        Inicializa a classe ChatbotApp com um estado de usuário e um consumidor de mensagens.

        Args:
            message_consumer (MessageConsumer): O consumidor de mensagens que lida com a entrada de mensagens no sistema.
            default_functions (dict[str, callable]): Dicionário de funções padrão que podem ser usadas antes das rotas.
        """
        if not message_consumer:
            message_consumer = MessageConsumer.load_dotenv()

        self.default_functions = default_functions
        self.__message_consumer = message_consumer
        self.__routes = {}

    def include_router(self, router: ChatbotRouter) -> None:
        """
        Inclui um roteador de chatbot com um prefixo nas rotas da aplicação.

        Args:
            router (ChatbotRouter): O roteador contendo as rotas a serem adicionadas.
        """
        self.__routes.update(router.routes)

    def route(self, route_name: str) -> Callable:
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
                debug(f'Parameter: {name}, Type: {param_type}')

            self.__routes[route_name] = {
                'function': func,
                'params': params,
                'return': output_param,
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

        matchDefault = False

        for regex, func in self.default_functions.items():
            if re.match(regex, usercall.content_message):
                matchDefault = True
                debug(
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

        func = handler['function']
        usercall_name = handler['params'].get(UserCall, None)
        route_state_name = handler['params'].get(Route, None)

        kwargs = {}
        if usercall_name:
            kwargs[usercall_name] = usercall
        if route_state_name:
            kwargs[route_state_name] = Route(route, list(self.__routes.keys()))

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

        error('Tipo de retorno inválido!')
        return None
