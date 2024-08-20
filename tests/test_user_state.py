from chatbot.user_state import SimpleUserState


def test_simple_user_state_initialization():
    user_state = SimpleUserState()
    assert isinstance(user_state, SimpleUserState)


def test_get_menu_returns_default():
    user_state = SimpleUserState()
    customer_id = '123'
    assert user_state.get_menu(customer_id) == 'START'


def test_set_and_get_menu():
    user_state = SimpleUserState()
    customer_id = '123'
    user_state.set_menu(customer_id, 'MAIN')
    assert user_state.get_menu(customer_id) == 'MAIN'
