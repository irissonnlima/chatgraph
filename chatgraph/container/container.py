import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from ..services.router_http_client import RouterHTTPClient


class Container:
    @classmethod
    def load_dotenv(cls, env_path: str = '.env') -> None:
        load_dotenv(dotenv_path=env_path)

        """Carrega variáveis de ambiente a partir de um arquivo .env."""

    def __init__(self) -> None:
        Container.load_dotenv()
        self.__router_client: 'RouterHTTPClient | None' = None
        self.__router_url = os.getenv('ROUTER_URL', '')
        self.__router_token = os.getenv('ROUTER_TOKEN', '')

    def __initialize_router(self) -> 'RouterHTTPClient':
        """Inicializa o cliente HTTP apenas uma vez (singleton)."""
        from ..services.router_http_client import RouterHTTPClient

        if self.__router_client is None:
            self.__router_client = RouterHTTPClient(
                base_url=self.__router_url,
                username='chatgraph',
                password=self.__router_token,
                timeout=60,
            )
        return self.__router_client

    def get_router_client(self) -> 'RouterHTTPClient':
        """Retorna o cliente HTTP do roteador."""
        return self.__initialize_router()
