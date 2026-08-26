# Lacunas: Go → Python

Funcionalidades presentes no `chatgraph-go` que **não existem** no `chatgraph` (Python).
Ordenadas por impacto estimado em produção.

---

## 0. Agentes de IA — ✅ PARCIALMENTE RESOLVIDO (v1.4.0)

O módulo `chatgraph/agent/` porta o protocolo **single-agent** do Go
(`GenerateProtocol` + `ExecuteSingleAgent`): `Agent`, tools locais com
`@agent.tool`, cliente OpenRouter próprio (httpx, retry/backoff),
normalização de JSON Schema para Structured Outputs, prompts portados,
executor com as proteções do Go (dedup por `result_key`, máx. 2
tentativas por tool, self-redirect guard, redirect silencioso, merge
aditivo de observation) e histórico com pareamento assistant/tool
(`trim_safe`). Extra opcional `chatgraph[agent]` (pydantic>=2).

Desde então (2026-08-17): `end_actions`/`EndActionInfo` para
`end_session` (seleção por name/id, mesmo critério do `transfer_menu`),
enum de `menu`/`end_action_id` por Agent no Structured Output, um
guardrail de saída específico — re-prompt corretivo de 1 tentativa via
`AgentContext.last_action_error` quando o modelo escolhe um
menu/end_action inexistente — e `Agent.validate_config` (opt-in,
confere no boot se os menus/end_actions configurados existem no
router). Também um extra sem equivalente no Go: `generate_content`
(`chatgraph/agent/content.py`), chamada de LLM tiro-único desacoplada
do protocolo de chat/roteamento, para analisar dados internos do bot.

**Ainda faltam** (extensões futuras, design já acomoda):
- Protocolo two-agent (`DecideRoute` + `Speak`, router barato + speaker premium)
- MCP (stdio/SSE/HTTP/JSON-RPC + registry) — tools hoje são locais
- Memória de longo prazo (`MemoryContext` cross-session)
- Guardrails de entrada/saída (o único hoje é a correção de ação
  inválida acima; nada cobre conteúdo impróprio na entrada/saída)
- `recoverObservation` (re-run do router em rotas "collect")
- Transfer por queue (divergência consciente: o client Python
  transfere por **name** de menu, e `end_session` seleciona a end
  action pelo mesmo critério)

---

## 1. Timeout automático de handler

**Prioridade: Alta**

No Go, cada rota possui um `TimeoutRouteOps{Duration, Route}`. Quando o handler ultrapassa a duração configurada, a execução é cancelada via `context.Context` e o usuário é redirecionado para uma rota de timeout.

```go
engine.RegisterRoute("slow_task", handler, chat.RouterHandlerOptions{
    Timeout: &chat.TimeoutRouteOps{
        Duration: 30 * time.Second,
        Route:    "timeout_route",
    },
})
```

**O que falta no Python:**
- Suporte a `timeout` por rota no decorador `@app.route()` / `@router.route()`
- Cancelamento do handler assíncrono quando o timeout é atingido
- Redirect automático para rota de fallback

---

## 2. Loop protection — ✅ PARCIALMENTE RESOLVIDO (v1.4.0)

No Go, o `Engine` rastreia quantas vezes consecutivas o mesmo redirect ocorreu. Se o limite for atingido (`LoopCountRouteOps{Count, Route}`), o usuário é enviado para uma rota de fallback.

**Implementado no Python (v1.4.0):** `MAX_REDIRECT_DEPTH = 5` em
`chatbot_model.py` limita a profundidade de redirects encadeados num
mesmo turno (a recursão de `RedirectResponse` em `process_message`).
Ao estourar, o turno é encerrado com erro no log — o `set_route` já
ocorreu, então a próxima mensagem cai na rota destino. A mesma
proteção evita que um agente de IA em ciclo trave o consumer, e a
reentrada por redirect não regrava MESSAGE_IN no histórico.

