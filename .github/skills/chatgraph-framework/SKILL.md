---
name: chatgraph-framework
description: "Use when: implementing a chatbot with chatgraph, creating routes with @app.route or @router.route, using UserCall, Route, Message, File, Button, EndChatResponse, RedirectResponse, TransferToMenu, BackgroundTask, setting up ChatbotApp, ChatbotRouter, include_router, configuring RabbitMQ consumer, configuring WebSocket stream transport (ROUTER_TRANSPORT=stream, ROUTER_MENUS, StreamConsumer, SessionNotOwnedError), adding per-user file logging with UserLoggerManager, integrating chatgraph in a new Python project."
argument-hint: "Descreva o fluxo de rotas que deseja implementar (opcional)"
---

# chatgraph-framework

Guia completo para implementar o framework **chatgraph** em projetos Python. Cobre setup, rotas, tipos de resposta, mensagens, logging e modularização.

## Visão Geral

O chatgraph é um framework de chatbot que consome mensagens via RabbitMQ e despacha para funções de rota registradas via decorador. O ponto de entrada de toda rota é `UserCall`, que agrega mensagem recebida, estado do usuário e cliente HTTP.

```
RabbitMQ → MessageConsumer → ChatbotApp.process_message() → @route() → UserCall
```

---

## 1. Instalação e Dependências

```toml
# pyproject.toml
[project]
requires-python = ">=3.12"
dependencies = [
    "chatgraph",
    "python-dotenv",
]
```

```bash
pip install chatgraph python-dotenv
```

---

## 2. Variáveis de Ambiente Obrigatórias

```env
# .env
RABBIT_USER=guest
RABBIT_PASS=guest
RABBIT_URI=localhost:5672
RABBIT_QUEUE=minha_fila
RABBIT_PREFETCH=1
RABBIT_VHOST=/
# Só o host; /v1/actions continua aceito
ROUTER_URL=http://localhost:8000
ROUTER_TOKEN=meu_token

# Opcional — transporte de entrada: queue (RabbitMQ, padrão) ou stream
# (WebSocket). No stream as RABBIT_* são dispensadas e ROUTER_MENUS
# (vírgula; padrão RABBIT_QUEUE) lista os menus servidos.
# ROUTER_TRANSPORT=queue
# ROUTER_MENUS=minha_fila

# Opcional — nível de log padrão (DEBUG, INFO, WARNING, ERROR). Default: INFO
CHATGRAPH_LOG_LEVEL=INFO
```

---

## 3. Setup Mínimo

```python
from chatgraph import ChatbotApp, UserCall, Route
from chatgraph.logger import get_system_logger
from dotenv import load_dotenv

load_dotenv()

_logger = get_system_logger()   # logs de módulo → chatgraph_logs/system.log
_logger.info('Aplicação inicializada')

app = ChatbotApp()
# Opções disponíveis:
# app = ChatbotApp(
#     log_level='DEBUG',         # sobrescreve CHATGRAPH_LOG_LEVEL
#     guard=meu_guard_customizado,  # substitui o default_guard
# )

@app.route('start')
async def start(usercall: UserCall, rota: Route):
    usercall.logger.info('Usuário na rota start')
    await usercall.send('Olá! Como posso ajudar?')

app.start()
```

> `app.start()` inicia o loop assíncrono de consumo do RabbitMQ. É bloqueante.

---

## 4. Parâmetros das Funções de Rota

Toda função de rota pode declarar **qualquer combinação** dos parâmetros abaixo (ordem livre — o framework resolve por tipo):

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `usercall` | `UserCall` | Mensagem + estado + cliente HTTP do usuário atual |
| `rota` | `Route` | Rota atual e histórico de navegação |

```python
@app.route('start')
async def start(usercall: UserCall, rota: Route): ...

@app.route('start')
async def start(usercall: UserCall): ...   # Route é opcional

@app.route('start')
async def start(rota: Route): ...          # UserCall é opcional
```

---

## 5. UserCall — API Completa

