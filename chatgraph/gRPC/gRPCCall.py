import os
import grpc
import json
from rich.console import Console

import chatgraph.pb.router_pb2 as chatbot_pb2
import chatgraph.pb.router_pb2_grpc as chatbot_pb2_grpc


class RouterServiceClient:
    def __init__(self, grpc_uri=None):
        self.grpc_uri = grpc_uri or os.getenv("GRPC_URI")

        if not self.grpc_uri:
            raise ValueError("A variável de ambiente 'GRPC_URI' não está definida.")

        # Cria o canal gRPC
        self.channel = grpc.insecure_channel(self.grpc_uri)

        # Cria os stubs para os serviços gRPC
        self.user_state_stub = chatbot_pb2_grpc.UserStateServiceStub(self.channel)
        self.send_message_stub = chatbot_pb2_grpc.SendMessageStub(self.channel)
        self.transfer_stub = chatbot_pb2_grpc.TransferStub(self.channel)
        self.end_chat_stub = chatbot_pb2_grpc.EndChatStub(self.channel)

        self.console = Console()

    def insert_update_user_state(self, user_state_data):
        request = chatbot_pb2.UserState(**user_state_data)
        try:
            response = self.user_state_stub.InsertUpdateUserState(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar InsertUpdateUserState: {response.message}",
                    style="bold red",
                )
            return response
        except grpc.RpcError as e:
            self.console.print(
                f"Erro ao chamar InsertUpdateUserState: {e}", style="bold red"
            )
            return None

    def delete_user_state(self, chat_id_data):
        request = chatbot_pb2.ChatID(**chat_id_data)
        try:
            response = self.user_state_stub.DeleteUserState(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar SendMessage: {response.message}", style="bold red"
                )
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar DeleteUserState: {e}", style="bold red")
            return None

    def get_user_state(self, chat_id_data):
        request = chatbot_pb2.ChatID(**chat_id_data)
        try:
            response = self.user_state_stub.GetUserState(request)
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar GetUserState: {e}", style="bold red")
            return None

    def send_message(self, message_data):
        # print(json.dumps(message_data))

        request = chatbot_pb2.Message(**message_data)

        try:
            response = self.send_message_stub.SendMessage(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar SendMessage: {response.message}", style="bold red"
                )
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar SendMessage: {e}", style="bold red")
            return None

    def send_image(self, message_data):
        # print(json.dumps(message_data))

        request = chatbot_pb2.FileMessage(**message_data)

        try:
            response = self.send_message_stub.SendImage(request)
            if not response.status and response.message != "arquivo não encontrado":
                self.console.print(
                    f"Erro ao chamar SendImage: {response.message}", style="bold red"
                )
            elif response.message == "arquivo não encontrado":
                print("Arquivo não encontrado, Carregando arquivo...")
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar SendImage: {e}", style="bold red")
            return None

    def upload_file(self, file_data):
        request = chatbot_pb2.UploadFileRequest(**file_data)
        try:
            response = self.send_message_stub.UploadFile(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar UploadFile: {response.message}", style="bold red"
                )
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar UploadFile: {e}", style="bold red")
            return None

    def transfer_to_human(self, transfer_request_data):
        request = chatbot_pb2.TransferToHumanRequest(**transfer_request_data)
        try:
            response = self.transfer_stub.TransferToHuman(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar SendMessage: {response.message}", style="bold red"
                )
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar TransferToHuman: {e}", style="bold red")
            return None

    def transfer_to_menu(self, transfer_request_data):
        request = chatbot_pb2.TransferToMenuRequest(**transfer_request_data)
        try:
            response = self.transfer_stub.TransferToMenu(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar TransferToMenu: {response.message}",
                    style="bold red",
                )
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar TransferToMenu: {e}", style="bold red")
            return None

    def end_chat(self, end_chat_request_data):
        request = chatbot_pb2.EndChatRequest(**end_chat_request_data)
        try:
            response = self.end_chat_stub.EndChat(request)
            if not response.status:
                self.console.print(
                    f"Erro ao chamar SendMessage: {response.message}", style="bold red"
                )
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar EndChat: {e}", style="bold red")
            return None

    def get_campaign_id(self, campaign_name):
        request = chatbot_pb2.CampaignName(**campaign_name)
        try:
            response = self.transfer_stub.GetCampaignID(request)
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar GetCampaignID: {e}", style="bold red")
            return None

    def get_all_campaigns(self):
        request = chatbot_pb2.Void()
        try:
            response = self.transfer_stub.GetAllCampaigns(request)
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar GetAllCampaigns: {e}", style="bold red")
            return None

    def get_tabulation_id(self, tabulation_name):
        request = chatbot_pb2.TabulationName(**tabulation_name)
        try:
            response = self.end_chat_stub.GetTabulationID(request)
            return response
        except grpc.RpcError as e:
            self.console.print(f"Erro ao chamar GetTabulationID: {e}", style="bold red")
            return None

    def get_all_tabulations(self):
        request = chatbot_pb2.Void()
        try:
            response = self.end_chat_stub.GetAllTabulations(request)
            return response
        except grpc.RpcError as e:
            self.console.print(
                f"Erro ao chamar GetAllTabulations: {e}", style="bold red"
            )
            return None
