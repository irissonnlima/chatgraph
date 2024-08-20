from dataclasses import dataclass
from typing import Optional


@dataclass
class Message:
    """
    Representa uma mensagem recebida ou enviada pelo chatbot.

    Atributos:
        type (str): O tipo da mensagem (por exemplo, texto, imagem, etc.).
        text (str): O conteúdo textual da mensagem.
        customer_id (str): O ID do cliente que enviou ou recebeu a mensagem.
        channel (str): O canal pelo qual a mensagem foi enviada ou recebida (por exemplo, WhatsApp, SMS, etc.).
        customer_phone (str): O número de telefone do cliente.
        company_phone (str): O número de telefone da empresa que está enviando ou recebendo a mensagem.
        status (Optional[str]): O status da mensagem (por exemplo, enviada, recebida, lida, etc.). Este campo é opcional.
    """
    type: str
    text: str
    customer_id: str
    channel: str
    customer_phone: str
    company_phone: str
    status: Optional[str] = None
