from abc import ABC, abstractmethod


class UserState(ABC):
    """
    Classe abstrata para gerenciar o estado do usuário no fluxo do chatbot.

    Esta classe define a interface para implementar o gerenciamento de estado do usuário, incluindo métodos para obter e definir o menu atual do usuário.
    """

    @abstractmethod
    def get_menu(self, customer_id: str) -> str:
        """
        Retorna o menu atual para o ID de cliente fornecido.

        Args:
            customer_id (str): O ID do cliente.

        Returns:
            str: O menu atual associado ao cliente.
        """
        pass

    @abstractmethod
    def set_menu(self, customer_id: str, menu: str) -> None:
        """
        Define o menu atual para o ID de cliente fornecido.

        Args:
            customer_id (str): O ID do cliente.
            menu (str): O menu a ser definido para o cliente.
        """
        pass
    
    @abstractmethod
    def delete_menu(self, customer_id: str) -> None:
        """
        Deleta o menu atual para o ID de cliente fornecido.

        Args:
            customer_id (str): O ID do cliente.
        """
        pass


class SimpleUserState(UserState):
    """
    Implementação simples de UserState que armazena o estado do usuário em um dicionário em memória.

    Atributos:
        states (dict): Dicionário que armazena o estado de menu atual para cada cliente.
    """

    def __init__(self):
        """
        Inicializa o estado do usuário com um dicionário vazio.
        """
        self.states = {}

    def get_menu(self, customer_id: str) -> str:
        """
        Retorna o menu atual para o ID de cliente fornecido. Se o cliente não tiver um menu definido, define 'start' como padrão.

        Args:
            customer_id (str): O ID do cliente.

        Returns:
            str: O menu atual associado ao cliente.
        """
        menu = self.states.get(customer_id, 'start')
        if menu == 'start':
            self.set_menu(customer_id, menu)
        return menu

    def set_menu(self, customer_id: str, menu: str | None = None) -> None:
        """
        Define o menu atual para o ID de cliente fornecido. Converte o nome do menu para maiúsculas.

        Args:
            customer_id (str): O ID do cliente.
            menu (str | None): O menu a ser definido para o cliente. Se None, não faz nenhuma alteração.
        """
        if menu:
            self.states[customer_id] = menu.lower()

    def delete_menu(self, customer_id: str) -> None:
        """
        Deleta o menu atual para o ID de cliente fornecido.

        Args:
            customer_id (str): O ID do cliente.
        """
        if customer_id in self.states:
            self.states.pop(customer_id)