from chatgraph.gRPC.gRPCCall import WhatsappServiceClient, UserStateServiceClient
from chatgraph.types.message_types import Message, Button, ListElements, messageTypes, MessageTypes
from dataclasses import dataclass
from typing import Optional
import json, os

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
    def __init__(
        self,
        customer_id: str,
        menu: str,
        route: str,
        voll_id: str,
        platform: str,
        direction_in: bool,
        lst_update: Optional[str]=None,
        obs: Optional[dict] = None,
    ) -> None:
        
        self.customer_id = customer_id
        self.menu = menu
        self.route = route
        self.lst_update = lst_update
        self.obs = obs
        self.direction_in = direction_in
        self.voll_id = voll_id
        self.platform = platform

    def __str__(self):
        return f"UserState:\n\tcustomer_id={self.customer_id},\n\tmenu={self.menu},\n\troute={self.route},\n\tlst_update={self.lst_update},\n\tobs={self.obs},\n\tdirection_in={self.direction_in}"

    def insert(self, grpc_uri: Optional[str] = None) -> None:
        if grpc_uri is None:
            grpc_uri = os.getenv('GRPC_URI')
        user_state_client = UserStateServiceClient(grpc_uri)
        
        user_state_client.insert_user_state({
            'user_id': self.customer_id,
            'menu_id': self.menu,
            'route': self.route,
            'obs': json.dumps(self.obs),
            'direction': self.direction_in,
            'voll_id': self.voll_id,
            'platform': self.platform,
        })
    
    def update(self, grpc_uri: Optional[str] = None) -> None:
        if grpc_uri is None:
            grpc_uri = os.getenv('GRPC_URI')
        user_state_client = UserStateServiceClient(grpc_uri)
        
        user_state_client.update_user_state({
            'user_id': self.customer_id,
            'menu_id': self.menu,
            'route': self.route,
            'obs': json.dumps(self.obs),
        })
    
    def delete(self, grpc_uri: Optional[str] = None) -> None:
        if grpc_uri is None:
            grpc_uri = os.getenv('GRPC_URI')
        user_state_client = UserStateServiceClient(grpc_uri)
        
        user_state_client.delete_user_state(self.customer_id)

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

    def send(self, message: messageTypes|Message|Button|ListElements) -> None:
        """
        Envia uma mensagem ao cliente.

        Args:
            message (Message|Button|ListElements): A mensagem a ser enviada.
        """
        if isinstance(message, MessageTypes):
            message = Message(message)
        
        if isinstance(message, Message):
            self.__send_text(message.text, message.absolute_text)
            
        elif isinstance(message, Button):
            self.__send_button(
                message.text, 
                message.buttons, 
                message.title, 
                message.caption
            )
            
        elif isinstance(message, ListElements):
            self.__send_list(
                text=message.text,
                title=message.title, 
                button_title=message.button_title, 
                caption=message.caption,
                element_list=message.elements, 
            )
        else:
            raise ValueError("Tipo de mensagem inválido.")
    
    def __send_text(self, text:str, abs_text:bool=False) -> None:
        if not abs_text:
            text = text.replace('\t', '')
        
        response = self.__wpp_server_client.send_text(
            {
                "hook_id": self.company_phone,
                "enterprise_id": self.customer_phone,
                "unique_customer_id": self.__user_state.voll_id,
                "message_text": text,
                "platform": self.channel,
            }
        )

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de texto.")
    
    def __send_button(
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
                "unique_customer_id": self.__user_state.voll_id,
                "message_text": text,
                "button_title": title,
                "message_caption": caption,
                "message_title": title,
                "options": [{"title": b} for b in buttons],
            }
        )

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de botões.")

    def __send_list(
        self, 
        text:str,
        button_title: str,
        title: str|None = None,
        element_list: list[dict] = None,
        caption: str|None = None,
        ) -> None:
        
        if not button_title:
            raise NameError('Button Title é um parâmetro obrigatório!')
        
        if len(element_list) > 20:
            raise ValueError("O número máximo de elementos é 20.")
        
        response = self.__wpp_server_client.send_list(
            {
                "hook_id": self.company_phone,
                "enterprise_id": self.customer_phone,
                "unique_customer_id": self.__user_state.voll_id,
                "message_text": text,
                "button_title": button_title,
                "message_caption": caption,
                "message_title": title,
                "options": [{"title": k, "description": v} for k,v in element_list.items()],
            }
        )

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de lista.")
    
    def transfer_to_human(self, message:str, campaign_name:str) -> None:
        response = self.__wpp_server_client.transfer_to_human(
            {
                "hook_id": self.company_phone,
                "enterprise_id": self.customer_phone,
                "unique_customer_id": self.__user_state.customer_id,
                "voll_id": self.__user_state.voll_id,
                "message_text": message,
                "platform": self.channel,
                "campaign_name": campaign_name,
            }
        )

        if not response.status:
            raise ValueError("Erro ao transferir chat para humano.")
    
    def end_chat(self, message:str, tabulation_name:str) -> None:
        response = self.__wpp_server_client.end_chat(
            {
                "tabulation_name": tabulation_name,
                "hook_id": self.company_phone,
                "unique_customer_id": self.__user_state.customer_id,
                "voll_id": self.__user_state.voll_id,
                "message_text": message,
                "platform": self.channel,
            }
        )

        if not response.status:
            raise ValueError("Erro ao encerrar chat.")
    
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
    