from chatgraph.gRPC.gRPCCall import RouterServiceClient
from chatgraph.types.message_types import Message, Button, MessageTypes, messageTypes
from typing import Optional
from datetime import datetime
import json, os


class ChatID:
    """
    Representa o ID de um chat.

    Atributos:
        user_id (str): O ID do usuário.
        company_id (str): O ID da empresa
    """

    def __init__(
        self,
        user_id: str,
        company_id: str,
    ):
        self.user_id = user_id
        self.company_id = company_id

    def __str__(self):
        return f"ChatID({self.user_id}, {self.company_id})"

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "company_id": self.company_id,
        }


class UserState:
    """
    Representa o estado de um usuário.

    Atributos:
        chatID (ChatID): O ID do chat.
        menu (str): O menu atual.
        route (str): A rota atual.
        protocol (str): O protocolo atual.
        observations (dict): Observações do estado do usuário.
    """

    def __init__(
        self,
        chatID: ChatID,
        menu: str,
        route: str,
        protocol: str,
        observation: dict,
    ) -> None:

        self.chatID = chatID
        self.menu = menu
        self.route = route
        self.observation = observation
        self.protocol = protocol

    def __str__(self):
        return f"UserState({self.chatID}, {self.menu}, {self.route}, {self.protocol}, {self.observation})"

    def __chat_id_to_dict(self) -> dict:
        return {
            "user_id": self.chatID.user_id,
            "company_id": self.chatID.company_id,
        }

    def __user_state_to_dict(self) -> dict:
        return {
            "chat_id": {
                "user_id": self.chatID.user_id,
                "company_id": self.chatID.company_id,
            },
            "menu": self.menu,
            "route": self.route,
            "protocol": self.protocol,
            "observation": json.dumps(self.observation),
        }

    def insert(self, grpc_uri: Optional[str] = None) -> None:
        if grpc_uri is None:
            grpc_uri = os.getenv("GRPC_URI")
        router_client = RouterServiceClient(grpc_uri)

        ustate = self.__user_state_to_dict()
        result = router_client.insert_update_user_state(ustate)
        return result

    def delete(self, grpc_uri: Optional[str] = None) -> None:
        if grpc_uri is None:
            grpc_uri = os.getenv("GRPC_URI")
        router_client = RouterServiceClient(grpc_uri)

        ustate = self.__user_state_to_dict()
        response = router_client.delete_user_state(ustate["chat_id"])
        return response

    @classmethod
    def get_user_state(
        cls, user_id: str, company_id: str, grpc_uri: Optional[str] = None
    ) -> "UserState":
        if grpc_uri is None:
            grpc_uri = os.getenv("GRPC_URI")
        router_client = RouterServiceClient(grpc_uri)

        chat_id = {"user_id": user_id, "company_id": company_id}
        response = router_client.get_user_state(chat_id)

        if not response:
            raise ValueError("Erro ao buscar estado do usuário.")

        return cls(
            chatID=ChatID(
                user_id=response.chat_id.user_id,
                company_id=response.chat_id.company_id,
            ),
            menu=response.menu,
            route=response.route,
            protocol=response.protocol,
            observation=json.loads(response.observation),
        )


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
        user_state: UserState,
        type_message: str,
        content_message: str,
        grpc_uri: str,
    ) -> None:

        self.type = type
        self.type_message = type_message
        self.content_message = content_message
        self.__user_state = user_state

        self.__grpc_uri = grpc_uri

        self.__router_client = RouterServiceClient(self.__grpc_uri)

    def __str__(self):
        return f"UserCall({self.type}, {self.type_message}, {self.content_message}, {self.__user_state})"
    
    def send(
        self,
        message: messageTypes | Message,
    ) -> None:
        """
        Envia uma mensagem ao cliente.

        Args:
            message (Message|Button|ListElements): A mensagem a ser enviada.
        """
        if isinstance(message, MessageTypes):
            message = Message(
                type="message",
                detail=str(message),
            )

        if isinstance(message, Message):
            self.__send(message)
        else:
            raise ValueError("Tipo de mensagem inválido.")

    def __send(self, message: Message) -> None:

        dict_message = message.to_dict()
        dict_message["chat_id"] = self.__user_state.chatID.to_dict()
        response = self.__router_client.send_message(dict_message)

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de texto.")

        if not response.status:
            raise ValueError("Erro ao enviar mensagem de botões.")

    def transfer_to_human(self, message: str, campaign_name: str) -> None:
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

    def end_chat(self, message: str, tabulation_name: str) -> None:
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
        response = self.__user_state.delete(self.__grpc_uri)

        if not response.status:
            raise ValueError("Erro ao deletar estado do usuário.")

    def update_user_state(
        self,
        menu: str,
        route: str,
        observation: dict,
    ) -> None:

        self.__user_state.menu = menu
        self.__user_state.route = route
        self.__user_state.observation = observation
        self.__user_state.insert(self.__grpc_uri)

    @property
    def chatID(self):
        return self.__user_state.chatID

    @property
    def user_id(self):
        return self.__user_state.chatID.user_id

    @property
    def company_id(self):
        return self.__user_state.chatID.company_id

    @property
    def menu(self):
        return self.__user_state.menu

    @property
    def route(self):
        return self.__user_state.route

    @property
    def customer_id(self):
        return self.__user_state.customer_id

    @property
    def protocol(self):
        return self.__user_state.protocol
    
    @property
    def observation(self):
        return self.__user_state.observation

    @menu.setter
    def menu(self, menu):

        self.update_user_state(menu, self.__user_state.route, self.__user_state.obs)

    @route.setter
    def route(self, route):

        self.update_user_state(self.__user_state.menu, route, self.__user_state.obs)

    @observation.setter
    def observation(self, observation):

        self.update_user_state(
            self.__user_state.menu, self.__user_state.route, observation
        )
