import inspect
from functools import wraps
from logging import debug
import json
from logging import error

from ..error.chatbot_error import ChatbotError, ChatbotMessageError
from ..messages.message_consumer import MessageConsumer
from ..types.message_types import UserCall
from ..types.output_state import ChatbotResponse, RedirectResponse, EndChatResponse, TransferToHuman
from ..types.route import Route
from .chatbot_router import ChatbotRouter


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
        self.__message_consumer.reprer()
        self.__message_consumer.start_consume(self.process_message)
    
    def process_message(self, userCall: UserCall):
        """
        Processa uma mensagem recebida, identificando a rota correspondente e executando a função associada.

        Args:
            userCall (Message): A mensagem a ser processada.

        Raises:
            ChatbotMessageError: Se nenhuma rota for encontrada para o menu atual do usuário.
            ChatbotError: Se o tipo de retorno da função associada à rota for inválido.

        Returns:
            str: A resposta gerada pela função da rota, que pode ser uma mensagem ou o resultado de uma redireção.
        """
        customer_id = userCall.customer_id
        route = userCall.route.lower()
        menu = userCall.menu.lower()
        obs = userCall.obs
        handler = self.__routes.get(route, None)

        if not handler:
            raise ChatbotMessageError(
                customer_id, f'Rota não encontrada para {route}!'
            )
            
        func = handler['function']
        userCall_name = handler['params'].get(UserCall, None)
        route_state_name = handler['params'].get(Route, None)

        kwargs = dict()
        if userCall_name:
            kwargs[userCall_name] = userCall
        if route_state_name:
            kwargs[route_state_name] = Route(route, list(self.__routes.keys()))

        userCall_response = func(**kwargs)
        
        if isinstance(userCall_response, (list, tuple)):
            for response in userCall_response:
                return self.__process_response(response, userCall)

    def __process_response(self, userCall_response, userCall: UserCall):
        
        if isinstance(userCall_response, (str, float, int)):
            
            return self.__create_response(userCall_response, customer_id, route, menu, obs)

        elif isinstance(userCall_response, ChatbotResponse):
            adjusted_route = self.__adjust_route(userCall_response.route, route)
            return self.__create_response(userCall_response.json(), customer_id, adjusted_route, menu, obs)

        elif isinstance(userCall_response, (EndChatResponse, TransferToHuman)):
            return self.__end_chat_response(userCall_response, customer_id)

        elif isinstance(userCall_response, RedirectResponse):
            route = self.__adjust_route(userCall_response.route, route)
            userCall.route = route
            return self.process_message(userCall)

        elif not userCall_response:
            return self.__create_response('', customer_id, None, None, None)

        else:
            error('Tipo de retorno inválido!')
            return None
        

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
    
    def __create_response(self, response, customer_id, route, menu, obs):
        """
        Cria uma resposta padronizada em formato JSON com o estado do usuário.
        """
        response = ChatbotResponse(response).json() if not isinstance(response, dict) else response
        response['user_state'] = {
            'customer_id': customer_id,
            'route': route,
            'menu': menu,
            'obs': obs,
        }
        return json.dumps(response)

    def __end_chat_response(self, response, customer_id):
        """
        Gera a resposta de finalização ou transferência de chat.
        """
        response = response.json()
        response['user_state'] = {
            'customer_id': customer_id,
            'menu': None,
            'route': None,
            'obs': None,
        }
        return json.dumps(response)