from ..error.route_error import RouteError


class Route:
    """
    Representa uma rota no sistema do chatbot, gerenciando a navegação entre diferentes partes do fluxo.

    Atributos:
        current (str): A rota atual.
        routes (list[str]): A lista de todas as rotas disponíveis no fluxo.
    """

    def __init__(self, current: str, routes: list[str], separator: str = "."):
        """
        Inicializa a rota com a rota atual e a lista de rotas disponíveis.

        Args:
            current (str): A rota atual.
            routes (list[str]): A lista de todas as rotas disponíveis no fluxo.
            separator (str): O separador de partes de rota. Padrão é '.'.
        """
        self.current = current
        self.routes = routes
        self.separator = separator

    @property
    def previous(self) -> "Route":
        """
        Retorna a rota anterior a atual do usuário
        """
        return self.get_previous()

    @property
    def current_node(self) -> str:
        """
        Retorna o nó atual do usuário
        """
        return self.current.split(self.separator)[-1]

    def get_previous(self) -> "Route":
        """
        Retorna o caminho anterior ao caminho atual.

        Raises:
            RouteError: Se a rota atual for 'start', indicando que não há caminho anterior.

        Returns:
            str: O caminho anterior à rota atual.
        """
        if self.current == "start":
            return Route(self.current, self.routes, self.separator)

        rotas_dedup = self.separator.join(
            dict.fromkeys(self.current.split(self.separator))
        )

        previous_route = self.separator.join(rotas_dedup.split(self.separator)[:-1])

        return Route(previous_route, self.routes, self.separator)

    def get_next(self, next_part: str) -> "Route":
        """
        Monta e retorna o próximo caminho com base na parte fornecida.

        Args:
            next_part (str): A parte do caminho a ser adicionada à rota atual.

        Raises:
            RouteError: Se a próxima rota montada não estiver na lista de rotas disponíveis.

        Returns:
            Route: O próximo caminho montado.
        """
        next_part = next_part.strip().lower()
        next_route = f"{self.current.rstrip(self.separator)}.{next_part}"
        if next_part not in self.routes:
            raise RouteError(f"Rota não encontrada: {next_part}")

        return Route(next_route, self.routes, self.separator)

    def __str__(self):
        """
        Retorna uma representação em string da rota atual.

        Returns:
            str: A representação em string da rota atual.
        """
        return f"Route(current={self.current})"

    def __repr__(self):
        """
        Retorna a representação oficial da rota, que é a mesma que a representação em string.

        Returns:
            str: A representação oficial da rota.
        """
        return self.__str__()
