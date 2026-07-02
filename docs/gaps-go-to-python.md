# Lacunas: Go → Python

Funcionalidades presentes no `chatgraph-go` que **não existem** no `chatgraph` (Python).
Ordenadas por impacto estimado em produção.

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

## 2. Loop protection

**Prioridade: Alta**

No Go, o `Engine` rastreia quantas vezes consecutivas o mesmo redirect ocorreu. Se o limite for atingido (`LoopCountRouteOps{Count, Route}`), o usuário é enviado para uma rota de fallback.

```go
// Padrão: 3 visitas consecutivas → redireciona para "loop_route"
engine.RegisterRoute("A", func(ctx *chat.Context[Obs]) chat.RouteReturn {
    return &chat.RedirectResponse{TargetRoute: "A"} // loop detectado na 4ª vez
})
```

**O que falta no Python:**
- Contador de redirects consecutivos para a mesma rota em `UserCall` / `ChatbotApp`
- Configuração de limite por rota ou global
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
