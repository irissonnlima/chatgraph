"""
Modelos de dados para gerenciamento de estado de usuário.

Este módulo contém as dataclasses que representam o estado do usuário
no sistema de chatbot, incluindo identificação, informações pessoais,
menu atual e metadados da sessão.
"""

from dataclasses import dataclass, field
from typing import Optional


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
class User:
    """
    Informações do usuário.

    Attributes:
        cpf: CPF do usuário (opcional)
        name: Nome do usuário (opcional)
        phone: Telefone do usuário (opcional)
        email: Email do usuário (opcional)
    """

    cpf: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> dict:
        """Converte para dicionário, omitindo campos None."""
        data = {}
        if self.cpf is not None:
            data['cpf'] = self.cpf
        if self.name is not None:
            data['name'] = self.name
        if self.phone is not None:
            data['phone'] = self.phone
        if self.email is not None:
            data['email'] = self.email
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Cria instância a partir de dicionário."""
        return cls(
            cpf=data.get('cpf'),
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
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
        )


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
    route: Optional[str] = None
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
            route=data.get('route'),
            direction_in=data.get('direction_in'),
            observation=data.get('observation'),
            platform=data.get('platform', ''),
            last_update=data.get('last_update'),
            dt_created=data.get('dt_created'),
        )
