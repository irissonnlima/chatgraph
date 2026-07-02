---
name: chatgraph-framework
description: "Use when: implementing a chatbot with chatgraph, creating routes with @app.route or @router.route, using UserCall, Route, Message, File, Button, EndChatResponse, RedirectResponse, TransferToMenu, TransferToHuman, BackgroundTask, setting up ChatbotApp, ChatbotRouter, include_router, configuring RabbitMQ consumer, adding per-user file logging with UserLoggerManager, integrating chatgraph in a new Python project."
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
ROUTER_URL=http://localhost:8000
ROUTER_TOKEN=meu_token

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

### `EndChatResponse(end_chat_id, end_chat_name?, observations?)` — Encerra o chat
```python
return EndChatResponse('voll_ended')
return EndChatResponse('', end_chat_name='Encerrado pelo usuário', observations='motivo')
```

### `TransferToMenu(menu, user_message, route?)` — Transfere para outro menu
```python
return TransferToMenu('p0299_suporte_ti', 'Transferindo...')
return TransferToMenu('p0299_suporte_ti', 'Transferindo...', route='etapa_inicial')  # inicia em rota específica
```

### `TransferToHuman(campaign_id?, campaign_name?, observations?)` — Transfere para humano
```python
return TransferToHuman(campaign_name='Suporte N2')
```

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
