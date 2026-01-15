import asyncio
from chatgraph import UserState, ChatID, Menu


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


asyncio.run(main())
