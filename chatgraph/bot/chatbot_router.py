
import inspect
from functools import wraps
from logging import debug

from ..error.chatbot_error import ChatbotError


class ChatbotRouter:
    """
    Classe responsável por gerenciar e registrar as rotas do chatbot, associando-as a funções específicas.
    
    Atributos:
        routes (dict): Um dicionário que armazena as rotas do chatbot e suas funções associadas.
    """

    def __init__(self):
        """
        Inicializa a classe ChatbotRouter com um dicionário vazio de rotas.
        """
        self.__routes = {}
    
    @property
    def routes(self):
        """
        Retorna as rotas registradas no roteador.

        Returns:
            dict: Um dicionário contendo as rotas e funções associadas.
        """
        return self.__routes

    def route(self, route_name: str):
        """
        Decorador para adicionar uma função como uma rota no roteador do chatbot.

        Args:
            route_name (str): O nome da rota para a qual a função deve ser associada.

        Returns:
            function: O decorador que adiciona a função à rota especificada.
        """

        route_name = route_name.strip().lower()

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

    def include_router(self, router: 'ChatbotRouter'):
        """
        Inclui outro roteador com um prefixo nas rotas do roteador atual.

        Args:
            router (ChatbotRouter): O roteador contendo as rotas a serem adicionadas.
            prefix (str): O prefixo a ser adicionado às rotas do roteador.

        Raises:
            ChatbotError: Se a rota 'start' não for encontrada no roteador fornecido.
        """
        self.__routes.update(router.__routes)
