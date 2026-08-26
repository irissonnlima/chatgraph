# Progresso do Projeto ChatGraph

**Última atualização:** 2026-08-17

## 1. Visão Geral do Projeto

**ChatGraph** é uma biblioteca Python 3.12+ para criação de chatbots interativos e modulares, com suporte a gRPC e RabbitMQ para gerenciamento de fluxos complexos de mensagens.

## 2. Arquitetura

### Padrão: Modular / Layered

```
chatgraph/
├── auth/          # Gerenciamento de credenciais
├── bot/           # Lógica principal do chatbot (ChatbotApp, ChatbotRouter, guards)
├── cli/           # CLI com Typer
├── container/     # Container de dependências
├── error/         # Exceções customizadas
├── gRPC/          # Comunicação gRPC
├── history/       # Histórico de mensagens plugável (HistoryStore, MemoryHistoryStore)
├── logger/        # Logging por usuário e sistema
├── messages/      # Consumidor RabbitMQ + LogPublisher (envio de erros)
├── models/        # Modelos de dados (UserState, Message, PlatformState, LogEnvelope, etc.)
├── pb/            # Arquivos protobuf gerados
├── services/      # Clientes HTTP (RouterHTTPClient)
└── types/         # Tipos do framework (Route, UserCall, EndTypes, BackgroundTask)
tests/
├── unit/          # Testes unitários com pytest + respx
└── integration/   # Testes de integração com APIs reais
```

## 3. Tecnologias Principais

| Categoria | Tecnologia |
|-----------|-----------|
| Linguagem | Python 3.12+ |
| Async | asyncio + aio-pika |
| Mensageria | RabbitMQ (pika / aio-pika) |
| gRPC | grpcio + protobuf |
| HTTP | httpx |
| CLI | typer |
| Logging | rich |
| Testes | pytest + pytest-asyncio + respx |
| Lint | ruff |

## 4. Linha do Tempo

### 2026-08

| Data | Commit | Descrição |
|------|--------|-----------|
| 2026-08-17 | - | **Fix: vocabulário de encerramento do agente + re-prompt corretivo.** Dois turnos de produção em 2026-08-14 falharam por causa raiz comum: o protocolo do agente não distinguia "transferir para outro bot" (`transfer_menu`) de "encerrar atendimento/transferir para humano" (`end_session`, ambos a mesma operação de EndAction no chatbot-router) — um bot acabou configurando um `MenuInfo` chamado `humano`, que o router rejeitou (`sql: no rows in result set`) só depois da promessa já ter sido enviada ao usuário. Correções: (1) `EndActionInfo`/`Agent(end_actions=...)`/`AgentContext.available_end_actions`, seção `AVAILABLE END ACTIONS` no prompt, resolução em `executor.py` (seletor por name/id, falha ANTES de side effect); (2) `AgentActionError` + `AgentContext.last_action_error` — ação inválida (transfer_menu ou end_session com seletor desconhecido) dispara 1 re-prompt corretivo por turno em vez de estourar o turno inteiro; sem correção, fallback é uma mensagem neutra fixa (nunca o `result.response`, que nesses casos costuma ser a promessa que acabou de falhar); (3) `build_agent_result_schema` parametrizado com enum de `menu`/`end_action_id` por Agent (`lru_cache(maxsize=32)`, antes `maxsize=1` sem args); (4) `agent.validate_config(router_client)` opt-in, confere no boot se menus/end_actions existem de verdade; (5) `TransferToHuman` aposentado do público (`__init__.py`, SKILL.md) — código morto no pipeline HTTP, mesma fonte de confusão um nível abaixo. Log DEBUG do raw response da LLM em `openrouter.py` para diagnosticar o próximo caso. Bug lateral corrigido: `Message.from_dict` não convertia `file` de dict para `File`, quebrando o registro de histórico em mensagens com anexo (`'dict' object has no attribute 'to_dict'`). |
| 2026-08-14 | - | **Agentes de IA (v1.4.0):** novo módulo `chatgraph/agent/` portando o protocolo single-agent do `chatgraph-go`: `Agent` (tools locais via `@agent.tool`, `generate_protocol`), `OpenRouterClient` (httpx, retry/backoff/Retry-After, structured outputs), normalização de JSON Schema (`schema.py`, port do `normalize.go`), prompts portados literalmente, executor com proteções (dedup por `result_key`, máx. 2 tentativas por tool, self-redirect guard, redirect silencioso, parada na primeira ação terminal, merge aditivo de observation), `history_bridge` (pareamento assistant/tool + `trim_safe`). Integração: `description=`/`ai_visible=` nos decorators (builder comum `route_registry.py`), `Route.infos`, `MAX_REDIRECT_DEPTH=5` no pipeline (corrige loop infinito de redirects e MESSAGE_IN duplicado em redirects). Extra opcional `chatgraph[agent]` (pydantic>=2) com exports lazy (PEP 562). Divergência consciente do Go: `transfer_menu` seleciona por **name** (client Python não transfere por queue). 461 testes unitários. |
| 2026-08-05 | `c24cbbd` | **Fix: acúmulo de `[ChatID: ...]` nos logs:** `ChatIDFilter.filter()` tornado idempotente (verifica `startswith` antes de prefixar); `remove_user_logger()` agora remove instâncias de `ChatIDFilter` antes de fechar handlers; `ChatID.__str__` adicionado (`user_id:company_id`); prefixo hardcoded removido da exceção em `UserCall.__send()`. Testes: `TestChatIDFilter` (3 novos), `test_remove_user_logger_removes_chatid_filters`, `test_remove_then_get_has_exactly_one_chatid_filter`, `test_chatid_str`, `TestSendException`. Revisão: ⚠️ CUIDADO — edge case `startswith` com `record.msg` não-string; teste de exceção poderia validar ausência de prefixo com `assert '[ChatID:' not in ...`. |
| 2026-08-04 | `672e4df` | **LogPublisher + integração final do histórico:** `LogPublisher` para publicação de erros via RabbitMQ com auto-configuração via `load_dotenv()`; `LogEnvelope`, `ErrorLogPayload`, `EventType` e mapeamento `error_code` por tipo de exceção. Integração completa do `HistoryStore` no pipeline: hooks `MESSAGE_IN`/`MESSAGE_OUT`/`ROUTE_CHANGE`/`TRANSFER`/`END_CHAT` no `UserCall` e `ChatbotApp`; repasse via `MessageConsumer`. Novas properties em `UserCall`: `user_state`, `session_id`, `message`, `history`. Publicação de erros em `ChatbotApp._publish_error_log` e `MessageConsumer._process_message_callback`. |
| 2026-08-04 | `c24cbbd` | **Testes:** `TestLogPublisher`, `TestLogEnvelope`, `TestChatbotAppLogPublisher`, `TestMessageConsumerLogPublisher`, `TestHistoryStore`, `TestHistoryIntegration`, `TestUserStateProperty`. Total: 283 testes unitários. |

