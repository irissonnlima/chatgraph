# Progresso do Projeto ChatGraph

**Última atualização:** 2026-08-05

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
| **Testes Unitários** | ✅ | 283 testes passando (histórico + log publisher + UserState) |
| **Testes de Integração** | ⚠️ | Requer variáveis de ambiente configuradas |
| **Documentação** | ⚠️ | README completo, falta docs/ detalhada |

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

## 9. Trabalhos Pendentes

| Prioridade | Tarefa | Área | Status |
|------------|--------|------|--------|
| Alta | Eliminar duplicação de lógica de registro entre `ChatbotApp.__record_message_in` e `UserCall.__record_history` | chatgraph/bot + types | ⚠️ |
| Média | Documentação técnica detalhada | docs/ | ❌ |
| Média | Mais testes de integração | tests/integration/ | ⚠️ |
| Baixa | Exemplos adicionais | examples/ | ❌ |
| Baixa | Suporte a mais plataformas | bot/ | ❌ |

## 10. Notas e Observações

- **MessageConsumer**: Implementado com fallback para modo passive quando fila já existe (resolve PRECONDITION_FAILED). Integrado com `HistoryStore` (repasse para `UserCall`) e `LogPublisher` (captura de exceções no callback).
- **RouterHTTPClient**: Integração via HTTP/REST com retry e timeout configuráveis
- **Id Positiva**: Integração via endpoint `/v1/id-positiva/`
- **History Store**: Plugável via `Protocol` (não ABC); `MemoryHistoryStore` padrão em memória com FIFO e dedup por idempotency key (SHA-256). Store opcional (`None` = no-op, retrocompatível). Registro fire-and-forget (hooks isolados em `try/except BaseException` fora do try principal; falhas geram warning, não propagam `Exception`/`BaseException`). Hooks em `UserCall` (MESSAGE_OUT/ROUTE_CHANGE/TRANSFER/END_CHAT) e `ChatbotApp.process_message` (MESSAGE_IN, payload `Message.to_dict()` completo). Pendência: lógica de registro duplicada entre `ChatbotApp.__record_message_in` e `UserCall.__record_history`.
- **LogPublisher**: Auto-configuração via `load_dotenv()`; se `LOG_RABBIT_QUEUE` não estiver definido, retorna `None` (no-op). Exchange e routing key configuráveis; default do routing key: `chatbot.{queue_name}`. Publicação fire-and-forget (falhas geram warning, não propagam). Erros capturados em `ChatbotApp.process_message` e `MessageConsumer._process_message_callback`. `LogEnvelope` com `ErrorLogPayload`, `EventType` e mapeamento `error_code` por classe de exceção (`ChatbotMessageError`, `ChatbotError`, `ValueError`, `TypeError`, `KeyError`, fallback `UNKNOWN_ERROR`).
- **UserCall**: Novas properties: `user_state` (UserState completo), `session_id` (int | None), `message` (Message), `history` (HistoryStore | None). `__record_history` privado com idempotency key SHA-256.
