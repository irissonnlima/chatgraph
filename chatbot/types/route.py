from ..error.route_error import RouteError


class Route:
    def __init__(self, current: str, routes: list[str]):
        self.current = current
        self.routes = routes

    def get_previous(self) -> str:
        """
        Retorna o caminho anterior ao caminho atual.
        """
        if self.current == 'START':
            raise RouteError('Não há caminho anterior ao START')

        previous_route = '/'.join(self.current.split('/')[:-1])
        return previous_route

    def get_next(self, next_part: str) -> str:
        """
        Monta e retorna o próximo caminho com base na parte fornecida.
        """
        next_part = next_part.strip().upper()
        next_route = f"{self.current.rstrip('/')}{next_part}"
        if next_route not in self.routes:
            raise RouteError(f'Rota não encontrada: {next_route}')
        return next_route

    def __str__(self):
        return f'Route(current={self.current})'

    def __repr__(self):
        return self.__str__()