```python
# Dados do usuário
usercall.user_id          # str — ID do usuário
usercall.company_id       # str — ID da empresa
usercall.content_message  # str — texto da mensagem recebida
usercall.menu             # Menu — menu atual do usuário
usercall.route            # str — rota atual (ex: "start.choice")
usercall.observation      # dict — observações da sessão (get/set)
usercall.chatID           # ChatID(user_id, company_id)
usercall.user             # User — dados completos do usuário da sessão

# Acesso aos sub-objetos de usercall.user
usercall.user.data.name            # str | None — nome
usercall.user.data.cpf             # str | None — CPF
usercall.user.data.phone           # str | None — telefone
usercall.user.data.email           # str | None — e-mail
usercall.user.data.nickname        # str | None — apelido
usercall.user.data.profile_photo_url  # str | None — foto de perfil
usercall.user.data.account            # str | None — conta/matrícula
usercall.user.data.birth_date         # str | None — data de nascimento

usercall.user.identity.auth_level     # AuthLevel — nível de autenticação (BLOCKED/UNKNOWN/READ/WRITE)
usercall.user.identity.cpf            # str | None — CPF autenticado
usercall.user.identity.active         # bool | None — usuário ativo
usercall.user.identity.auth_status    # str | None — status de autenticação
usercall.user.identity.device_id      # str | None — ID do dispositivo

usercall.user.internal                # UserInternal | None — dados internos (RH)
usercall.user.internal.matricula      # str | None
usercall.user.internal.cargo          # str | None
usercall.user.internal.filial         # str | None
usercall.user.internal.empresa        # str | None
usercall.user.internal.data_admissao  # str | None

# Logging contextualizado por usuário
usercall.logger           # logging.Logger → chatgraph_logs/{user_id}_{company_id}.log

# Envio de mensagens
await usercall.send(message)           # Message | File | str | int | float

# Navegação e estado
await usercall.set_route('nova_rota')
await usercall.set_observation('texto')
await usercall.add_observation({'chave': 'valor'})
await usercall.update_user_data(user)

# Encerramento
await usercall.end_chat(end_action_id='id', end_action_name='nome', observation='...')
await usercall.transfer_to_menu('nome_menu', 'mensagem_usuario')
await usercall.transfer_to_menu('nome_menu', 'mensagem_usuario', route='rota_inicial')  # com rota de entrada

# Consulta
menu = await usercall.get_menu(name='nome_menu')           # por nome
menu = await usercall.get_menu(menu_id=42)                 # por ID
menu = await usercall.get_menu(description='Suporte TI')   # por descrição

# Setters diretos (síncronos — não persistem imediatamente, usam loop existente)
usercall.observation = {'chave': 'valor'}  # dict — substitui toda a observação
usercall.content_message = 'nova mensagem'  # str — sobrescreve o texto recebido

# Carga/atualização de dados remotos
identity = await usercall.load_identity()            # recarrega UserIdentity da API
identity = await usercall.load_identity(cpf='cpf')   # força busca por CPF específico
userstate = await usercall.load_userstate()          # recarrega UserState completo da API

# Associação de CPF
await usercall.associate_cpf(
    cpf='00000000000',
    source='nome_do_menu',   # origem da associação (ex: nome do menu)
    phone='',                # telefone da empresa (opcional)
    device_id='',            # ID do dispositivo (opcional)
)
```

---

## 6. Tipos de Retorno de Rota

Cada função de rota deve retornar **um dos tipos** abaixo:

### `RedirectResponse(route)` — Redireciona e re-executa imediatamente
```python
return RedirectResponse('choice_start')
```

### `Route(current_node)` — Atualiza a rota e aguarda nova mensagem
```python
return Route('aguardando_resposta')
```

### `EndChatResponse(end_chat_id, end_chat_name?, observations?)` — Encerra o chat OU transfere para humano
No chatbot-router, encerrar o atendimento e transferir para um atendente humano são a
**mesma operação**: uma tabulação de encerramento com ID/nome próprio. Não existe um tipo de
retorno separado para "transferir para humano" — use `EndChatResponse` com a end action de
atendimento humano configurada no router.
```python
return EndChatResponse('voll_ended')
return EndChatResponse('', end_chat_name='Encerrado pelo usuário', observations='motivo')
return EndChatResponse('ea_atendimento_humano')  # transferência para humano é um end_chat_id específico
```

