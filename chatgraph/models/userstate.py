"""
Modelos de dados para gerenciamento de estado de usuário.

Este módulo contém as dataclasses que representam o estado do usuário
no sistema de chatbot, incluindo identificação, informações pessoais,
menu atual e metadados da sessão.
"""

import asyncio
import concurrent.futures
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from ..container.container import Container


class AuthLevel(Enum):
    BLOCKED = 'blocked'
    UNKNOWN = 'unknown'
    READ = 'read'
    WRITE = 'write'

    @classmethod
    def from_value(cls, value) -> 'AuthLevel':
        """Aceita string ('read', 'write', etc.) ou int (-1, 0, 1, 2)."""
        _int_map = {-1: cls.BLOCKED, 0: cls.UNKNOWN, 1: cls.READ, 2: cls.WRITE}
        if isinstance(value, int):
            return _int_map.get(value, cls.UNKNOWN)
        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                return cls.UNKNOWN
        return cls.UNKNOWN


@dataclass
class ChatID:
    """
    Identificador único do chat.

    Attributes:
        user_id: ID único do usuário
        company_id: ID da empresa/organização
    """

    user_id: str
    company_id: str

    def __post_init__(self):
        self.user_id = str(self.user_id)
        self.company_id = str(self.company_id)

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            'user_id': self.user_id,
            'company_id': self.company_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatID':
        """Cria instância a partir de dicionário."""
        return cls(
            user_id=data.get('user_id', ''),
            company_id=data.get('company_id', ''),
        )


@dataclass
class UserData:
    cpf: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    profile_photo_url: Optional[str] = None
    nickname: Optional[str] = None

    def to_dict(self) -> dict:
        data = {}
        if self.cpf is not None:
            data['cpf'] = self.cpf
        if self.name is not None:
            data['name'] = self.name
        if self.phone is not None:
            data['phone'] = self.phone
        if self.email is not None:
            data['email'] = self.email
        if self.profile_photo_url is not None:
            data['profile_photo_url'] = self.profile_photo_url
        if self.nickname is not None:
            data['nickname'] = self.nickname
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'UserData':
        return cls(
            cpf=data.get('cpf'),
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            profile_photo_url=data.get('profile_photo_url'),
            nickname=data.get('nickname'),
        )


@dataclass
class UserIdentity:
    cpf: Optional[str] = None
    device_id: Optional[str] = None
    hash_authorization: Optional[str] = None
    active: Optional[bool] = None
    auth_level: AuthLevel = AuthLevel.UNKNOWN
    auth_status: Optional[str] = None
    last_access_at: Optional[str] = None
    last_validation_at: Optional[str] = None
    consent_source: Optional[str] = None

    def to_dict(self) -> dict:
        data: dict = {'auth_level': self.auth_level.value}
        if self.cpf is not None:
            data['cpf'] = self.cpf
        if self.device_id is not None:
            data['device_id'] = self.device_id
        if self.hash_authorization is not None:
            data['hash_authorization'] = self.hash_authorization
        if self.active is not None:
            data['active'] = self.active
        if self.auth_status is not None:
            data['auth_status'] = self.auth_status
        if self.last_access_at is not None:
            data['last_access_at'] = self.last_access_at
        if self.last_validation_at is not None:
            data['last_validation_at'] = self.last_validation_at
        if self.consent_source is not None:
            data['consent_source'] = self.consent_source
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'UserIdentity':
        return cls(
            cpf=data.get('cpf'),
            device_id=data.get('device_id'),
            hash_authorization=data.get('hash_authorization'),
            active=data.get('active'),
            auth_level=AuthLevel.from_value(data.get('auth_level', 'unknown')),
            auth_status=data.get('auth_status'),
            last_access_at=data.get('last_access_at'),
            last_validation_at=data.get('last_validation_at'),
            consent_source=data.get('consent_source'),
        )


