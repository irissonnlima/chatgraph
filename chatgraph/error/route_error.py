class RouteError(Exception):
    """
    Exceção personalizada para erros relacionados a rotas no sistema do chatbot.

    Atributos:
        message (str): A mensagem de erro descrevendo o problema.
    """

    def __init__(self, message: str):
        """
        Inicializa a exceção RouteError com uma mensagem de erro.

        Args:
            message (str): A mensagem de erro descrevendo o problema.
        """
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """
        Retorna a representação em string da exceção RouteError.

        Returns:
            str: Uma string formatada que inclui o nome da exceção e a mensagem de erro.
        """
        return f'RouteError: {self.message}'
