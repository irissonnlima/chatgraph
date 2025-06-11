import os
import grpc
import json

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

    def insert_update_user_state(self, user_state_data):
        request = chatbot_pb2.UserState(**user_state_data)
        try:
            response = self.user_state_stub.InsertUpdateUserState(request)
            if not response.status:
                print(f"Erro ao chamar SendMessage: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar InsertUpdateUserState: {e}")
            return None

    def delete_user_state(self, chat_id_data):
        request = chatbot_pb2.ChatID(**chat_id_data)
        try:
            response = self.user_state_stub.DeleteUserState(request)
            if not response.status:
                print(f"Erro ao chamar SendMessage: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar DeleteUserState: {e}")
            return None

    def get_user_state(self, chat_id_data):
        request = chatbot_pb2.ChatID(**chat_id_data)
        try:
            response = self.user_state_stub.GetUserState(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar GetUserState: {e}")
            return None

    def send_message(self, message_data):
        # print(json.dumps(message_data))

        request = chatbot_pb2.Message(**message_data)

        try:
            response = self.send_message_stub.SendMessage(request)
            if not response.status:
                print(f"Erro ao chamar SendMessage: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar SendMessage: {e}")
            return None

    def send_image(self, message_data):
        # print(json.dumps(message_data))

        request = chatbot_pb2.FileMessage(**message_data)

        try:
            response = self.send_message_stub.SendImage(request)
            if not response.status and response.message != "arquivo não encontrado":
                print(f"Erro ao chamar SendImage: {response.message}")
            elif response.message == "arquivo não encontrado":
                print("Arquivo não encontrado, Carregando arquivo...")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar SendImage: {e}")
            return None

    def upload_file(self, file_data):
        request = chatbot_pb2.UploadFileRequest(**file_data)
        try:
            response = self.send_message_stub.UploadFile(request)
            if not response.status:
                print(f"Erro ao chamar UploadFile: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar UploadFile: {e}")
            return None

    def transfer_to_human(self, transfer_request_data):
        request = chatbot_pb2.TransferToHumanRequest(**transfer_request_data)
        try:
            response = self.transfer_stub.TransferToHuman(request)
            if not response.status:
                print(f"Erro ao chamar SendMessage: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar TransferToHuman: {e}")
            return None

    def transfer_to_menu(self, transfer_request_data):
        request = chatbot_pb2.TransferToMenuRequest(**transfer_request_data)
        try:
            response = self.transfer_stub.TransferToMenu(request)
            if not response.status:
                print(f"Erro ao chamar TransferToMenu: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar TransferToMenu: {e}")
            return None

    def end_chat(self, end_chat_request_data):
        request = chatbot_pb2.EndChatRequest(**end_chat_request_data)
        try:
            response = self.end_chat_stub.EndChat(request)
            if not response.status:
                print(f"Erro ao chamar SendMessage: {response.message}")
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar EndChat: {e}")
            return None

    def get_campaign_id(self, campaign_name):
        request = chatbot_pb2.CampaignName(**campaign_name)
        try:
            response = self.transfer_stub.GetCampaignID(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar GetCampaignID: {e}")
            return None

    def get_all_campaigns(self):
        request = chatbot_pb2.Void()
        try:
            response = self.transfer_stub.GetAllCampaigns(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar GetAllCampaigns: {e}")
            return None

    def get_tabulation_id(self, tabulation_name):
        request = chatbot_pb2.TabulationName(**tabulation_name)
        try:
            response = self.end_chat_stub.GetTabulationID(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar GetTabulationID: {e}")
            return None

    def get_all_tabulations(self):
        request = chatbot_pb2.Void()
        try:
            response = self.end_chat_stub.GetAllTabulations(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao chamar GetAllTabulations: {e}")
            return None
