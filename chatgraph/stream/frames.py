import json

HELLO = 'hello'
WELCOME = 'welcome'
DELIVER = 'deliver'
ACK = 'ack'
NACK = 'nack'
COMMAND = 'command'
COMMAND_RESULT = 'command_result'
GOAWAY = 'goaway'
PING = 'ping'
PONG = 'pong'
ERROR = 'error'

PROTOCOL_VERSION = '1.0'
CONNECT_PATH = '/menus/connect'


def encode(frame: dict) -> str:
    return json.dumps(frame, ensure_ascii=False, separators=(',', ':'))


def hello(menus: list[str], max_inflight: int) -> dict:
    return {
        'type': HELLO,
        'menus': menus,
        'version': PROTOCOL_VERSION,
        'max_inflight': max_inflight,
    }


def ack(delivery_id: str, msg_id: str) -> dict:
    return {'type': ACK, 'delivery_id': delivery_id, 'msg_id': msg_id}


def nack(delivery_id: str, msg_id: str, retryable: bool, error: str) -> dict:
    return {
        'type': NACK,
        'delivery_id': delivery_id,
        'msg_id': msg_id,
        'retryable': retryable,
        'error': error,
    }


def command(cmd_id: str, name: str, chat_id: dict, payload: dict) -> dict:
    return {
        'type': COMMAND,
        'cmd_id': cmd_id,
        'name': name,
        'chat_id': chat_id,
        'payload': payload,
    }


def ping() -> dict:
    return {'type': PING}
