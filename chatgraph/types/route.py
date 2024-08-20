from ..error.route_error import RouteError


class Route:
    """
    Representa uma rota no sistema do chatbot, gerenciando a navegação entre diferentes partes do fluxo.

    Atributos:
        current (str): A rota atual.
        routes (list[str]): A lista de todas as rotas disponíveis no fluxo.
    """

    def __init__(self, current: str, routes: list[str]):
        """
        Inicializa a rota com a rota atual e a lista de rotas disponíveis.

        Args:
            current (str): A rota atual.
            routes (list[str]): A lista de todas as rotas disponíveis no fluxo.
        """
        self.current = current
        self.routes = routes

    def get_previous(self) -> str:
        """
        Retorna o caminho anterior ao caminho atual.

        Raises:
            RouteError: Se a rota atual for 'START', indicando que não há caminho anterior.

        Returns:
            str: O caminho anterior à rota atual.
        """
        if self.current == 'START':
            raise RouteError('Não há caminho anterior ao START')

        previous_route = '/'.join(self.current.split('/')[:-1])
        return previous_route

    def get_next(self, next_part: str) -> str:
        """
        Monta e retorna o próximo caminho com base na parte fornecida.

        Args:
            next_part (str): A parte do caminho a ser adicionada à rota atual.

        Raises:
            RouteError: Se a próxima rota montada não estiver na lista de rotas disponíveis.

        Returns:
            str: O próximo caminho construído a partir da rota atual e da parte fornecida.
        """
        next_part = next_part.strip().upper()
        next_route = f"{self.current.rstrip('/')}{next_part}"
        if next_route not in self.routes:
            raise RouteError(f'Rota não encontrada: {next_route}')
        return next_route

    def __str__(self):
        """
        Retorna uma representação em string da rota atual.

        Returns:
            str: A representação em string da rota atual.
        """
        return f'Route(current={self.current})'

    def __repr__(self):
        """
        Retorna a representação oficial da rota, que é a mesma que a representação em string.

        Returns:
            str: A representação oficial da rota.
        """
        return self.__str__()