### 2026-07

| Data | Commit | Descrição |
|------|--------|-----------|
| 2026-07-08 | - | Atualização dos agentes de desenvolvimento (Architect, Developer, CodeReviewer) |
| 2026-07-22 | - | Sistema de Histórico de Mensagens plugável (pacote `chatgraph/history/`): `HistoryEntry`/enums, `generate_idempotency_key` (SHA-256), `HistoryStore` (Protocol) + `MemoryHistoryStore` (FIFO/dedup), hooks em `UserCall` (MESSAGE_OUT/ROUTE_CHANGE/TRANSFER/END_CHAT) e `ChatbotApp.process_message` (MESSAGE_IN), repasse via `MessageConsumer`. Store opcional (retrocompatível), fire-and-forget. |
| 2026-07-22 | - | Revisão de follow-up (5 correções): `MESSAGE_IN` passou a registrar `Message.to_dict()` completo; hooks isolados em `try/except BaseException` fora do try principal; escopo limpo (revertidos `message.py`/`example.py`/`pyproject.toml`/`test_message_consumer.py`); E501 corrigido; testes ampliados (dedup com instâncias distintas + hook MESSAGE_IN + idempotência no reprocessamento). 23 testes de histórico, 253 unitários no total, sem regressão. |

## 5. Estado Atual por Área

