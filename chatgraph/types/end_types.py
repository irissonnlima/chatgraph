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


class EndChatResponse:
    """
    Representa uma resposta que indica o fim do chatbot.

    Atributos:
        tabulation_id (str): O ID da tabulação do chatbot.
        observations (str): As observações finais do chatbot.
    """

    def __init__(self, tabulation_id: str, observations: str) -> None:
        """
        Finzaliza e tabula as informações do chatbot.
        """
        self.tabulation_id = tabulation_id
        self.observations = observations


class TransferToHuman:
    """
    Representa uma transferencia para um atendente humano.
    """

    def __init__(self, campaign_id: str, observations: str) -> None:
        """
        Finzaliza e tabula as informações do chatbot.
        """
        self.campaign_id = campaign_id
        self.observations = observations


class TransferToMenu:
    """
    Representa uma transferencia para outro Menu.
    """

    def __init__(self, menu: str, user_message: str) -> None:
        """
        Finzaliza e tabula as informações do chatbot.
        """
        self.menu = menu.lower()
        self.user_message = user_message
