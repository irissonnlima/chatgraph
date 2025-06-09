import inspect
from functools import wraps
from logging import debug, error
import asyncio

from ..error.chatbot_error import ChatbotMessageError
from ..messages.message_consumer import MessageConsumer
from ..types.request_types import UserCall
from ..types.message_types import Message, Button
from ..types.end_types import (
    RedirectResponse,
    EndChatResponse,
    TransferToHuman,
    TransferToMenu,
)
from ..types.route import Route
from .chatbot_router import ChatbotRouter
from ..types.background_task import BackgroundTask


class ChatbotApp:
    """
    Classe principal para a aplicação do chatbot, gerencia as rotas e a lógica de processamento de mensagens.
    """

    def __init__(self, message_consumer: MessageConsumer = None):
        """
        Inicializa a classe ChatbotApp com um estado de usuário e um consumidor de mensagens.

        Args:
            message_consumer (MessageConsumer): O consumidor de mensagens que lida com a entrada de mensagens no sistema.
        """
        if not message_consumer:
            message_consumer = MessageConsumer.load_dotenv()

        self.__message_consumer = message_consumer
        self.__routes = {}

    def include_router(self, router: ChatbotRouter):
        """
        Inclui um roteador de chatbot com um prefixo nas rotas da aplicação.

        Args:
            router (ChatbotRouter): O roteador contendo as rotas a serem adicionadas.
        """
        self.__routes.update(router.routes)

    def route(self, route_name: str):
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
                    else "Any"
                )
                params[param_type] = name
                debug(f"Parameter: {name}, Type: {param_type}")

            self.__routes[route_name] = {
                "function": func,
                "params": params,
                "return": output_param,
            }

            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def start(self):
        """
        Inicia o consumo de mensagens pelo chatbot, processando cada mensagem recebida.
        """
        self.__message_consumer.reprer()
        asyncio.run(self.__message_consumer.start_consume(self.process_message))

    async def process_message(self, userCall: UserCall):
        """
        Processa uma mensagem recebida, identificando a rota correspondente e executando a função associada.

        Args:
            userCall (UserCall): A mensagem a ser processada.

        Raises:
            ChatbotMessageError: Se nenhuma rota for encontrada para o menu atual do usuário.
        """
        user_id = userCall.user_id
        route = userCall.route.lower()
        route_handler = route.split(".")[-1]

        handler = self.__routes.get(route_handler, None)

        if not handler:
            raise ChatbotMessageError(user_id, f"Rota não encontrada para {route}!")

        func = handler["function"]
        userCall_name = handler["params"].get(UserCall, None)
        route_state_name = handler["params"].get(Route, None)

        kwargs = {}
        if userCall_name:
            kwargs[userCall_name] = userCall
        if route_state_name:
            kwargs[route_state_name] = Route(route, list(self.__routes.keys()))

        if asyncio.iscoroutinefunction(func):
            userCall_response = await func(**kwargs)
        else:
            loop = asyncio.get_running_loop()
            userCall_response = await loop.run_in_executor(None, lambda: func(**kwargs))

        if isinstance(userCall_response, (list, tuple)):
            for response in userCall_response:
                await self.__process_func_response(response, userCall, route=route)
        else:
            await self.__process_func_response(userCall_response, userCall, route=route)

    async def __process_func_response(
        self, userCall_response, userCall: UserCall, route: str
    ):
        """
        Processa a resposta de uma função associada a uma rota, enviando mensagens ou ajustando estados.

        Args:
            userCall_response: A resposta gerada pela função da rota.
            userCall (UserCall): O objeto UserCall associado à mensagem processada.
            route (str): O nome da rota atual.
        """
        loop = asyncio.get_running_loop()

        if isinstance(userCall_response, (str, float, int)):
            # Envia o resultado como mensagem (executando a chamada síncrona no executor)
            await loop.run_in_executor(None, userCall.send, Message(userCall_response))
            return

        elif isinstance(userCall_response, Route):
            userCall.route = userCall_response.current
            return

        elif isinstance(userCall_response, (Message, Button)):
            # Envia o objeto Message ou Button
            await loop.run_in_executor(None, userCall.send, userCall_response)
            return

        elif isinstance(userCall_response, EndChatResponse):
            await loop.run_in_executor(
                None,
                userCall.end_chat,
                userCall_response.observations,
                userCall_response.tabulation_id,
            )
            return

        elif isinstance(userCall_response, TransferToHuman):
            await loop.run_in_executor(
                None,
                userCall.transfer_to_human,
                userCall_response.observations,
                userCall_response.campaign_id,
            )
            return

        elif isinstance(userCall_response, TransferToMenu):
            await loop.run_in_executor(
                None,
                userCall.transfer_to_menu,
                userCall_response.menu,
                userCall_response.user_message,
            )
            return

        elif isinstance(userCall_response, RedirectResponse):
            route = route + "." + userCall_response.route
            userCall.route = route
            await self.process_message(userCall)

        elif not userCall_response:
            route = route + "." + route.split(".")[-1]
            userCall.route = route
            return

        elif isinstance(userCall_response, BackgroundTask):
            response = await userCall_response.run()
            await self.__process_func_response(response, userCall, route=route)

        else:
            error("Tipo de retorno inválido!")
            return None