| Área | Status | Descrição |
|------|--------|-----------|
| **Core Framework** | ✅ | Estrutura base de rotas, tipos e modelos implementada |
| **History Store** | ✅ | Pacote `chatgraph/history/` plugável (Protocol + MemoryHistoryStore) com hooks de mensagem/rota/transfer/end; `MESSAGE_IN` registra `to_dict()` completo; registro fire-and-forget (`BaseException`) |
| **LogPublisher** | ✅ | `LogPublisher` com auto-configuração via `load_dotenv()`; `LogEnvelope`, `ErrorLogPayload`, `EventType`; publicação de erros via RabbitMQ em `ChatbotApp` e `MessageConsumer`; mapeamento `error_code` por tipo de exceção |
| **RabbitMQ Consumer** | ✅ | MessageConsumer com suporte a modo passive (fallback), heartbeat e reconexão automática; integração com HistoryStore e LogPublisher |
| **gRPC Integration** | ✅ | Suporte a chamadas gRPC via gRPCCall |
| **HTTP Router Client** | ✅ | RouterHTTPClient para integração com API REST |
| **Logging** | ✅ | UserLoggerManager com logs por usuário e sistema |
| **CLI** | ✅ | Comandos básicos (campaigns, delete-ustate) |
| **Agentes de IA** | ✅ | Módulo `chatgraph/agent/` (protocolo single-agent do Go): Agent + tools locais, OpenRouterClient, schema normalizer, executor com proteções (inclui re-prompt corretivo de ação inválida), histórico com pareamento assistant/tool, `end_actions`/`validate_config`, `generate_content` desacoplado do turno de chat. Extra `chatgraph[agent]`. Futuro: two-agent, MCP, memória, guardrails |
| **Testes Unitários** | ✅ | 500 testes passando (agent + histórico + log publisher + UserState) |
| **Testes de Integração** | ⚠️ | Requer variáveis de ambiente configuradas |
| **Documentação** | ⚠️ | README completo + SKILL.md §14 (agentes); falta docs/ detalhada |

**Legenda:**
- ✅ Completo
- ⚠️ Parcial ou requer configuração
- ❌ Não iniciado

## 6. Convenções Estabelecidas

### Código
- **Lint**: ruff com line-length 79 e aspas simples
- **Tipagem**: Annotations do typing (Python 3.12+)
- **Async**: Suporte a sync e async nas rotas
- **Interfaces**: Sem prefixo I, tipagem por anotações
- **Construtores**: `__init__` + métodos factory `from_dict()`, `from_name()`
- **Injeção**: Manual via construtores
- **Logs**: `UserLoggerManager` (nunca print)

### Testes
- **Framework**: pytest + pytest-asyncio + respx
- **Estrutura**: Classes descritivas (`Test<Nome>Scenario`)
- **Fixtures**: Em `conftest.py`
- **Markers**: `@pytest.mark.unit` e `@pytest.mark.integration`
- **Mock HTTP**: `respx_mock`

### Rotas
- Convenção de nome: `start`, `start.choice`, `start.choice.about`
- Decorators: `@app.route()` e `@router.route()`
- Handlers recebem: `UserCall` e opcionalmente `Route`
- Default functions: regex matching antes das rotas
- Guard/Auth: `auth_level` por rota com `guard` customizável

## 7. Configuração de Ambiente

### Variáveis Obrigatórias
```bash
RABBIT_USER=seu_usuario
RABBIT_PASS=sua_senha
RABBIT_URI=amqp://localhost
RABBIT_QUEUE=chat_queue
RABBIT_PREFETCH=1
RABBIT_VHOST=/
ROUTER_URL=https://api.example.com/v1/actions
ROUTER_TOKEN=seu_token
```

### Variáveis Opcionais — Log Publisher
```bash
# Defina LOG_RABBIT_QUEUE para ativar o envio de logs de erro para RabbitMQ
LOG_RABBIT_QUEUE=logs
LOG_RABBIT_EXCHANGE=chatbot-hml
# LOG_RABBIT_ROUTING_KEY=chatbot.logs  # default = chatbot.{LOG_RABBIT_QUEUE}
```

### Testes
```bash
# Unitários
poetry run pytest tests/unit/ -v

# Com cobertura
poetry run pytest --cov=chatgraph --cov-report=html

# Integração (requer env vars)
poetry run pytest tests/integration/ -v
```

### Lint e Formatação
```bash
poetry run ruff check . && ruff format .
```

## 8. Decisões Técnicas Importantes

