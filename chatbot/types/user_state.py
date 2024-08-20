from abc import ABC, abstractmethod


class UserState(ABC):
    @abstractmethod
    def get_menu(self, customer_id: str):
        pass

    @abstractmethod
    def set_menu(self, customer_id: str, menu: str):
        pass


class SimpleUserState(UserState):
    def __init__(self):
        self.states = {}

    def get_menu(self, customer_id: str) -> str:
        menu = self.states.get(customer_id, 'START')
        if menu == 'START':
            self.set_menu(customer_id, menu)
        return menu

    def set_menu(self, customer_id: str, menu: str|None=None) -> str:
        if menu:
            self.states[customer_id] = menu.upper()
