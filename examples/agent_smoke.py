"""Smoke test do agente SEM infraestrutura (RabbitMQ/chatbot-router).

Simula os turnos da conversa em memória e chama o OpenRouter de
verdade — valida prompt → structured output → ações localmente.

Requisitos no .env: OPENROUTER_API_KEY e AGENT_MODEL.

Uso:
    python examples/agent_smoke.py                     # REPL interativo
    python examples/agent_smoke.py "quero ver pedido"  # um turno só
"""

import asyncio
import logging
import sys
from datetime import datetime
from types import SimpleNamespace

from pydantic import BaseModel

from chatgraph import (
    Agent,
    EndChatResponse,
    MenuInfo,
    Message,
    OpenRouterClient,
    RedirectResponse,
    Route,
    TransferToMenu,
    execute_single_agent,
)
from chatgraph.history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)
from chatgraph.history.keys import generate_idempotency_key
from chatgraph.history.store import MemoryHistoryStore
from chatgraph.models.userstate import AuthLevel

MAX_REDIRECTS = 5

ROUTE_INFOS = [
    {
        'name': 'start',
        'description': (
            'Triage route. Understand what the user wants. For order '
            'lookup, redirect to buscar_pedido. For anything you '
            'cannot solve, transfer to the humano menu.'
        ),
        'ai_visible': True,
    },
    {
        'name': 'buscar_pedido',
        'description': (
            'Order lookup — collect cpf and numero_pedido from the '
            'user. When both are collected, call the consultar_pedido '
            "tool with result_key='dados_pedido'. After the tool "
            'result is in observation, redirect to exibir_pedido.'
        ),
        'ai_visible': True,
    },
    {
        'name': 'exibir_pedido',
        'description': (
            'Present the order data from observation.dados_pedido '
            'with friendly formatting, then ask if the user needs '
            'anything else.'
        ),
        'ai_visible': True,
    },
]


class PedidoObs(BaseModel):
    cpf: str = ''
    numero_pedido: str = ''


class FakeUserCall:
    """Superfície mínima de UserCall, com estado em memória."""

    def __init__(self) -> None:
        self.route = 'start'
        self.content_message = ''
        self._observation: dict = {}
        self._store = MemoryHistoryStore()
        self.user = SimpleNamespace(
            data=SimpleNamespace(name='Rodrigo'),
            identity=SimpleNamespace(auth_level=AuthLevel.READ),
        )
        self.user_id = 'smoke-user'
        self.company_id = 'smoke-company'
        self.session_id = 1
        self.logger = logging.getLogger('agent_smoke')

    @property
    def observation(self) -> dict:
        return self._observation

    @property
    def history(self) -> MemoryHistoryStore:
        return self._store

    async def add_observation(self, observation: dict) -> None:
        self._observation.update(observation)

    async def record_text(
        self,
        role: HistoryRole,
        event: HistoryEventType,
        text: str,
    ) -> None:
        key = generate_idempotency_key(
            f'{self.user_id}:{self.company_id}',
            self.session_id,
            role.value,
            event.value,
            self.route,
            f'{datetime.now().isoformat()}|{text}',
        )
        await self._store.record(
            HistoryEntry(
                idempotency_key=key,
                chat_id=f'{self.user_id}:{self.company_id}',
                session_id=self.session_id,
                role=role,
                event_type=event,
                timestamp=datetime.now(),
                route=self.route,
                message={'text_message': {'detail': text}},
            )
        )


def build_agent() -> Agent:
    return Agent.load_dotenv(
        OpenRouterClient.load_dotenv(),
        system_prompt=(
            'Você é o assistente virtual da loja. Seja simpático, '
            'direto e sempre responda em português do Brasil.'
        ),
        observation_model=PedidoObs,
        menus=[
            MenuInfo(
                name='humano',
                route='start',
                description='Atendimento humano para casos complexos.',
                message='Transferindo você para um atendente...',
            ),
        ],
    )


async def run_turn(
    usercall: FakeUserCall, agent: Agent, depth: int = 0
) -> None:
    """Executa um turno e aplica os retornos ao estado em memória,
    espelhando o __process_func_response do pipeline."""
    route = Route(
        usercall.route,
        [info['name'] for info in ROUTE_INFOS],
        infos=ROUTE_INFOS,
    )
    returns = await execute_single_agent(usercall, route, agent)

    if returns is None:
        print(f'   [permanece na rota: {usercall.route}]')
        return

    for item in returns:
        if isinstance(item, Message):
            print(f'🤖 {item.text_message.detail}')
            for button in item.buttons:
                print(f'   [botão: {button.title}]')
            await usercall.record_text(
                HistoryRole.BOT,
                HistoryEventType.MESSAGE_OUT,
                item.text_message.detail,
            )
        elif isinstance(item, RedirectResponse):
            usercall.route += f'.{item.route}'
            print(f'   [redirect → {usercall.route}]')
            if depth < MAX_REDIRECTS:
                await run_turn(usercall, agent, depth + 1)
        elif isinstance(item, Route):
            usercall.route += f'.{item.current_node}'
            print(f'   [next_route → {usercall.route}]')
        elif isinstance(item, EndChatResponse):
            print(f'   [end_session: {item.end_chat_id}]')
        elif isinstance(item, TransferToMenu):
            print(
                f'   [transfer_menu → {item.menu!r} '
                f'(rota {item.route!r}): {item.user_message}]'
            )


async def main() -> None:
    logging.getLogger().setLevel(logging.WARNING)
    agent = build_agent()

    @agent.tool(
        description=(
            'Consulta um pedido pelo CPF do cliente e número do pedido.'
        ),
        parameters={
            'type': 'object',
            'properties': {
                'cpf': {'type': 'string'},
                'numero_pedido': {'type': 'string'},
            },
            'required': ['cpf', 'numero_pedido'],
        },
    )
    async def consultar_pedido(cpf: str, numero_pedido: str) -> dict:
        print(
            f'   [tool consultar_pedido chamada: '
            f'cpf={cpf!r} pedido={numero_pedido!r}]'
        )
        return {
            'numero': numero_pedido,
            'status': 'Entregue',
            'previsao': '2026-08-20',
        }

    usercall = FakeUserCall()
    single_message = sys.argv[1] if len(sys.argv) > 1 else None

    print(f'Modelo: {agent.model} | rota inicial: {usercall.route}')
    print('Digite sua mensagem (ou "sair").\n')

    while True:
        if single_message is not None:
            text = single_message
            print(f'👤 {text}')
        else:
            try:
                text = input('👤 ').strip()
            except (EOFError, KeyboardInterrupt):
                break
        if not text or text.lower() == 'sair':
            break

        usercall.content_message = text
        await usercall.record_text(
            HistoryRole.USER, HistoryEventType.MESSAGE_IN, text
        )
        await run_turn(usercall, agent)
        print(
            f'   [observation: {usercall.observation} '
            f'| rota: {usercall.route}]\n'
        )

        if single_message is not None:
            break


if __name__ == '__main__':
    asyncio.run(main())
