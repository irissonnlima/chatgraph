"""Construção compartilhada de entradas de rota.

Extrai a introspecção de assinatura antes duplicada entre
``ChatbotApp.route`` e ``ChatbotRouter.route``, e adiciona os metadados
usados pelos agentes de IA (``description``/``ai_visible``).

Limitação conhecida da injeção por tipo: dois parâmetros com a mesma
anotação colidem no dict ``params`` (o último vence).
"""

import inspect
from typing import Callable, Optional

from ..logger.user_logger import UserLoggerManager

_logger = UserLoggerManager.get_system_logger()


def build_route_entry(
    func: Callable,
    auth_level: Optional[str] = None,
    description: str = '',
    ai_visible: bool = False,
) -> dict:
    """Monta a entrada de registro de uma rota.

    ``description`` é o prompt de comportamento da rota para agentes de
    IA (mesma semântica do chatgraph-go); ``ai_visible`` expõe a rota
    ao roteamento do agente.
    """
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

    return {
        'function': func,
        'params': params,
        'return': output_param,
        'auth_level': auth_level,
        'description': description,
        'ai_visible': ai_visible,
    }


def route_infos(routes: dict) -> list[dict]:
    """Metadados das rotas registradas, para consumo do agente de IA
    (via ``Route.infos``)."""
    return [
        {
            'name': name,
            'description': entry.get('description', ''),
            'ai_visible': entry.get('ai_visible', False),
        }
        for name, entry in routes.items()
    ]
