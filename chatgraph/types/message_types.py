from dataclasses import dataclass
from typing import Optional


@dataclass
class UserState:
    """
    Representa o estado de um usuário.
    
    Atributos:
        customer_id (str): O ID do cliente.
        menu (str): O menu atual.
        lst_update (str): A última atualização do menu.
        obs (dict): Observações adicionais sobre o estado do usuário.
    """
    customer_id: str
    menu: str
    lst_update: str
    obs: Optional[dict] = None

@dataclass
class Message:
    """
    Representa uma mensagem recebida ou enviada pelo chatbot.

    Atributos:
        type (str): O tipo da mensagem (por exemplo, texto, imagem, etc.).
        text (str): O conteúdo textual da mensagem.
        UserState (UserState): O estado do usuário.
        channel (str): O canal pelo qual a mensagem foi enviada ou recebida (por exemplo, WhatsApp, SMS, etc.).
        customer_phone (str): O número de telefone do cliente.
        company_phone (str): O número de telefone da empresa que está enviando ou recebendo a mensagem.
        status (Optional[str]): O status da mensagem (por exemplo, enviada, recebida, lida, etc.). Este campo é opcional.
    """
    type: str
    text: str
    user_state: UserState
    channel: str
    customer_phone: str
    company_phone: str
    status: Optional[str] = None
