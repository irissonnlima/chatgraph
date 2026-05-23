# Plano de Implementação — AI Agents no chatgraph

## Contexto

Adição de suporte nativo a Agentes de IA no chatgraph, permitindo que projetos
clientes integrem LLMs com **structured outputs**, **function calling** e
**embeddings/RAG** sem sair do padrão de rotas já existente.

Provider LLM: **OpenRouter** (API compatível com OpenAI).  
Biblioteca principal: **Pydantic AI** (`pydantic-ai`).

---

## Estrutura de pastas

```
chatgraph/
  agent/
    __init__.py
    ai_agent.py           # AIAgent — classe pública principal
    tool.py               # @tool decorator — function calling
    model.py              # get_model() singleton — interno
    embeddings.py         # EmbeddingsClient + LocalEmbeddingsClient
    embeddings_factory.py # cria client por EMBEDDING_PROVIDER do .env
    vector_store.py       # VectorStore in-memory com cosine similarity
```

---

## Arquivos novos

### `agent/model.py` (interno)

Singleton do modelo LLM. Lê `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` e
`AGENT_MODEL` do `.env`. Compartilhado por todos os `AIAgent` da aplicação.

```python
def get_model(override: str | None = None) -> OpenAIModel: ...
```

### `agent/ai_agent.py` (público)

Classe principal. O cliente instancia no próprio projeto e passa para
`@router.route(agent=...)`.

```python
class AIAgent:
    def __init__(
        self,
        system_prompt: str,
        result_type: Type[BaseModel] | Type[str] = str,
        tools: list[Callable] = [],
        model: str | None = None,   # override do AGENT_MODEL
    ): ...

    async def run(self, message: str, deps=None) -> result_type: ...
```

- `result_type`: modelo Pydantic para **structured output**. Se `str`, retorna
  texto livre.
- `tools`: lista de funções decoradas com `@tool` para **function calling**.
- `model`: permite cada agente usar um modelo diferente do padrão global.
- Lazy init — o `Agent` do Pydantic AI só é construído na primeira chamada.

### `agent/tool.py` (público)

Decorator que registra uma função como tool do agente (function calling).

```python
def tool(description: str): ...
```

### `agent/embeddings.py` (público)

Dois clients intercambiáveis:

| Classe | Provider | Custo |
|---|---|---|
| `EmbeddingsClient` | OpenAI API via httpx | $0.02/1M tokens |
| `LocalEmbeddingsClient` | fastembed (local, CPU) | zero |

```python
class EmbeddingsClient:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"): ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

class LocalEmbeddingsClient:
    def __init__(self, model: str = "paraphrase-multilingual-MiniLM-L12-v2"): ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

`LocalEmbeddingsClient` lança `ImportError` com mensagem clara se `fastembed`
não estiver instalado.

### `agent/embeddings_factory.py` (interno)

Seleciona o client de embeddings com base na variável `EMBEDDING_PROVIDER` do
`.env` (`"local"` padrão ou `"openai"`).

### `agent/vector_store.py` (público)

Busca semântica in-memory com cosine similarity via numpy. Adequado para bases
de até ~1000 documentos (FAQs, políticas, etc.).

```python
@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict

class VectorStore:
    def __init__(self, embedder: EmbeddingsClient | LocalEmbeddingsClient): ...
    async def add(self, texts: list[str], metadata: list[dict] = None): ...
    async def search(self, query: str, top_k: int = 3) -> list[SearchResult]: ...
```

---

## Arquivos modificados

### `chatbot_router.py` — 1 parâmetro novo

```python
# antes
def route(self, route_name: str, auth_level: str | None = None):

# depois
def route(self, route_name: str, auth_level: str | None = None, agent=None):
```

O `agent` é salvo no dicionário da rota junto com `function`, `params`, `return`
e `auth_level`.

### `chatbot_model.py` — injeção do resultado do agente

Em `process_message()`, após resolver o handler e antes de montar `kwargs`:

```python
agent = handler.get('agent')
if agent:
    agent_result = await agent.run(usercall.content_message)
    result_param = handler['params'].get(agent.result_type)
    if result_param:
        kwargs[result_param] = agent_result
```

O resultado é injetado **por tipo** na assinatura da função — mesmo mecanismo já
usado para `UserCall` e `Route`.

### `__init__.py` — novos exports públicos

```python
from .agent.ai_agent import AIAgent
from .agent.tool import tool
from .agent.embeddings import EmbeddingsClient, LocalEmbeddingsClient
from .agent.vector_store import VectorStore
```

### `pyproject.toml` — dependências

Obrigatórias (sempre instaladas com o chatgraph):
```toml
"pydantic-ai>=0.0.14",
"openai>=1.50.0",
```

> O pacote `openai` é o driver HTTP que o Pydantic AI usa internamente para
> qualquer API compatível com OpenAI — incluindo o OpenRouter. Não implica
> uso dos serviços da OpenAI.

Opcionais (instaladas sob demanda):
```toml
[project.optional-dependencies]
agent = ["pydantic-ai>=0.0.14", "openai>=1.50.0"]
embeddings = ["numpy>=1.26.0", "fastembed>=0.3.0"]
```

```bash
pip install chatgraph[agent]              # só agente
pip install chatgraph[agent,embeddings]   # agente + embeddings locais
```

---

## Variáveis de ambiente

```bash
# agente LLM (OpenRouter)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AGENT_MODEL=anthropic/claude-3.5-sonnet   # qualquer modelo do OpenRouter

# embeddings
EMBEDDING_PROVIDER=local          # "local" (padrão) ou "openai"
OPENAI_API_KEY=sk-...             # só se EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

---

## Exemplo de uso pelo cliente

```python
# agents.py — projeto do cliente
from chatgraph import AIAgent, tool, VectorStore, LocalEmbeddingsClient
from pydantic import BaseModel

class IntentResult(BaseModel):
    intent: str        # "saldo" | "extrato" | "cancelamento"
    confidence: float

_store = VectorStore(LocalEmbeddingsClient())
# await _store.add(["como ver saldo", "minha fatura", ...])

@tool("Busca resposta na base de conhecimento")
async def search_faq(question: str) -> str:
    results = await _store.search(question, top_k=3)
    return "\n".join(r.text for r in results)

triagem_agent = AIAgent(
    system_prompt="Classifique a intenção. Use a base de conhecimento.",
    result_type=IntentResult,
    tools=[search_faq],
)
```

```python
# routes.py — projeto do cliente
from chatgraph import ChatbotRouter, UserCall, RedirectResponse
from .agents import triagem_agent, IntentResult

router = ChatbotRouter()

@router.route("triagem", agent=triagem_agent)
async def triagem(call: UserCall, result: IntentResult) -> RedirectResponse:
    if result.confidence < 0.7:
        return RedirectResponse("fallback")
    return RedirectResponse(result.intent)
```

---

## Impacto e compatibilidade

| Métrica | Valor |
|---|---|
| Arquivos novos | 6 |
| Linhas modificadas nos arquivos existentes | ~15 |
| Novos símbolos públicos | `AIAgent`, `tool`, `EmbeddingsClient`, `LocalEmbeddingsClient`, `VectorStore` |
| Breaking changes | **zero** |
| Dependências obrigatórias novas | `pydantic-ai`, `openai` |
| Dependências opcionais novas | `fastembed`, `numpy` |

Toda a API pública atual permanece inalterada. O parâmetro `agent=` no
`@router.route()` é opcional — rotas sem agente continuam funcionando
exatamente como antes.