### `TransferToMenu(menu, user_message, route?)` — Transfere para OUTRO BOT (menu)
`TransferToMenu` é só bot→bot (outro menu/robô configurado no router). **Nunca** use para chegar a
um atendente humano — isso é `EndChatResponse` (ver acima). Confundir os dois faz o handler prometer
uma transferência que o router rejeita, porque o "menu" de atendimento humano não existe como menu.
```python
return TransferToMenu('p0299_suporte_ti', 'Transferindo...')
return TransferToMenu('p0299_suporte_ti', 'Transferindo...', route='etapa_inicial')  # inicia em rota específica
```

> `TransferToHuman` (`chatgraph.types.end_types`) é **obsoleto**: não tem efeito no pipeline HTTP
> (só existia no caminho gRPC legado). Não é mais exportado por `chatgraph/__init__.py`.

### `BackgroundTask(async_func, *args, **kwargs)` — Executa tarefa em background e encadeia o retorno
```python
async def processar(usercall: UserCall):
    await usercall.send('Processando...')
    return EndChatResponse('concluido')

return BackgroundTask(processar, usercall)
```

### Lista/tupla — Múltiplas respostas sequenciais
```python
return [
    Message('Primeira mensagem'),
    Message('Segunda mensagem'),
    RedirectResponse('proxima_rota'),
]
```

---

## 7. Mensagens

```python
from chatgraph import Message, Button, File, TextMessage, SendType

# Texto simples
await usercall.send('Olá!')
await usercall.send(Message('Olá!'))

# Com botões
msg = Message(
    'Escolha uma opção:',
    buttons=[
        Button('Opção 1'),                        # POSTBACK simples
        Button('Ver mais', detail='payload_123'), # com payload
        Button('Cancelar'),
    ],
)
await usercall.send(msg)

# Arquivo por path local
file = File.from_path('caminho/para/imagem.png')
await usercall.send(file)

# Arquivo em mensagem
msg_com_arquivo = Message(file=file)
await usercall.send(msg_com_arquivo)
```

### `Button` — campos
```python
from chatgraph import Button
from chatgraph.models.message import ButtonType  # não exportado no __init__ top-level

Button(
    title='Texto do botão',   # exibido para o usuário
    detail='payload',         # dados enviados ao pressionar (opcional)
    type=ButtonType.POSTBACK, # ButtonType.POSTBACK (padrão) | ButtonType.URL
)
```

### `TextMessage` — dataclass
```python
from chatgraph import TextMessage

# Normalmente criado automaticamente por Message(str)
# Acesso direto ao conteúdo recebido:
usercall.content_message  # equivale a mensagem_recebida.text_message.detail
```

### `SendType` — enum para arquivos
```python
from chatgraph import SendType

# SendType.IMAGE | SendType.VIDEO | SendType.AUDIO | SendType.FILE | SendType.UNKNOWN
file = File.from_path('video.mp4')
file.send_type = SendType.VIDEO
```

---

## 8. Logging

### Níveis recomendados

| Situação | Método | Destino |
|----------|--------|---------|
| Dentro de rota, com `usercall` | `usercall.logger.info/debug/warning/error(...)` | `chatgraph_logs/{user_id}_{company_id}.log` |
| Fora de rota (startup, módulo) | `_logger = get_system_logger()` | `chatgraph_logs/system.log` |

```python
from chatgraph.logger import get_system_logger, get_user_logger, set_level

_logger = get_system_logger()
_logger.info('App iniciada')

# Logger de usuário fora de uma rota (raramente necessário — prefira usercall.logger dentro de rotas)
user_log = get_user_logger('user123', 'empresa456')

# Alterar nível de log em runtime (afeta todos os loggers existentes)
set_level('DEBUG')   # ou logging.DEBUG
# Equivalente: UserLoggerManager.set_level('DEBUG')

@app.route('start')
async def start(usercall: UserCall):
    usercall.logger.info('Usuário entrou em start')
    usercall.logger.debug(f'Mensagem recebida: {usercall.content_message}')
    try:
        await usercall.send('Olá!')
    except Exception as e:
        usercall.logger.error(f'Erro ao enviar: {e}')
```

### Formato do log
```
2026-05-06 15:13:15,828 | INFO | Mensagem | nome_funcao | user123_empresa456
```

---

## 9. Modularização com `ChatbotRouter`

Para projetos maiores, organize rotas em módulos separados:

