# Lacunas: Python → Go

Funcionalidades presentes no `chatgraph` (Python) que **não existem** no `chatgraph-go`.
Ordenadas por impacto estimado.

---

## 1. Sistema de autorização por rota (`auth_level` + `default_guard`)

**Prioridade: Alta**

No Python, cada rota pode declarar um nível de acesso mínimo. O `default_guard` verifica o `AuthLevel` do usuário e redireciona para `menu_id_positiva` se o acesso for insuficiente.

```python
@app.route("dados_sensiveis", auth_level="write")
async def handler(usercall: UserCall):
    ...
```

`AuthLevel` é um enum ordenado: `blocked < unknown < read < write`, com suporte especial para `internal` (verificação de vínculo interno).

**O que existe no Go (parcial):**
`ProtectedRouteOps{Route}` apenas redireciona para uma rota se o usuário "não tem acesso", mas não define o que é "ter acesso" — a lógica de verificação fica fora do framework.

**O que falta:**
- Enum `AuthLevel` com ordenação (`blocked < unknown < read < write`)
- Campo `AuthLevel` em `UserState.User.Identity`
- Lógica de `guard` configurável no `Engine` (equivalente ao `default_guard`)
- Flag `internal` em `UserState.User`

---

## 2. Logger por usuário (`UserLoggerManager`)

**Prioridade: Média**

No Python, cada `UserCall` expõe um `logger` isolado por `(user_id, company_id)`, com suporte a log em arquivo por usuário via `UserLoggerManager`.

```python
usercall.logger.info("Usuário entrou na rota de pedidos")
usercall.logger.debug(f"CPF={usercall.user.identity.cpf}")
```

**O que falta no Go:**
- Logger estruturado por usuário acessível via `ctx`
- Suporte a log em arquivo por usuário (ex: `chatgraph_logs/<user_id>.log`)
- Nível de log configurável globalmente

---

## 3. `user_message` em `TransferToMenu`

**Prioridade: Baixa**

No Python, `TransferToMenu` recebe um `user_message` que é enviado automaticamente após a transferência.

```python
return TransferToMenu(menu="menu_principal", user_message="inicio")
```

**O que falta no Go:**
- Campo `UserMessage string` na struct `TransferToMenu`
- Envio automático da mensagem pelo adapter após a transferência

---
