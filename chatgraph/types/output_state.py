from typing import Union
import json

messageTypes = Union[str, float, int, None]


class ChatbotResponse:
    """
    Representa a resposta do chatbot, contendo a mensagem a ser enviada ao usuário e a rota a ser seguida.

    Atributos:
        message (messageTypes): A mensagem de resposta do chatbot. Pode ser uma string, um número, ou None.
        route (str, opcional): A rota para a qual o chatbot deve direcionar após esta mensagem. Padrão é None.
    """

    def __init__(
            self, 
            message: messageTypes = None, 
            route: str = None, 
            abs_text:bool=False
        ) -> None:
        """
        Inicializa a resposta do chatbot com uma mensagem e uma rota opcional.

        Args:
            message (messageTypes, opcional): A mensagem a ser enviada ao usuário. Pode ser uma string, um número, ou None.
            route (str, opcional): A rota para a qual o chatbot deve direcionar após esta mensagem. Padrão é None.
        """
        if not message:
            message = ''
            
        if not abs_text:
            message = message.replace('\t', '')
            
        self.message = message
        self.route = route
    
    def json(self):
        '''
        Retorna o objeto em formato json.
        '''
        return {
            'type': 'message',
            'text': self.message,
        }


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

    def __init__(self, tabulation_id: str, observations:str) -> None:
        '''
        Finzaliza e tabula as informações do chatbot.
        '''
        self.tabulation_id = tabulation_id
        self.observations = observations
        
    def json(self):
        '''
        Retorna o objeto em formato json.
        '''
        return {
            'type': 'tabulate',
            'tabulation_id': self.tabulation_id,
            'observations': self.observations,
        }
        
class TransferToHuman:
    """
    Representa uma transferencia para um atendente humano.
    """
    def __init__(self, campaign_id: str, observations:str) -> None:
        '''
        Finzaliza e tabula as informações do chatbot.
        '''
        self.campaign_id = campaign_id
        self.observations = observations
        
    def json(self):
        '''
        Retorna o objeto em formato json.
        '''
        return {
            'type': 'transfer',
            'campaign_id': self.campaign_id,
            'observations': self.observations,
        }

class RedirectEntireChatbot:
    """
    Representa uma resposta que redireciona o fluxo do chatbot para um outro menu.

    Atributos:
        menu (str): O menu para o qual o chatbot deve redirecionar.
        route (str): A rota para a qual o chatbot deve redirecionar.
    """

    def __init__(self, menu:str, route: str) -> None:
        """
        Inicializa a resposta de redirecionamento com a rota especificada.

        Args:
            route (str): A rota para a qual o chatbot deve redirecionar.
        """
        self.route = route
        self.menu = menu
    def json(self):
        '''
        Retorna o objeto em formato json.
        '''
        return {
            'type': 'redirect',
            'menu': self.menu,
            'route': self.route,
        }