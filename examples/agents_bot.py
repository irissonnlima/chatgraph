"""Exemplo de bot com agente de IA (protocolo single-agent).

Espelha ``chatgraph-go/examples/agents/main.go`` com tools mock.

Requisitos:
    pip install chatgraph[agent]
    # .env: RABBIT_*, ROUTER_URL/TOKEN, OPENROUTER_API_KEY, AGENT_MODEL

Como funciona:
- A ``description`` de cada rota é o prompt de comportamento daquela
  rota — o framework a injeta no system prompt e o LLM a lê como
  instrução. ``ai_visible=True`` expõe a rota ao roteamento do agente.
- O handler chama ``agent.execute(call, route)`` e devolve o retorno
  direto ao pipeline. Handlers com agente devem ser ``async``.
- Tools locais são registradas com ``@agent.tool`` e chamadas pelo
  modelo via ação declarativa ``call_tool``; o resultado entra na
  observation da sessão sob ``result_key``.
"""

from pydantic import BaseModel

from chatgraph import (
    Agent,
    ChatbotApp,
    MenuInfo,
    OpenRouterClient,
    Route,
    UserCall,
)
from chatgraph.history.store import MemoryHistoryStore


class PedidoObs(BaseModel):
    """Campos que o agente pode coletar (gera o observation_schema)."""

    cpf: str = ''
    numero_pedido: str = ''


# Modelo e parâmetros vêm do .env (AGENT_MODEL obrigatório; ver
# .env.example para os opcionais AGENT_TEMPERATURE etc.).
agent = Agent.load_dotenv(
    OpenRouterClient.load_dotenv(),
    system_prompt=(
        'Você é o assistente virtual da loja. Seja simpático, direto '
        'e sempre responda em português do Brasil.'
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


@agent.tool(
    description='Consulta um pedido pelo CPF do cliente e número do pedido.',
    parameters={
        'type': 'object',
        'properties': {
            'cpf': {'type': 'string', 'description': 'CPF do cliente'},
            'numero_pedido': {
                'type': 'string',
                'description': 'Número do pedido',
            },
        },
        'required': ['cpf', 'numero_pedido'],
    },
)
async def consultar_pedido(cpf: str, numero_pedido: str) -> dict:
    # Mock: em produção, chame a API real.
    return {
        'numero': numero_pedido,
        'status': 'Entregue',
        'previsao': '2026-08-20',
    }


app = ChatbotApp(history_store=MemoryHistoryStore())


@app.route(
    'start',
    description=(
        'Triage route. Understand what the user wants. For order '
        'lookup, redirect to buscar_pedido. For anything you cannot '
        'solve, transfer to the humano menu.'
    ),
    ai_visible=True,
)
async def start(call: UserCall, route: Route):
    return await agent.execute(call, route)


@app.route(
    'buscar_pedido',
    description=(
        'Order lookup — collect cpf and numero_pedido from the user. '
        'When both are collected, call the consultar_pedido tool with '
        "result_key='dados_pedido'. After the tool result is in "
        'observation, redirect to exibir_pedido.'
    ),
    ai_visible=True,
)
async def buscar_pedido(call: UserCall, route: Route):
    return await agent.execute(call, route)


@app.route(
    'exibir_pedido',
    description=(
        'Present the order data from observation.dados_pedido with '
        'friendly formatting, then ask if the user needs anything '
        'else.'
    ),
    ai_visible=True,
)
async def exibir_pedido(call: UserCall, route: Route):
    return await agent.execute(call, route)


if __name__ == '__main__':
    app.start()