**O que ainda falta (paridade completa):**
- Contador por rota (visitas consecutivas à MESMA rota, como no Go)
- Configuração de limite por rota
- Redirect automático para rota de fallback ao atingir o limite

---

## 3. Route Triggers (regex globais por rota)

**Prioridade: Média-Alta**

No Go, `RouteTrigger{Regex, Route}` permite que qualquer mensagem que bata com um padrão seja redirecionada para uma rota específica **antes** da execução normal. Pode ser configurado globalmente no `Engine` ou por rota.

```go
engine := chat.NewEngine[Obs](chat.RouterHandlerOptions{
    Triggers: []chat.RouteTrigger{
        {Regex: `(?i)^cancelar$`, Route: "cancelar_route"},
        {Regex: `(?i)^ajuda$`,    Route: "help_route"},
    },
})
```

**O que existe no Python (parcial):**
O `ChatbotApp` já possui `DEFAULT_FUNCTION` — um dicionário `{regex: callable}` executado antes das rotas (ex: `voltar`). Porém a implementação atual executa uma função diretamente em vez de redirecionar para uma rota nomeada, e não é configurável por rota individualmente.

**O que falta:**
- Suporte a triggers por rota individualmente
- Semântica de redirect para rota nomeada (em vez de executar função inline)

---

## 4. Route validation

**Prioridade: Média**

No Go, `engine.ValidateRoutes()` verifica em tempo de inicialização que todas as rotas referenciadas (timeout, loop, protected, triggers) estão de fato registradas, evitando erros silenciosos em produção.

```go
if err := engine.ValidateRoutes(); err != nil {
    log.Fatal(err)
}
```

**O que falta no Python:**
- Método `validate_routes()` no `ChatbotApp` que levanta erro se qualquer rota referenciada (em redirects, transfers, etc.) não estiver registrada

---

## 5. `EngineTester` — helper de teste para handlers

**Prioridade: Média**

No Go, `EngineTester` fornece um `mockExecutor` que captura todas as ações executadas pelo handler (mensagens enviadas, observações salvas, rotas definidas, arquivos buscados/enviados) e permite validá-las em assertions.

```go
tester := chat.NewEngineTester[Obs](t, engine)
tester.Execute(
    userState,
    message,
    []chat.ExpectedAction{
        {Type: chat.ExecSendMessage, Message: &expectedMsg},
        {Type: chat.ExecSetRoute, Route: "next_route"},
    },
    expectedReturn,
)
```

**O que falta no Python:**
- Classe `ChatbotTester` (ou similar) que mocka o `RouterHTTPClient` e captura chamadas em sequência
- Tipos `ExpectedAction` para `send_message`, `set_observation`, `set_route`, `get_file`, `upload_file`
- Integração com `pytest` e as fixtures existentes em `tests/unit/conftest.py`

---

## 6. Upload de arquivo a partir de bytes (`load_file_bytes`)

**Prioridade: Baixa**

No Go, `ctx.LoadFileBytes("nome.txt", []byte{...})` permite fazer upload de conteúdo gerado em memória sem precisar de um arquivo em disco.

**O que falta no Python:**
- Método equivalente em `UserCall` para upload a partir de `bytes` diretamente

---

## 7. Deduplicação de arquivos via SHA256

**Prioridade: Baixa**

No Go, o upload de um arquivo já enviado anteriormente retorna o registro cacheado (identificado por hash SHA256), evitando uploads duplicados.

**O que falta no Python:**
- Verificação de hash antes do upload em `RouterHTTPClient.upload_file()`

---

## 8. `DepartmentID` e `LastUpdate` em `EndChatResponse`

**Prioridade: Baixa**

O `EndAction` do Go possui dois campos extras que o `EndChatResponse` do Python não tem:

| Campo | Go (`EndAction`) | Python (`EndChatResponse`) |
|---|---|---|
| `DepartmentID` | `int` | ❌ ausente |
| `LastUpdate` | `string` (timestamp) | ❌ ausente |

---