@dataclass
class UserInternal:
    matricula: Optional[str] = None
    cargo: Optional[str] = None
    filial: Optional[str] = None
    empresa: Optional[str] = None
    data_admissao: Optional[str] = None

    def to_dict(self) -> dict:
        data = {}
        if self.matricula is not None:
            data['matricula'] = self.matricula
        if self.cargo is not None:
            data['cargo'] = self.cargo
        if self.filial is not None:
            data['filial'] = self.filial
        if self.empresa is not None:
            data['empresa'] = self.empresa
        if self.data_admissao is not None:
            data['data_admissao'] = self.data_admissao
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'UserInternal':
        return cls(
            matricula=data.get('matricula'),
            cargo=data.get('cargo'),
            filial=data.get('filial'),
            empresa=data.get('empresa'),
            data_admissao=data.get('data_admissao'),
        )


@dataclass
class User:
    data: UserData = field(default_factory=UserData)
    identity: UserIdentity = field(default_factory=UserIdentity)
    internal: Optional[UserInternal] = None

    def to_dict(self) -> dict:
        result = {
            'data': self.data.to_dict(),
            'identity': self.identity.to_dict(),
        }
        if self.internal is not None:
            result['internal'] = self.internal.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        internal_data = data.get('internal')
        return cls(
            data=UserData.from_dict(data.get('data', {})),
            identity=UserIdentity.from_dict(data.get('identity', {})),
            internal=UserInternal.from_dict(internal_data) if internal_data else None,
        )


@dataclass
class Menu:
    """
    Informações do menu/departamento.

    Attributes:
        id: ID do menu (opcional)
        department_id: ID do departamento (opcional)
        name: Nome do menu (opcional)
        description: Descrição do menu (opcional)
        active: Status de ativação do menu (opcional)
    """

    id: Optional[int] = None
    department_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    protection_level: Optional[AuthLevel] = None

    def to_dict(self) -> dict:
        """Converte para dicionário, omitindo campos None."""
        data = {}
        if self.id is not None:
            data['id'] = self.id
        if self.department_id is not None:
            data['department_id'] = self.department_id
        if self.name is not None:
            data['name'] = self.name
        if self.description is not None:
            data['description'] = self.description
        if self.active is not None:
            data['active'] = self.active
        if self.protection_level is not None:
            data['protection_level'] = self.protection_level.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Menu':
        """Cria instância a partir de dicionário."""
        return cls(
            id=data.get('id'),
            department_id=data.get('department_id'),
            name=data.get('name'),
            description=data.get('description'),
            active=data.get('active'),
            protection_level=AuthLevel.from_value(data['protection_level']) if data.get('protection_level') is not None else None,
        )

    @classmethod
    def from_name(cls, name: str) -> 'Menu':
        """Cria instância a partir do nome do Menu."""
        return cls(name=name)


