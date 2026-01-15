import asyncio
from chatgraph import UserState, ChatID, Menu
import logging


def example_user_state() -> UserState:
    user_state = UserState(
        chat_id=ChatID('chat_123', 'prevencao-palavra'),
        menu=Menu(name='prevencao-palavra'),
        platform='voll',
        observation='{"key": "value"}',
        route='start.foo'
    )

    return user_state


logging.info('Teste')
us = example_user_state()
us.insert()
us_existente = UserState.get_user_state(ChatID('chat_123', 'prevencao-palavra'))
print(us_existente.to_dict() if us_existente else 'No user state found')


logging.basicConfig(level=logging.INFO)
logging.info('Teste2')
