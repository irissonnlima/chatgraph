from typing import Union

messageTypes = Union[str, float, int, None]


class ChatbotResponse:
    """
    Representa a resposta do chatbot, contendo a mensagem a ser enviada ao usuário e a rota a ser seguida.

    Atributos:
        message (messageTypes): A mensagem de resposta do chatbot. Pode ser uma string, um número, ou None.
        route (str, opcional): A rota para a qual o chatbot deve direcionar após esta mensagem. Padrão é None.
    """

    def __init__(self, message: messageTypes = None, route: str = None) -> None:
        """
        Inicializa a resposta do chatbot com uma mensagem e uma rota opcional.

        Args:
            message (messageTypes, opcional): A mensagem a ser enviada ao usuário. Pode ser uma string, um número, ou None.
            route (str, opcional): A rota para a qual o chatbot deve direcionar após esta mensagem. Padrão é None.
        """
        self.message = message
        self.route = route


class RedirectResponse:
    """
    Representa uma resposta que redireciona o fluxo do chatbot para uma nova rota.

    Atributos:
        route (str): A rota para a qual o chatbot deve redirecionar.
    """

    def __init__(self, route: str) -> None:
        """
        Inicializa a resposta de redirecionamento com a rota especificada.

        Args:
            route (str): A rota para a qual o chatbot deve redirecionar.
        """
        self.route = route
