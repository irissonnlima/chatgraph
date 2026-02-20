from chatgraph import UserState, ChatID, Menu
import json


def create_userstate(id) -> UserState:
    print('Creating user state for chat_id:', id)
    # id = str(id)
    user_state = UserState(
        chat_id=ChatID(id, 'prevencao-palavra'),
        menu=Menu(name='prevencao-palavra'),
        platform='voll',
        observation=json.dumps({'key': 'value'}),
        route='start.foo',
    )

    return user_state


def get_user_state(id) -> UserState | None:
    print('Retrieving user state for chat_id:', id)
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


def delete_userstate(userstate: UserState):
    userstate.delete()


if __name__ == '__main__':
    user = create_userstate(123)
    user.insert()
    retrieved_user = get_user_state(123)

    if not retrieved_user:
        print('User state not found')
    else:
        print(retrieved_user.to_dict())
        delete_userstate(retrieved_user)
