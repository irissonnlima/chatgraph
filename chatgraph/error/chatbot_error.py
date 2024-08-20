class ChatbotError(Exception):
    """
    Exceção personalizada para erros gerais relacionados ao chatbot.

    Atributos:
        message (str): A mensagem de erro descrevendo o problema.
    """

    def __init__(self, message: str):
        """
        Inicializa a exceção ChatbotError com uma mensagem de erro.

        Args:
            message (str): A mensagem de erro descrevendo o problema.
        """
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """
        Retorna a representação em string da exceção ChatbotError.

        Returns:
            str: Uma string formatada que inclui o nome da exceção e a mensagem de erro.
        """
        return f'ChatbotError: {self.message}'


class ChatbotMessageError(Exception):
    """
    Exceção personalizada para erros relacionados a mensagens de clientes no chatbot.

    Atributos:
        customer_id (str): O ID do cliente relacionado ao erro.
        message (str): A mensagem de erro descrevendo o problema, incluindo o ID do cliente.
    """

    def __init__(self, customer_id: str, message: str):
        """
        Inicializa a exceção ChatbotMessageError com um ID de cliente e uma mensagem de erro.

        Args:
            customer_id (str): O ID do cliente relacionado ao erro.
            message (str): A mensagem de erro descrevendo o problema.
        """
        self.customer_id = customer_id
        self.message = f'{message} ID recebido: {customer_id}'
        super().__init__(self.message)

    def __str__(self):
        """
        Retorna a representação em string da exceção ChatbotMessageError.

        Returns:
            str: Uma string formatada que inclui o nome da exceção e a mensagem de erro.
        """
        return f'ChatbotMessageError: {self.message}'
