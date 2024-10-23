import os
import grpc
import chatgraph.pb.userstate_pb2 as userstate_pb2
import chatgraph.pb.userstate_pb2_grpc as userstate_pb2_grpc

import chatgraph.pb.voll_pb2 as whatsapp_pb2
import chatgraph.pb.voll_pb2_grpc as whatsapp_pb2_grpc

class WhatsappServiceClient:
    def __init__(self, grpc_uri=None):
        
        self.grpc_uri = grpc_uri
        
        if not grpc_uri:
            self.grpc_uri = os.getenv('GRPC_URI')
        
        if not self.grpc_uri:
            raise ValueError("A variável de ambiente 'GRPC_URI' não está definida.")
        
        # Cria o canal gRPC
        self.channel = grpc.insecure_channel(self.grpc_uri)
        
        # Cria o stub (client) para o serviço gRPC
        self.stub = whatsapp_pb2_grpc.MessageServiceStub(self.channel)

    def send_button(self, message_data):
        # Cria o request para o método SendButton
        request = whatsapp_pb2.MessageRequest(**message_data)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.SendButton(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC SendButton: {e}")
            return None

    def send_list(self, message_data):
        # Cria o request para o método SendList
        request = whatsapp_pb2.MessageRequest(**message_data)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.SendList(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC SendList: {e}")
            return None

    def send_text(self, message_data):
        # Cria o request para o método SendText
        request = whatsapp_pb2.MessageRequest(**message_data)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.SendText(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC SendText: {e}")
            return None

class UserStateServiceClient:
    def __init__(self, grpc_uri=None):
        
        self.grpc_uri = grpc_uri
        
        if not grpc_uri:
            self.grpc_uri = os.getenv('GRPC_URI')
        
        if not self.grpc_uri:
            raise ValueError("A variável de ambiente 'GRPC_URI' não está definida.")
        
        # Cria o canal gRPC
        self.channel = grpc.insecure_channel(self.grpc_uri)
        
        # Cria o stub (client) para o serviço gRPC
        self.stub = userstate_pb2_grpc.UserStateServiceStub(self.channel)

    def select_user_state(self, user_id):
        # Cria o request para o método SelectUserState
        request = userstate_pb2.UserStateId(user_id=user_id)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.SelectUserState(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC SelectUserState: {e}")
            return None

    def insert_user_state(self, user_state_data):
        # Cria o request para o método InsertUserState
        request = userstate_pb2.UserState(**user_state_data)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.InsertUserState(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC InsertUserState: {e}")
            return None

    def update_user_state(self, user_state_data):
        # Cria o request para o método UpdateUserState
        request = userstate_pb2.UserState(**user_state_data)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.UpdateUserState(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC UpdateUserState: {e}")
            return None

    def delete_user_state(self, user_id):
        # Cria o request para o método DeleteUserState
        request = userstate_pb2.UserStateId(user_id=user_id)

        # Faz a chamada ao serviço gRPC
        try:
            response = self.stub.DeleteUserState(request)
            return response
        except grpc.RpcError as e:
            print(f"Erro ao fazer a requisição gRPC DeleteUserState: {e}")
            return None