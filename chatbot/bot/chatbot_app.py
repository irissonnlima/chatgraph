import inspect
import json
from functools import wraps
from logging import debug

import pika
import pika.exceptions

from ..auth.credentials import Credential
from ..error.chatbot_error import ChatbotError, ChatbotMessageError
from ..types.message_types import Message
from ..types.user_state import SimpleUserState, UserState
from .chatbot_router import ChatbotRouter


class ChatbotApp:
    def __init__(
        self,
        amqp_url: str,
        queue_consume: str,
        credentials: Credential,
        user_state: UserState,
        prefetch_count: int = 1,
        virtual_host: str = '/',
    ):
        self.__virtual_host = virtual_host
        self.__prefetch_count = prefetch_count
        self.__user_state = user_state
        self.__queue_consume = queue_consume
        self.__amqp_url = amqp_url
        self.__credentials = pika.PlainCredentials(
            credentials.username, credentials.password
        )
        self.__routes = {}

    def include_router(self, router: ChatbotRouter, prefix: str):
        if 'START' not in router.routes.keys():
            raise ChatbotError('Erro ao incluir rota, START não encontrado!')

        prefixed_routes = {
            (
                f'START{prefix.upper()}'
                if key.upper() == 'START'
                else f'START{prefix.upper()}{key.upper()}'
            ): value
            for key, value in router.routes.items()
        }
        self.__routes.update(prefixed_routes)

    def route(self, state: str, default_message: str):
        def decorator(func):
            params = dict()
            signature = inspect.signature(func)
            output_param = signature.return_annotation

            for name, param in signature.parameters.items():
                param_type = (
                    param.annotation
                    if param.annotation != inspect.Parameter.empty
                    else 'Any'
                )
                params[param_type] = name
                debug(f'Parameter: {name}, Type: {param_type}')

            if Message not in params.keys():
                raise ChatbotError(
                    'Função não recebe Message, parâmetro obrigatório!'
                )

            self.__routes[state.upper()] = {
                'function': func,
                'default_message': default_message,
                'params': params,
                'return': output_param,
            }

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def start(self):
        try:  # Verificar se recursão não vai estourar
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.__amqp_url,
                    virtual_host=self.__virtual_host,
                    credentials=self.__credentials,
                )
            )
            channel = connection.channel()

            channel.basic_qos(prefetch_count=self.__prefetch_count)
            channel.basic_consume(
                queue=self.__queue_consume,
                on_message_callback=self.on_request,
            )

            debug('[x] Aguardando solicitações RPC')
            channel.start_consuming()
        except pika.exceptions.StreamLostError as e:
            debug(e)
            self.start()

    def on_request(self, ch, method, props, body):
        message = body.decode()
        response = self.process_message(message)

        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id
            ),
            body=str(response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def process_message(self, message: str):
        data = json.loads(message)
        message_imported = self.__transform_message(data)

        customer_id = message_imported.customer_id

        menu = self.__user_state.get_menu(customer_id)
        handler = self.__routes.get(menu, None)

        if not handler:
            raise ChatbotMessageError(
                customer_id, f'Rota não encontrada para {menu}!'
            )
        func = handler['function']
        message_name = handler['params'].get(Message)
        user_state_name = handler['params'].get(UserState, None)

        kwargs = {message_name: message_imported}
        if user_state_name:
            kwargs[user_state_name] = SimpleUserState(
                menu, list(self.__routes.keys())
            )
        return func(**kwargs)

    def __transform_message(self, message: dict) -> Message:
        return Message(
            type=message.get('type', ''),
            text=message.get('text', ''),
            customer_id=message.get('customer_id', ''),
            channel=message.get('channel', ''),
            customer_phone=message.get('customer_phone', ''),
            company_phone=message.get('company_phone', ''),
            status=message.get('status'),
        )
