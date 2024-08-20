import os


class Credential:
    """
    Classe para gerenciar credenciais de usuário e senha, com suporte a variáveis de ambiente.
    """

    def __init__(self, username: str | None = None, password: str | None = None):
        """
        Inicializa a classe Credential com um nome de usuário e senha.

        Args:
            username (str | None): O nome de usuário. Pode ser None se for carregado de uma variável de ambiente.
            password (str | None): A senha do usuário. Pode ser None se for carregada de uma variável de ambiente.
        """
        self.__username = username
        self.__password = password

    @property
    def password(self) -> str:
        """
        Retorna a senha do usuário.

        Raises:
            ValueError: Se a senha não estiver definida.

        Returns:
            str: A senha do usuário.
        """
        if not self.__password:
            raise ValueError('Senha vazia!')
        return self.__password

    @property
    def username(self) -> str:
        """
        Retorna o nome de usuário.

        Raises:
            ValueError: Se o nome de usuário não estiver definido.

        Returns:
            str: O nome de usuário.
        """
        if not self.__username:
            raise ValueError('Usuário vazio!')
        return self.__username

    @classmethod
    def load_dotenv(cls, user_env: str = 'CHATBOT_USER', pass_env: str = 'CHATBOT_PASS') -> 'Credential':
        """
        Carrega as credenciais de variáveis de ambiente e retorna uma instância da classe Credential.

        Args:
            user_env (str): Nome da variável de ambiente que armazena o nome de usuário. Padrão é 'CHATBOT_USER'.
            pass_env (str): Nome da variável de ambiente que armazena a senha. Padrão é 'CHATBOT_PASS'.

        Raises:
            ValueError: Se o nome de usuário ou a senha não estiverem definidas nas variáveis de ambiente.

        Returns:
            Credential: Uma instância da classe Credential com as credenciais carregadas.
        """
        username = os.getenv(user_env)
        password = os.getenv(pass_env)

        if not username or not password:
            raise ValueError('Corrija as variáveis de ambiente!')

        return cls(username=username, password=password)
