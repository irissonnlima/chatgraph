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
        end_chat_id (str): O ID do fim do chatbot.
        end_chat_name (str): O nome da ação de encerramento.
        observations (str): As observações finais do chatbot.
    """

    def __init__(
        self,
        end_chat_id: str,
        end_chat_name: str = '',
        observations: str = '',
    ) -> None:
        """
        Finzaliza e tabula as informações do chatbot.
        """
        if not end_chat_id and not end_chat_name:
            raise ValueError('end_chat_id or end_chat_name must be provided.')

        self.end_chat_id = end_chat_id
        self.end_chat_name = end_chat_name
        self.observations = observations


class TransferToHuman:
    """
    OBSOLETO: sem efeito no pipeline HTTP. Era usado só pelo caminho
    gRPC legado (``gRPC/gRPCCall.py``); ``__process_func_response`` não
    tem ramo para este tipo. Para transferir para atendente humano, use
    ``EndChatResponse`` com a end action de atendimento humano
    configurada no chatbot-router — no chatbot, encerrar e transferir
    para humano são a mesma operação (uma tabulação de encerramento).
    """

    def __init__(
        self,
        campaign_id: str | None = None,
        campaign_name: str | None = None,
        observations: str | None = None,
    ) -> None:
        """
        Finzaliza e tabula as informações do chatbot.
        """
        self.campaign_id = campaign_id
        self.campaign_name = campaign_name
        self.observations = observations


class TransferToMenu:
    """
    Representa uma transferencia para outro Menu.
    """

    def __init__(self, menu: str, user_message: str, route: str = '') -> None:
        """
        Finzaliza e tabula as informações do chatbot.
        """
        self.menu = menu.lower()
        self.user_message = user_message
        self.route = route
