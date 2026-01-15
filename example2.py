import asyncio
from chatgraph import UserState, ChatID, Menu
import logging


def example_user_state() -> UserState:
    user_state = UserState(
        chat_id=ChatID('chat_123', 'prevencao-palavra'),
        menu=Menu(name='prevencao-palavra'),
        platform='voll',
        observation='{"key": "value"}',
    )

    return user_state


async def main():
    us = example_user_state()
    await us.insert()


logging.basicConfig(level=logging.INFO)
logging.info('Teste')
asyncio.run(main())
logging.info('Teste2')
