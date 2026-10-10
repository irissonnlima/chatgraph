# Changelog

Todas as mudanças relevantes do `chatgraph` ficam neste arquivo. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [versionamento semântico](https://semver.org/lang/pt-BR/).

Histórico anterior a esta seção: `PROGRESS.md` e `git log`.

## [1.5.0] — 2026-10-10

### Adicionado
- Transporte stream por WebSocket (`ROUTER_TRANSPORT=stream`, `ROUTER_MENUS`).
- `StreamConsumer`, `RouterStreamClient` e `StreamOptions`.
- Erros `StreamRejectedError`, `SessionNotOwnedError`, `CommandTimeoutError`, `ConnectionLostError` e `StreamClosedError`, e o helper `is_session_not_owned`.
- Exemplo `examples/stream` com Dockerfile.
- Dependência `websockets>=15.0`.
- Modo `ROUTER_TRANSPORT=dual` (transição `queue` → `stream`): `DualConsumer` consome a fila RabbitMQ e mantém a conexão stream, com todas as ações por HTTP, `"mode":"dual"` no `hello` e leitura de `welcome.transport`. O lado stream nunca derruba o processo no boot (401/403/1008 e 404 em nova tentativa a cada 30 s).
- `StreamConsumer` aceita `tolerant`, `mode` e `actions_via_http`; `StreamOptions` aceita `tolerant` e `mode`.

### Alterado
- `ChatbotApp()` sem consumer escolhe o transporte por `ROUTER_TRANSPORT`.
- `RABBIT_*` não são obrigatórias no stream.
- `ROUTER_TRANSPORT` aceita `queue`, `stream` ou `dual`.
- O log `Stream connected` ganha `router_transport=<transport>`.
- Turno da fila interrompido por cancelamento (SIGTERM no `dual`, SIGINT no `queue`) volta para a fila em vez de ir para o dead-letter `log_error`.
- `ROUTER_URL` é normalizada da mesma forma no HTTP e no stream: só o host é o formato recomendado; `/v1` e `/v1/actions` continuam aceitos.
- `pytest-asyncio` e `respx` no grupo `dev`.

### Corrigido
- `ROUTER_URL` só com o host (o formato do `.env.example`) quebrava o `RouterHTTPClient`, que chamava `<host>/actions/…` sem `/v1`.

### Notas de migração
- `queue` continua o padrão e não muda.
- `dual` exige as `RABBIT_*` do `queue` mais `ROUTER_MENUS` (padrão: `RABBIT_QUEUE`) e o vínculo do token em `token_menus`; com o router em `queue`, a conexão stream só fica registrada, sem receber mensagens.
- Nenhuma `ROUTER_URL` em uso precisa mudar: as formas `…/v1` e `…/v1/actions` resolvem como antes.
- No stream, o token precisa de vínculo em `token_menus` para cada menu declarado.
- No stream, comando depois de `TransferToMenu` ou de fallback falha com `SessionNotOwnedError` (no HTTP passava).
- No stream, observation que não é JSON vira `nack` e o router manda a mensagem ao fallback (no queue ela era descartada com log).
- No stream, sinal antes do `welcome` (ou `request_shutdown()` antes do `start_consume`) sai com código 1; SIGTERM depois do boot drena a fila por até 15 s e sai com 0.
