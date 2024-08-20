import os


class Credential:
    def __init__(
        self, username: str | None = None, password: str | None = None
    ):
        self.__username = username
        self.__password = password

    @property
    def password(self):
        if not self.__password:
            raise ValueError('Senha vazia!')
        return self.__password

    @property
    def username(self):
        if not self.__username:
            raise ValueError('Usuário vazio!')
        return self.__username

    @classmethod
    def dot_env_credentials(
        cls, user_env: str = 'CHATBOT_USER', pass_env: str = 'CHATBOT_PASS'
    ) -> 'Credential':
        username = os.getenv(user_env)
        password = os.getenv(pass_env)

        if not username or not password:
            raise ValueError('Corrija as variáveis de ambiente!')

        return cls(username=username, password=password)
