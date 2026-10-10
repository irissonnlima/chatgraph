"""Smoke test de generate_content: análise de dado interno, sem turno
de chat (sem UserCall, sem Route, sem AgentContext/menus/rotas).

Simula uma consulta a banco (mockada) e pede um insight estruturado à
IA sobre o resultado — chama o OpenRouter de verdade.

Requisitos no .env: OPENROUTER_API_KEY e AGENT_MODEL.

Uso:
    python examples/content_insight.py
"""

import asyncio
import json
import os

from dotenv import load_dotenv
from pydantic import BaseModel

from chatgraph import OpenRouterClient, generate_content


class VendasInsight(BaseModel):
    resumo: str
    tendencia: str
    produtos_em_alerta: list[str] = []


def buscar_vendas_do_mes() -> list[dict]:
    """Mock de uma consulta que, num bot real, viria do banco interno
    (não é uma mensagem de cliente)."""
    return [
        {'produto': 'Cimento CP-II', 'unidades': 1200, 'variacao_pct': -18},
        {'produto': 'Tijolo baiano', 'unidades': 8400, 'variacao_pct': 4},
        {'produto': 'Argamassa AC-I', 'unidades': 300, 'variacao_pct': -32},
    ]


async def main() -> None:
    load_dotenv()
    dados = buscar_vendas_do_mes()

    result = await generate_content(
        OpenRouterClient.load_dotenv(),
        model=os.environ['AGENT_MODEL'],
        content=json.dumps(dados, ensure_ascii=False),
        system_prompt=(
            'Você é um analista de vendas. Responda em português do '
            'Brasil. Aponte quedas relevantes como alerta.'
        ),
        response_model=VendasInsight,
    )

    print(f'Texto bruto: {result.text}\n')
    if result.data is not None:
        print(f'Resumo: {result.data.resumo}')
        print(f'Tendência: {result.data.tendencia}')
        print(f'Produtos em alerta: {result.data.produtos_em_alerta}')
    print(f'\nTokens usados: {result.usage.total_tokens}')


if __name__ == '__main__':
    asyncio.run(main())
