import inspect
from abc import ABC
from functools import wraps
from logging import debug

from ..error.chatbot_error import ChatbotError, ChatbotMessageError
from ..messages.base_message_consumer import MessageConsumer
from ..types.message_types import Message
from ..types.output_state import ChatbotResponse, RedirectResponse, EndChatResponse, TransferToHuman
from ..types.route import Route
from .chatbot_router import ChatbotRouter


class ChatbotApp(ABC):
    """
    Classe principal para a aplicação do chatbot, gerencia as rotas e a lógica de processamento de mensagens.
    """

    def __init__(self, message_consumer: MessageConsumer):
        """
        Inicializa a classe ChatbotApp com um estado de usuário e um consumidor de mensagens.

        Args:
            message_consumer (MessageConsumer): O consumidor de mensagens que lida com a entrada de mensagens no sistema.
        """
        self.__message_consumer = message_consumer
        self.__routes = {}
    
    def include_router(self, router: ChatbotRouter, prefix: str):
        """
        Inclui um roteador de chatbot com um prefixo nas rotas da aplicação.

        Args:
            router (ChatbotRouter): O roteador contendo as rotas a serem adicionadas.
            prefix (str): O prefixo a ser adicionado às rotas do roteador.

        Raises:
            ChatbotError: Se a rota 'start' não for encontrada no roteador.
        """
        if 'start' not in router.routes.keys():
            raise ChatbotError('Erro ao incluir rota, start não encontrado!')

        prefixed_routes = {
            (
                f'start{prefix.lower()}'
                if key.lower() == 'start'
                else f'start{prefix.lower()}{key.lower().replace("start", "")}'
            ): value
            for key, value in router.routes.items()
        }
        self.__routes.update(prefixed_routes)

    def route(self, route_name: str):
        """
        Decorador para adicionar uma função como uma rota na aplicação do chatbot.

        Args:
            route_name (str): O nome da rota para a qual a função deve ser associada.

        Returns:
            function: O decorador que adiciona a função à rota especificada.
        """
        route_name = route_name.strip().lower()

        if 'start' not in route_name:
            route_name = f'start{route_name}'

        def decorator(func):
            params = dict()
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
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def start(self):
        """
        Inicia o consumo de mensagens pelo chatbot, processando cada mensagem recebida.
        """
        self.__message_consumer.start_consume(self.process_message)

    def process_message(self, message: Message):
        """
        Processa uma mensagem recebida, identificando a rota correspondente e executando a função associada.

        Args:
            message (Message): A mensagem a ser processada.

        Raises:
            ChatbotMessageError: Se nenhuma rota for encontrada para o menu atual do usuário.
            ChatbotError: Se o tipo de retorno da função associada à rota for inválido.

        Returns:
            str: A resposta gerada pela função da rota, que pode ser uma mensagem ou o resultado de uma redireção.
        """
        customer_id = message.user_state.customer_id
        user_state = message.user_state
        menu = message.user_state.menu
        menu = menu.lower()
        handler = self.__routes.get(menu, None)

        if not handler:
            raise ChatbotMessageError(
                customer_id, f'Rota não encontrada para {menu}!'
            )
        func = handler['function']
        message_name = handler['params'].get(Message, None)
        route_state_name = handler['params'].get(Route, None)

        kwargs = dict()
        if message_name:
            kwargs[message_name] = message
        if route_state_name:
            kwargs[route_state_name] = Route(menu, list(self.__routes.keys()))

        message_response = func(**kwargs)

        if type(message_response) in (str, float, int):
            response = ChatbotResponse(message_response)
            return response.json()
        elif type(message_response) == ChatbotResponse:
            route = self.__adjust_route(message_response.route, menu)
            response = message_response.json()
            response['user_state'] = {
                'customer_id': customer_id,
                'menu': route,
                'obs': user_state.obs,
            }
            return response            
        elif type(message_response) in (ChatbotResponse, EndChatResponse, TransferToHuman):
            return message_response.json()
        elif type(message_response) == RedirectResponse:
            route = self.__adjust_route(message_response.route, menu)
            message.user_state.menu = route
            return self.process_message(message)
        else:
            raise ChatbotError('Tipo de retorno inválido!')

    def __adjust_route(self, route: str, absolute_route: str) -> str:
        """
        Ajusta a rota fornecida para incluir o prefixo necessário, se não estiver presente.

        Args:
            route (str): A rota que precisa ser ajustada.
            absolute_route (str): A rota completa atual, usada como referência.

        Returns:
            str: A rota ajustada.
        """
        if not route:
            return absolute_route

        if 'start' not in route:
            route = absolute_route + route

        return route