| Tópico | Decisão | Justificativa |
|--------|---------|---------------|
| Estado | Externo (via API) | Escalabilidade e persistência |
| Async/Sync | Suporte a ambos | Flexibilidade para handlers |
| RabbitMQ | Modo passive primeiro | Evita PRECONDITION_FAILED em filas existentes |
| HTTP Client | httpx | Async nativo e moderno |
| gRPC | protobuf | Contratos tipados e performance |
| History Store | Protocol (não ABC) | Plugável, sem acoplamento a classe base |
| Log Publisher | load_dotenv() + opcional | Retrocompatível — se `LOG_RABBIT_QUEUE` não estiver definido, o publisher é `None` e os erros não são publicados |
| Agentes de IA | Port fiel do Go, sem pydantic-ai/SDK openai | Paridade de comportamento entre os frameworks; cliente OpenRouter próprio via httpx; pydantic>=2 isolado ao módulo `agent/` (extra opcional `chatgraph[agent]`, exports lazy PEP 562) |
| transfer_menu do agente | Seletor por `name` do menu | O client Python só transfere por nome (`Menu.from_name`); queue/menu_id do Go não mapeiam — reintroduzir se o RouterHTTPClient ganhar transfer por queue |
| Redirects | `MAX_REDIRECT_DEPTH=5` global | Recursão de `RedirectResponse` era ilimitada (risco de loop, agravado por agentes); a reentrada por redirect também não regrava MESSAGE_IN no histórico |
| end_session do agente | Seletor por `name` (depois `id`) de `EndActionInfo`, mesmo critério do `transfer_menu` | `end_session` cobre encerrar E transferir para humano (mesma EndAction no chatbot-router); sem `end_actions` configuradas, `end_action_id` continua livre (retrocompatível) |
| Ação inválida do agente | Re-prompt corretivo (1 tentativa/turno via `AgentContext.last_action_error`), depois mensagem neutra fixa | Um `transfer_menu`/`end_session` com seletor inexistente perdia o turno inteiro em silêncio (ou, pior, enviava a promessa antes do router rejeitar); "falha antes de side effect" continua valendo — a correção nunca executa ação |
| TransferToHuman | Aposentado do público (`__init__.py`, SKILL.md); classe mantida em `end_types.py` só por compatibilidade de import | Código morto no pipeline HTTP (sem ramo em `__process_func_response`, sem método no `RouterHTTPClient`) — mesma confusão de "transferir para humano" um nível abaixo do bug de `transfer_menu`/`humano` |

## 9. Trabalhos Pendentes

| Prioridade | Tarefa | Área | Status |
|------------|--------|------|--------|
| Alta | Eliminar duplicação de lógica de registro entre `ChatbotApp.__record_message_in` e `UserCall.__record_history` | chatgraph/bot + types | ⚠️ |
| Média | Agentes: protocolo two-agent (`DecideRoute`+`Speak`) | chatgraph/agent | ❌ |
| Média | Agentes: MCP (stdio/SSE/HTTP) como fonte de tools | chatgraph/agent | ❌ |
| Média | Agentes: memória de longo prazo (`MemoryContext`) e guardrails | chatgraph/agent | ❌ |
| Média | Documentação técnica detalhada | docs/ | ❌ |
| Média | Mais testes de integração | tests/integration/ | ⚠️ |
| Baixa | Dispatcher com serialização por chat_id (prefetch > 1 seguro p/ bots com agente) | messages/ | ❌ |
| Baixa | Exemplos adicionais | examples/ | ⚠️ (`examples/agents_bot.py` criado) |
| Baixa | Suporte a mais plataformas | bot/ | ❌ |

## 10. Notas e Observações

- **MessageConsumer**: Implementado com fallback para modo passive quando fila já existe (resolve PRECONDITION_FAILED). Integrado com `HistoryStore` (repasse para `UserCall`) e `LogPublisher` (captura de exceções no callback).
- **RouterHTTPClient**: Integração via HTTP/REST com retry e timeout configuráveis
- **Id Positiva**: Integração via endpoint `/v1/id-positiva/`
- **History Store**: Plugável via `Protocol` (não ABC); `MemoryHistoryStore` padrão em memória com FIFO e dedup por idempotency key (SHA-256). Store opcional (`None` = no-op, retrocompatível). Registro fire-and-forget (hooks isolados em `try/except BaseException` fora do try principal; falhas geram warning, não propagam `Exception`/`BaseException`). Hooks em `UserCall` (MESSAGE_OUT/ROUTE_CHANGE/TRANSFER/END_CHAT) e `ChatbotApp.process_message` (MESSAGE_IN, payload `Message.to_dict()` completo). Pendência: lógica de registro duplicada entre `ChatbotApp.__record_message_in` e `UserCall.__record_history`.
- **LogPublisher**: Auto-configuração via `load_dotenv()`; se `LOG_RABBIT_QUEUE` não estiver definido, retorna `None` (no-op). Exchange e routing key configuráveis; default do routing key: `chatbot.{queue_name}`. Publicação fire-and-forget (falhas geram warning, não propagam). Erros capturados em `ChatbotApp.process_message` e `MessageConsumer._process_message_callback`. `LogEnvelope` com `ErrorLogPayload`, `EventType` e mapeamento `error_code` por classe de exceção (`ChatbotMessageError`, `ChatbotError`, `ValueError`, `TypeError`, `KeyError`, fallback `UNKNOWN_ERROR`).
- **UserCall**: Novas properties: `user_state` (UserState completo), `session_id` (int | None), `message` (Message), `history` (HistoryStore | None). `__record_history` privado com idempotency key SHA-256.