```python
# rotas/suporte.py
from chatgraph import ChatbotRouter, UserCall, Route, RedirectResponse

router = ChatbotRouter()

@router.route('suporte')
async def suporte(usercall: UserCall):
    await usercall.send('Como posso ajudar?')
    return Route('aguardar_resposta_suporte')

@router.route('aguardar_resposta_suporte')
async def aguardar(usercall: UserCall):
    await usercall.send(f'Você disse: {usercall.content_message}')
    return RedirectResponse('start')

# auth_level também pode ser definido em rotas de router
@router.route('area_rh', auth_level='internal')
async def area_rh(usercall: UserCall):
    await usercall.send(f'Olá, {usercall.user.internal.cargo}!')
    return RedirectResponse('start')
```

```python
# main.py
from chatgraph import ChatbotApp
from rotas.suporte import router as suporte_router

app = ChatbotApp()
app.include_router(suporte_router)

app.start()
```

> Não há prefixo automático — o nome de cada `@router.route('nome')` é o nome final da rota.

`ChatbotRouter` também pode absorver outro `ChatbotRouter` com `include_router()`:

```python
# rotas/geral.py
from chatgraph import ChatbotRouter
from rotas.suporte import router as suporte_router
from rotas.vendas import router as vendas_router

router = ChatbotRouter()
router.include_router(suporte_router)
router.include_router(vendas_router)
```

---

## 10. Funções Padrão (`default_functions`)

O `ChatbotApp` intercepta mensagens **antes** de despachar para a rota quando o texto corresponder a um padrão regex registrado em `default_functions`. Após a execução da função padrão, `content_message` é zerado.

### Comportamento embutido — `voltar`

Por padrão, qualquer mensagem que corresponda a `^\s*(voltar)\s*$` (case-insensitive) é interceptada e executa `voltar()`, que redireciona para o nó anterior via `route.get_previous()`.

```python
# Comportamento automático — nenhuma rota necessária
# Usuário digita "voltar" → retorna para a rota anterior
```

### Customizar ou desabilitar as funções padrão

```python
from chatgraph import ChatbotApp

# Desabilitar o voltar
app = ChatbotApp(default_functions={})

# Adicionar função customizada
from chatgraph import UserCall, Route, RedirectResponse

async def ajuda(route: Route, usercall: UserCall):
    await usercall.send('Comandos disponíveis: voltar, sair')
    return RedirectResponse(route.current_node)

app = ChatbotApp(default_functions={
    r'^\s*(voltar)\s*$': voltar,    # manter o padrão
    r'^\s*(ajuda|help)\s*$': ajuda, # adicionar novo
})
```

> As funções padrão recebem `(route: Route, usercall: UserCall)` e têm acesso às mesmas respostas de rota. `auth_level` não é verificado para funções padrão.

---

## 11. Fluxo de Navegação

- Rota inicial obrigatória: `start`
- Sub-rotas usam notação de ponto internamente: `start.choice.confirm`
- `Route(node)` adiciona o nó ao caminho atual e aguarda nova mensagem
- `RedirectResponse(route)` troca para o nó e re-executa imediatamente (sem aguardar)
- `rota.current_node` → último segmento (ex: `"confirm"`)
- `rota.previous` → rota anterior no histórico
- `rota.get_next('sub_rota')` → constrói o próximo `Route` e valida se existe na lista de rotas disponíveis

---

## 12. Controle de Acesso — `auth_level` e `guard`

Cada rota pode declarar um `auth_level` que é validado pelo guard antes de executar a função.

```python
# Níveis suportados pelo default_guard:
# 'read'     → usercall.user.identity.auth_level >= AuthLevel.READ
# 'write'    → usercall.user.identity.auth_level >= AuthLevel.WRITE
# 'internal' → usercall.user.internal não pode ser None

@app.route('area_restrita', auth_level='internal')
async def area_restrita(usercall: UserCall):
    await usercall.send('Acesso autorizado!')
    return RedirectResponse('menu_principal')

@app.route('dados_sensiveis', auth_level='write')
async def dados_sensiveis(usercall: UserCall):
    await usercall.send('Você tem permissão de escrita.')
    return EndChatResponse('concluido')
```

