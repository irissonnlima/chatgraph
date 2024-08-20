import inspect
from functools import wraps
from logging import debug

from ..error.chatbot_error import ChatbotError
from ..types.message_types import Message


class ChatbotRouter:
    def __init__(self):
        self.routes = {}

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

                
            self.routes[route_name.strip().upper()] = {
                'function': func,
                'params': params,
                'return': output_param,
            }

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def include_router(self, router: 'ChatbotRouter', prefix: str):
        if 'START' not in router.routes.keys():
            raise ChatbotError('Erro ao incluir rota, START não encontrado!')

        prefixed_routes = {
            (
                f'{prefix.upper()}'
                if key.upper() == 'START'
                else f'START{prefix.upper()}{key.upper().replace("START", "")}'
            ): value
            for key, value in router.routes.items()
        }
        self.routes.update(prefixed_routes)
