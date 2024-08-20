import inspect
from abc import ABC
from functools import wraps
from logging import debug

from ..error.chatbot_error import ChatbotError, ChatbotMessageError
from ..messages.base_message_consumer import MessageConsumer
from ..types.message_types import Message
from ..types.route import Route
from ..types.user_state import UserState
from .chatbot_router import ChatbotRouter
from ..types.output_state import ChatbotResponse, RedirectResponse

class ChatbotApp(ABC):
    def __init__(
        self,
        user_state: UserState,
        message_consumer: MessageConsumer,
    ):
        self.__message_consumer = message_consumer
        self.__user_state = user_state
        self.__routes = {}

    def include_router(self, router: ChatbotRouter, prefix: str):
        if 'START' not in router.routes.keys():
            raise ChatbotError('Erro ao incluir rota, START não encontrado!')

        prefixed_routes = {
            (
                f'START{prefix.upper()}'
                if key.upper() == 'START'
                else f'START{prefix.upper()}{key.upper().replace("START", "")}'
            ): value
            for key, value in router.routes.items()
        }
        self.__routes.update(prefixed_routes)

    def route(self, route_name: str):
        if not 'START' in route_name:
            route_name = f'START{route_name}'
            
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

                
            self.__routes[route_name.strip().upper()] = {
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
        self.__message_consumer.start_consume(self.process_message)

    def process_message(self, message: Message):
        customer_id = message.customer_id

        menu = self.__user_state.get_menu(customer_id)
        menu = menu.upper()
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
            return message_response
        elif type(message_response) == ChatbotResponse:
            route = self.__adjust_route(message_response.route, menu)
            self.__user_state.set_menu(customer_id, route)
            return message_response.message
        elif type(message_response) == RedirectResponse:
            route = self.__adjust_route(message_response.route, menu)
            self.__user_state.set_menu(customer_id, route)
            return self.process_message(message)
        else:
            raise ChatbotError('Tipo de retorno inválido!')
    
    def __adjust_route(self, route: str, absolute_route:str) -> str:
        if not route:
            return absolute_route
        
        if not 'START' in route:
            route = absolute_route+route
            
        return route