Quando o acesso é negado, o `default_guard` redireciona para `menu_id_positiva` e salva `pending_route`, `pending_menu` e `pending_auth_level` na observação da sessão.

### Guard customizado

```python
from chatgraph import ChatbotApp, UserCall, default_guard
from chatgraph.types.end_types import TransferToMenu

async def meu_guard(usercall: UserCall, auth_level: str) -> TransferToMenu | None:
    if auth_level == 'admin' and usercall.user.data.email != 'admin@empresa.com':
        return TransferToMenu('menu_acesso_negado', '')
    return None  # None = acesso liberado

app = ChatbotApp(guard=meu_guard)
```

> Se o guard retornar `None`, a rota é executada normalmente. Qualquer outro tipo de retorno é processado como resposta de rota (ex: `TransferToMenu`, `RedirectResponse`).

---

## 13. Exemplo Completo

```python
from chatgraph import (
    ChatbotApp, UserCall, Route,
    Message, Button, File,
    EndChatResponse, RedirectResponse, TransferToMenu,
)
from chatgraph.logger import get_system_logger
from dotenv import load_dotenv

load_dotenv()
_logger = get_system_logger()
_logger.info('Aplicação iniciada')
app = ChatbotApp()


@app.route('start')
async def start(usercall: UserCall, rota: Route):
    usercall.logger.info('Usuário entrou em start')
    await usercall.send(
        Message('Bem-vindo! Escolha:', buttons=[Button('Suporte'), Button('Sair')])
    )
    return Route('aguardar_escolha')


@app.route('aguardar_escolha')
async def aguardar_escolha(usercall: UserCall):
    resposta = usercall.content_message
    usercall.logger.info(f'Escolha recebida: {resposta}')

    if resposta == 'Suporte':
        return TransferToMenu('menu_suporte', 'Transferindo para suporte...')
    elif resposta == 'Sair':
        return EndChatResponse('encerrado')
    else:
        usercall.logger.warning(f'Opção inválida: {resposta}')
        await usercall.send('Opção inválida. Tente novamente.')
        return RedirectResponse('start')


app.start()
```

## 14. Agentes de IA (`chatgraph.agent`)

Requer o extra opcional: `pip install chatgraph[agent]` (pydantic>=2).
Port do protocolo single-agent do `chatgraph-go`: uma chamada de LLM
decide navegação E escreve a resposta, com tool calling declarativo.

### Conceitos

- **`Agent`**: configura LLM client, modelo, prompt de personalidade,
  tools locais, menus, end actions e o modelo pydantic da observation.
- **`description` da rota é o prompt de comportamento** daquela rota —
  injetada no system prompt do protocolo. `ai_visible=True` expõe a
  rota ao roteamento do agente.
- **Tools locais** (`@agent.tool`): o modelo as chama via ação
  `call_tool`; o resultado entra na observation sob `result_key` e o
  agente decide de novo (até `max_tool_loops`, default 5).
- **Ações do protocolo** mapeiam nos tipos de retorno existentes:
  `send_message`→`Message`, `next_route`→`Route`,
  `redirect`→`RedirectResponse`, `set_observation`→merge aditivo na
  observation.
- **`end_session`→`EndChatResponse`** cobre TANTO encerrar o
  atendimento QUANTO transferir para um atendente humano — no
  chatbot-router as duas são a mesma operação (uma tabulação de
  encerramento). Seleção por **name** do `EndActionInfo` configurado
  em `Agent(end_actions=[...])`.
- **`transfer_menu`→`TransferToMenu`** é só bot→bot (seleção por
  **name** do `MenuInfo`). **Nunca** configure um menu para representar
  "atendimento humano" — isso pertence a `end_actions`/`end_session`.
  Confundir os dois faz o agente prometer uma transferência que o
  router rejeita (o "menu" de humano não existe como menu).
- **Histórico**: com `history_store` configurado no `ChatbotApp`, o
  agente recebe a conversa (janela `history_limit`, default 20) com o
  pareamento assistant/tool preservado.
- **Ação inválida do modelo** (menu/end_action_id que não existe na
  lista configurada) dispara um re-prompt corretivo automático (1
  tentativa por turno, via `AgentContext.last_action_error`); se a
  correção também falhar, o turno termina com uma mensagem neutra em
  vez de silêncio ou uma promessa que não vai se cumprir.

