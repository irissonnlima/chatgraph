# Instruções do Projeto — chatgraph

## Agentes Disponíveis

Este projeto possui três agentes customizados. Antes de agir, identifique qual é o apropriado:

| Situação | Agente |
|----------|--------|
| Analisar uma demanda, planejar uma feature, decidir onde o código deve viver, questionar design, sugerir tecnologias | **Architect** |
| Implementar código especificado, escrever testes, refatorar, corrigir bugs em arquivos existentes | **Developer** |
| Revisar código implementado, validar convenções, verificar regras de negócio e cobertura de testes | **CodeReviewer** |

Quando o usuário descrever uma demanda nova em texto livre, delegue ao **Architect**.
Quando o usuário pedir implementação direta com escopo já definido, delegue ao **Developer**.
Quando o usuário pedir revisão de código ou o Developer concluir uma implementação, delegue ao **CodeReviewer**.

### Fluxo Completo

```
Usuário (demanda) → Architect (especificação) → Developer (implementação) → CodeReviewer (parecer)
```

- Se o CodeReviewer emitir 🚨 **CRÍTICO**: volta ao **Developer** para correção, depois nova revisão.
- Se emitir ⚠️ **CUIDADO** ou ✅ **ACEITO**: entrega ao usuário com o parecer anexado.

---

## Arquitetura

**Linguagem/Runtime**: Python 3.12+
**Framework**: Custom (aio-pika, httpx AsyncClient, gRPC, Typer)
**Padrão**: Layered Architecture — bot, models, services, types, container

```
chatgraph/
  auth/         # Credenciais e autenticação
  bot/          # ChatbotApp (orquestrador) + ChatbotRouter (registro de rotas)
  cli/          # Interface de linha de comando (Typer)
  container/    # Container singleton — gerencia RouterHTTPClient via .env
  error/        # ChatbotError, RouteError
  gRPC/         # gRPCCall — comunicação via gRPC (protobuf)
  logger/       # Logger estruturado (rich + logging)
  messages/     # MessageConsumer — consome RabbitMQ via aio-pika
  models/       # Dataclasses: UserState, Message, File, Button, actions, http_responses
  pb/           # Protobuf gerado (router.proto, router_pb2.py)
  services/     # RouterHTTPClient — httpx AsyncClient para o backend
  types/        # Tipos de domínio: UserCall, Route, EndTypes, BackgroundTask
tests/
  unit/         # Testes unitários com pytest + respx
  integration/  # Testes de integração
```

### Camadas e Responsabilidades

- **`bot/`** — Orquestração principal. `ChatbotApp` despacha para a rota correta. `ChatbotRouter` registra rotas via `@router.route("nome")`.
- **`types/`** — `UserCall` (parâmetro padrão das rotas), `Route`, `EndTypes` (respostas possíveis), `BackgroundTask`.
- **`models/`** — Dataclasses de dados: `UserState`, `Message`, `File`, `Button`, `actions`, `http_responses`.
- **`services/`** — `RouterHTTPClient` encapsula toda comunicação HTTP assíncrona com o backend.
- **`container/`** — `Container` expõe singleton de `RouterHTTPClient` via `get_router_client()`.
- **`messages/`** — `MessageConsumer` integra com RabbitMQ via `aio-pika`.

---

## Convenções de Código

- **Modelos**: `@dataclass` com type hints explícitos; fábricas como `from_dict()` e `load_dotenv()`
- **Construtores**: `__init__` padrão; sem retorno de interface — retorna tipo concreto
- **Injeção de dependência**: Manual via construtor; `Container.get_router_client()` para `RouterHTTPClient`
- **Banco de dados**: Sem banco local — estado gerenciado via `RouterHTTPClient` (API externa)
- **Logs**: `logging.debug/error` + `rich.Console`; sem `print()` em produção

## Convenções de Teste

- **Framework**: pytest + pytest-asyncio + respx
- **Estilo**: Classes agrupadas por classe testada com `@pytest.mark.unit` / `@pytest.mark.integration`; fixtures em `conftest.py`
- **Alvo principal**: `pytest tests/`

## Convenções de Commit

- **Idioma**: Todas as mensagens de commit devem ser escritas em **português do Brasil (pt-br)**
- **Formato**: Conventional Commits — `tipo(escopo): descrição curta` seguido de corpo opcional
- **Tipos**: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `style`, `perf`
- **Exemplo**:
  ```
  feat(models): adiciona operadores de comparação ao AuthLevel

  Implementa __lt__, __eq__ e __hash__ via @total_ordering para permitir
  comparações diretas entre níveis de acesso.
  ```