@dataclass
class UserState:
    """
    Estado completo do usuário no sistema.

    Attributes:
        chat_id: Identificador do chat (obrigatório)
        platform: Plataforma de comunicação (obrigatório)
        session_id: ID da sessão (opcional)
        menu: Menu atual (opcional)
        user: Informações do usuário (opcional)
        route: Rota atual no fluxo (opcional)
        direction_in: Indica se é mensagem de entrada (opcional)
        observation: Observações/contexto adicional (opcional)
        last_update: Data/hora da última atualização (opcional)
        dt_created: Data/hora de criação (opcional)
    """

    chat_id: ChatID
    platform: str
    session_id: Optional[int] = None
    menu: Optional[Menu] = field(default_factory=Menu)
    user: Optional[User] = field(default_factory=User)
    route: str = 'start'
    direction_in: Optional[bool] = None
    observation: Optional[str] = None
    last_update: Optional[str] = None
    dt_created: Optional[str] = None

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        data = {
            'chat_id': self.chat_id.to_dict(),
            'platform': self.platform,
        }

        if self.session_id is not None:
            data['session_id'] = self.session_id
        if self.menu is not None:
            data['menu'] = self.menu.to_dict()
        if self.user is not None:
            data['user'] = self.user.to_dict()
        if self.route is not None:
            data['route'] = self.route
        if self.direction_in is not None:
            data['direction_in'] = self.direction_in
        if self.observation is not None:
            data['observation'] = self.observation
        if self.last_update is not None:
            data['last_update'] = self.last_update
        if self.dt_created is not None:
            data['dt_created'] = self.dt_created

        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'UserState':
        """Cria instância a partir de dicionário."""
        chat_id_data = data.get('chat_id', {})
        menu_data = data.get('menu', {})
        user_data = data.get('user', {})

        return cls(
            session_id=data.get('session_id'),
            chat_id=ChatID.from_dict(chat_id_data),
            menu=Menu.from_dict(menu_data) if menu_data else Menu(),
            user=User.from_dict(user_data) if user_data else User(),
            route=data.get('route', 'start'),
            direction_in=data.get('direction_in'),
            observation=data.get('observation'),
            platform=data.get('platform', ''),
            last_update=data.get('last_update'),
            dt_created=data.get('dt_created'),
        )

    @property
    def observation_dict(self) -> dict:
        """Retorna a observação como dicionário."""

        if self.observation:
            try:
                return json.loads(self.observation)
            except json.JSONDecodeError:
                return {}
        return {}

    def insert(self) -> None:
        """Insere o estado do usuário no sistema via RouterHTTPClient."""
        try:
            # Executa a versão assíncrona de forma síncrona
            asyncio.run(self.insert_async())
        except RuntimeError:
            # Se já existe um loop rodando, usa run_in_executor
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.insert_async())
                    future.result()
            else:
                asyncio.run(self.insert_async())

    async def insert_async(self) -> None:
        """Insere o estado do usuário no sistema via RouterHTTPClient de forma assíncrona."""
        container = Container()
        router_client = container.get_router_client()
        try:
            async with router_client as rc:
                await rc.start_session(self)
        except Exception as e:
            print(f'Erro ao inserir UserState assíncrono: {e}')
            raise e

    @staticmethod
    def get_user_state(chat_id: ChatID) -> Optional['UserState']:
        """Recupera o estado do usuário de forma síncrona."""
        try:
            return asyncio.run(UserState.get_user_state_async(chat_id))
        except RuntimeError:
            # Se já existe um loop rodando, usa run_in_executor
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, UserState.get_user_state_async(chat_id)
                    )
                    return future.result()
            else:
                return asyncio.run(UserState.get_user_state_async(chat_id))

    @staticmethod
    async def get_user_state_async(chat_id: ChatID) -> Optional['UserState']:
        """Recupera o estado do usuário do sistema via RouterHTTPClient."""
        container = Container()
        router_client = container.get_router_client()
        try:
            async with router_client as rc:
                user_state = await rc.get_session_by_chat_id(chat_id)
                return user_state
        except Exception as e:
            print(f'Erro ao recuperar UserState: {e}')
            return None

    def delete(self) -> Optional['UserState']:
        """Recupera o estado do usuário de forma síncrona."""
        try:
            return asyncio.run(self.delete_async())
        except RuntimeError:
            # Se já existe um loop rodando, usa run_in_executor
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.delete_async())
                    return future.result()
            else:
                return asyncio.run(self.delete_async())

    async def delete_async(self) -> Optional['UserState']:
        """Recupera o estado do usuário do sistema via RouterHTTPClient."""
        container = Container()
        router_client = container.get_router_client()
        try:
            async with router_client as rc:
                end_action = await rc.get_end_action('voll_ended')
                result = await rc.end_chat(
                    self.chat_id, end_action, 'chatgraph-userstate'
                )
                return result
        except Exception as e:
            print(f'Erro ao recuperar UserState: {e}')
            return None