### Env vars

```
OPENROUTER_API_KEY=sk-or-...   # obrigatória p/ OpenRouterClient
OPENROUTER_BASE_URL=...        # opcional
AGENT_MODEL=openai/gpt-4o-mini # obrigatória p/ Agent.load_dotenv
AGENT_TEMPERATURE / AGENT_MAX_TOKENS / AGENT_MAX_TOOL_LOOPS /
AGENT_HISTORY_LIMIT / AGENT_SYSTEM_PROMPT_FILE   # opcionais
LOG_AGENT_CONTEXT=1            # debug: loga contexto completo (PII!)
```

### Exemplo

```python
from pydantic import BaseModel
from chatgraph import (
    Agent, ChatbotApp, EndActionInfo, MenuInfo, OpenRouterClient, Route,
    UserCall,
)
from chatgraph.history.store import MemoryHistoryStore


class PedidoObs(BaseModel):
    cpf: str = ''
    numero_pedido: str = ''


agent = Agent(
    llm_client=OpenRouterClient.load_dotenv(),
    model='openai/gpt-4o-mini',
    system_prompt='Você é o assistente da loja. Responda em pt-BR.',
    observation_model=PedidoObs,
    # transfer_menu: só bot→bot (outro robô configurado no router).
    menus=[MenuInfo(name='suporte_ti', description='Bot de suporte técnico.')],
    # end_session: encerrar OU transferir para atendente humano — NÃO
    # é um menu. "id" é opcional (o seletor por name já basta).
    end_actions=[
        EndActionInfo(name='humano', description='Atendente humano.'),
        EndActionInfo(name='resolvido', description='Atendimento concluído.'),
    ],
)

# Opcional, no boot do bot (fora do caminho de mensagem): confirma que
# os menus/end_actions acima existem de verdade no chatbot-router,
# falhando cedo em vez de só na primeira transferência de um usuário.
# await agent.validate_config(router_client)


@agent.tool(
    description='Consulta pedido por CPF e número.',
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
    return {'status': 'Entregue'}


app = ChatbotApp(history_store=MemoryHistoryStore())


@app.route(
    'buscar_pedido',
    description="Order lookup — collect cpf and numero_pedido. Call "
        "consultar_pedido with result_key='dados_pedido', then "
        'redirect to exibir_pedido.',
    ai_visible=True,
)
async def buscar_pedido(call: UserCall, route: Route):
    return await agent.execute(call, route)
```

### Regras e cuidados

- Handlers com agente devem ser `async` (sync roda em thread e não
  pode `await`).
- Um turno de agente pode levar vários segundos (até `max_tool_loops`
  chamadas de LLM). Com `RABBIT_PREFETCH=1` a fila serializa —
  considere aumentar o prefetch para bots com agente.
- Redirects têm limite global (`MAX_REDIRECT_DEPTH=5` em
  `chatbot_model.py`): um agente que redirecionar em ciclo é
  interrompido com erro no log.
- `await agent.validate_config(router_client)` é opcional e não é
  chamado automaticamente — confere no boot se os `menus`/`end_actions`
  configurados existem de verdade no chatbot-router. Chame fora do
  caminho de mensagem (uma vez, ao subir o bot).
- Proteções do executor (port do Go): dedup de tool por `result_key`,
  máx. 2 tentativas por tool com degradação, self-redirect vira
  "none", alvo de rota desconhecido vira "none" com warning, redirect
  é silencioso (a rota destino responde), transfer inválido falha
  ANTES de qualquer side effect.
- Exemplo completo: `examples/agents_bot.py`.

## 15. Geração de conteúdo desacoplada (`generate_content`)

Requer o mesmo extra opcional: `pip install chatgraph[agent]`.

**Para dados internos do bot, não para turno de chat.** Caso de uso:
o bot tem acesso a uma base interna (ex.: uma consulta a banco) e
precisa que a IA analise esse conteúdo e devolva um insight — não é
uma mensagem de cliente, não tem rota, não tem menu, não passa por
`UserCall`/`Route`/`AgentContext`. `generate_content` é uma função
solta, independente de `Agent`: funciona com qualquer `LLMClient`
(inclusive `OpenRouterClient` já existente), sem exigir menus, tools,
observation_model ou histórico de conversa configurados.

