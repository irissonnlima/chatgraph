from chatgraph import UserState, ChatID, Menu
import json


def create_userstate(id) -> UserState:
    user_state = UserState(
        chat_id=ChatID(id, 'prevencao-palavra'),
        menu=Menu(name='prevencao-palavra'),
        platform='voll',
        observation=json.dumps({'key': 'value'}),
        route='start.foo',
    )

    return user_state


def get_user_state(id) -> UserState | None:
    chat_id = ChatID(id, 'prevencao-palavra')
    user_state = UserState.get_user_state(chat_id)
    if not user_state:
        return None
    return user_state


def create_multiples_userstates():
    for i in range(100):
        print('Inserting user state for chat_id:', i)
        user_state = create_userstate(i)
        user_state.insert()
        print('Inserted user state: ')
        print(user_state.to_dict())
