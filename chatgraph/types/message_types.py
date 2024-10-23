from ..gRPC.gRPCCall import WhatsappServiceClient, UserStateServiceClient

from dataclasses import dataclass
from typing import Optional
import json

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
    route: str
    lst_update: str
    obs: Optional[dict] = None


@dataclass
class Element:
    """
    Representa um elemento de uma lista de opções.
    
    Atributos:
        title (str): O título do elemento.
        description (str): A descrição do elemento.
    """
    title: str
    description: Optional[str] = None

class UserCall:
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
    def __init__(
        self,
        type: str,
        text: str,
        user_state: UserState,
        channel: str,
        customer_phone: str,
        company_phone: str,
        grpc_uri: str,
        status: Optional[str] = None,
    ) -> None:
        
        self.type = type
        self.text = text
        self.__user_state = user_state
        self.channel = channel
        self.customer_phone = customer_phone
        self.company_phone = company_phone
        self.status = status
        
        self.grpc_uri = grpc_uri
        
        self.__wpp_server_client = WhatsappServiceClient(self.grpc_uri)
        self.__user_state_client = UserStateServiceClient(self.grpc_uri)

    def send_text(self, text:str, abs_text:bool=False) -> None:
        if not abs_text:
            text = text.replace('\t', '')
        
        response = self.__wpp_server_client.send_text(
            {
                "hook_id": self.company_phone,
                "enterprise_id": self.customer_phone,
                "unique_customer_id": self.__user_state.customer_id,
                "message_text": text
            }
        )

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de texto.")
    
    def send_button(
        self, 
        text:str, 
        buttons:list, 
        title: str|None = None,
        caption: str|None = None,
        ) -> None:
        if len(buttons) > 3:
            raise ValueError("O número máximo de botões é 3.")
        
        response = self.__wpp_server_client.send_button(
            {
                "hook_id": self.company_phone,
                "enterprise_id": self.customer_phone,
                "unique_customer_id": self.__user_state.customer_id,
                "message_text": text,
                "button_title": title,
                "message_caption": caption,
                "message_title": title,
                "options": [{"title": b} for b in buttons],
            }
        )

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de botões.")

    def send_list(
        self, 
        text:str,
        title: str|None = None,
        button_title: str|None = None,
        element_list: list[Element] = None,
        caption: str|None = None,
        ) -> None:
        
        if len(element_list) > 20:
            raise ValueError("O número máximo de elementos é 20.")
        
        response = self.__wpp_server_client.send_list(
            {
                "hook_id": self.company_phone,
                "enterprise_id": self.customer_phone,
                "unique_customer_id": self.__user_state.customer_id,
                "message_text": text,
                "button_title": button_title,
                "message_caption": caption,
                "message_title": title,
                "options": [{"title": e.title, "description": e.description} for e in element_list],
            }
        )

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de lista.")
    
    def delete_user_state(self) -> None:
        response = self.__user_state_client.delete_user_state(self.__user_state.customer_id)

        if not response.status:
            raise ValueError("Erro ao deletar estado do usuário.")

    def update_user_state(
        self, 
        menu: str,
        route: str,
        obs: dict,
        ) -> None:
        
        response = self.__user_state_client.update_user_state({
            "user_id": self.__user_state.customer_id,
            "menu_id": menu,
            "route": route,
            "obs": json.dumps(obs),
        })

        if not response.status:
            raise ValueError("Erro ao atualizar estado do usuário.")
        
        self.__user_state.menu = menu
        self.__user_state.route = route
        self.__user_state.obs = obs
    
    @property
    def menu(self):
        return self.__user_state.menu
    
    @property
    def route(self):
        return self.__user_state.route
    
    @property
    def obs(self):
        return self.__user_state.obs
    
    @property
    def customer_id(self):
        return self.__user_state.customer_id
    
    @menu.setter
    def menu(self, menu):
        
        self.update_user_state(
            menu, 
            self.__user_state.route, 
            self.__user_state.obs
        )
    
    @route.setter
    def route(self, route):
        
        self.update_user_state(
            self.__user_state.menu, 
            route, 
            self.__user_state.obs
        )
    
    @obs.setter
    def obs(self, obs):
        
        self.update_user_state(
            self.__user_state.menu, 
            self.__user_state.route, 
            obs
        )
    