```python
import json

from pydantic import BaseModel
from chatgraph import OpenRouterClient, generate_content


class VendasInsight(BaseModel):
    resumo: str
    tendencia: str
    produtos_em_alerta: list[str] = []


async def gerar_relatorio(dados_do_banco: list[dict]) -> VendasInsight | None:
    result = await generate_content(
        OpenRouterClient.load_dotenv(),
        model='openai/gpt-4o-mini',
        content=json.dumps(dados_do_banco, ensure_ascii=False),
        system_prompt='Você é um analista de vendas. Responda em pt-BR.',
        response_model=VendasInsight,  # opcional; sem ele, result.data é None
    )
    return result.data  # ou result.text, se response_model não foi passado
```

- **`content`** é uma string já serializada pelo chamador (JSON, CSV,
  texto) — a função não sabe de onde o dado vem.
- **`response_model`** opcional (mesmo padrão do `observation_model` do
  `Agent`): com ele, o Structured Output usa o schema fechado do
  modelo e `result.data` vem parseado; sem ele, só `result.text`.
- **`history`** opcional para follow-up sobre o mesmo conteúdo (ex.:
  uma segunda pergunta sobre o mesmo relatório) — sem `HistoryStore`,
  cada chamada é isolada por padrão.
- **O retorno não passa pelo pipeline** (`Message`/`Route`/etc.): é
  consumido diretamente por quem chamou — envie via `usercall.send(...)`
  se estiver dentro de um handler, ou grave em log/banco se for um job
  agendado sem turno de chat nenhum.
- Exemplo completo: `examples/content_insight.py`.

---

## 16. Transporte stream (WebSocket)

Alternativa ao RabbitMQ: o bot recebe as mensagens do router por WebSocket. `ROUTER_TRANSPORT=stream` basta; o código das rotas não muda. `ChatbotApp()` escolhe o consumer pelo transporte; com consumer explícito: `ChatbotApp(message_consumer=StreamConsumer(router_url, router_token, menus=['rh']))`.

| Variável | Descrição |
|---|---|
| `ROUTER_TRANSPORT` | `queue` (padrão) ou `stream` |
| `ROUTER_MENUS` | menus servidos, separados por vírgula (padrão: `RABBIT_QUEUE`) |
| `ROUTER_URL` | só o host (`https://voll-hml.verdecard.cloud`); `…/v1` e `…/v1/actions` continuam aceitos. A URL do WebSocket é derivada (`http→ws`, `https→wss`, `/v1/menus/connect`) |
| `ROUTER_TOKEN` | precisa estar vinculado em `token_menus` a cada menu declarado |
| `RABBIT_*` | dispensadas; só o `LogPublisher` usa, se `LOG_RABBIT_QUEUE` estiver definida |

Comportamento:

- ack imediato antes do handler, dedupe por `msg_id` + menu, processamento serial, fila de 100 com `nack` quando cheia;
- o I/O roda numa thread própria: handler bloqueante não atrasa o ack, mas continua atrasando o próprio turno;
- GoAway sem perda e reconexão com backoff;
- 401/403/404/1008 no boot: `StreamRejectedError` e exit 1; sinal antes do `welcome` (ou `request_shutdown()` antes do `start_consume`): `StreamClosedError` e exit 1;
- SIGTERM/SIGINT depois do boot: drena a fila por até 15 s e sai com 0; um segundo sinal mata na hora;
- arquivos e ID Positiva continuam no HTTP; o `StreamConsumer` é de uso único.

```python
from chatgraph import is_session_not_owned

try:
    await usercall.send('Mensagem')
except Exception as e:
    if is_session_not_owned(e):
        return None
    raise
```

**Gotchas**

- No stream, comando depois de `TransferToMenu` ou fallback falha com `SessionNotOwnedError` (no HTTP passava). O `UserCall` embrulha a exceção: use `is_session_not_owned(e)`. `usercall.set_observation` só loga o erro.
- `time.sleep` em handler `async` continua travando o turno.
- Observation que não é JSON vira `nack` e o router manda ao fallback (no queue a mensagem era descartada com log).
- Exemplo completo, com Dockerfile: `examples/stream/` (bot de eco; `STREAM_ECHO_POD` entra no texto).
