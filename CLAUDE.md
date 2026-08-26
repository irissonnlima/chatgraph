# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`chatgraph` é uma **biblioteca** (não uma aplicação) para construir chatbots orientados a rotas.
Este arquivo trata de desenvolver a biblioteca. Para *usá-la* em um bot, a referência de API
está em `.github/skills/chatgraph-framework/SKILL.md`.

## Comandos

O ambiente real de trabalho é o `.venv/` do repositório. `taskipy` **não** está instalado nele,
então as tasks `poetry run task test|lint|format` documentadas no README e no PROGRESS.md não
funcionam — use os binários diretamente:

```bash
.venv/bin/python -m pytest tests/unit -q            # suíte rápida (500 testes, ~20s)
.venv/bin/python -m pytest tests/unit/test_agent_executor.py -v          # um arquivo
.venv/bin/python -m pytest tests/unit/test_agent_executor.py::TestNome::test_caso -v   # um teste
.venv/bin/python -m pytest -m integration -v        # integração (auto-skip sem env vars)
.venv/bin/ruff check chatgraph                      # lint
.venv/bin/ruff format .                             # format (aspas simples, linha 79)
```

`pytest-asyncio` roda em modo strict (sem `asyncio_mode` no `pyproject.toml`): todo teste async
precisa de `@pytest.mark.asyncio` explícito.

**O lint não está limpo e isso é pré-existente.** Em 2026-08-14, `ruff check .` reportava 775
erros (174 em `chatgraph/`, 590 em `tests/`), dominados por `PLR6301` (no-self-use nos testes) e
`E501`; `ruff format --check` acusava 7 arquivos. Não trate esses erros como regressão da sua
mudança, e não faça um mutirão de correção junto com uma feature — verifique apenas os arquivos
que você tocou.

Testes de integração leem `ROUTER_API_BASE_URL` (+ `_USERNAME`/`_PASSWORD`) e são **pulados
silenciosamente** se ela não estiver definida — um "tudo verde" pode significar "nada rodou".
A lista completa de env vars está em `.env.example`.

## Arquitetura

Pipeline de um turno:

```
RabbitMQ → MessageConsumer → ChatbotApp.process_message → default_functions (regex)
        → guard (auth_level) → handler da rota → __process_func_response → UserCall → RouterHTTPClient
```

Pontos que não se deduzem lendo um arquivo só:

- **O despacho usa apenas o último segmento da rota.** `process_message` calcula
  `route.split('.')[-1]` e busca essa chave em `self.__routes`, enquanto os decorators registram
  o nome literal passado. Ou seja: registre handlers com o **nome folha** (`@app.route('choice')`),
  nunca com o caminho pontuado (`'start.choice'` fica inalcançável). O caminho pontuado é a
  *posição* do usuário, mantida no backend — não a chave de registro. O README ainda mostra o
  formato antigo com ponto; ele está desatualizado.
- **O retorno do handler é a API de efeitos.** `__process_func_response` faz dispatch por tipo:
  `Message`/`File` envia, `Route` avança e espera nova mensagem, `RedirectResponse` reexecuta o
  pipeline no mesmo turno, `EndChatResponse`/`TransferToMenu` encerram, `BackgroundTask` roda e
  encadeia o próprio retorno, `list`/`tuple` processa em sequência. Retornar `None`/falsy
  **duplica o último segmento** da rota atual (mecanismo de "fica no nó"); `Route.get_previous()`
  desduplica segmentos repetidos ao voltar. Adicionar um novo tipo de resposta = adicionar um
  ramo aqui, e não lógica no handler.
- **`MAX_REDIRECT_DEPTH = 5`** (`bot/chatbot_model.py`) corta cadeias de `RedirectResponse` no
  mesmo turno. Sem isso um handler (ou agente de IA) em ciclo recursa até estourar a pilha e
  travar o consumer. `MESSAGE_IN` só é gravado no histórico em `_redirect_depth == 0`, senão a
  mesma mensagem entraria várias vezes com rotas diferentes.
- **Handlers podem ser sync ou async.** Sync roda em `run_in_executor`, então um handler sync
  **não pode** `await` — handlers com agente de IA precisam ser `async`.
- **Injeção de parâmetros é por anotação de tipo**, não por nome: `build_route_entry`
  (`bot/route_registry.py`) mapeia `{tipo: nome_do_param}`. Dois parâmetros com a mesma anotação
  colidem (o último vence) — limitação conhecida e documentada no módulo.
- **Não existe estado local.** Todo estado de usuário/sessão vive na API externa via
  `RouterHTTPClient`; `Container.get_router_client()` é o singleton (lê `ROUTER_URL`/`ROUTER_TOKEN`).
  Não introduza cache nem banco local sem decisão explícita.
- **Histórico e log de erro são fire-and-forget.** Os hooks de `HistoryStore` e o `LogPublisher`
  capturam `BaseException` e só emitem warning — observabilidade nunca derruba o turno. Se você
  adicionar um hook, mantenha esse contrato. `history_store=None` e `LogPublisher` sem
  `LOG_RABBIT_QUEUE` são no-ops válidos (retrocompatibilidade).

### `chatgraph/agent/` — extra opcional

Port fiel do protocolo **single-agent** do projeto irmão `chatgraph-go` (uma chamada de LLM decide
navegação *e* escreve a resposta). Regras que orientam mudanças aqui:

- `pydantic` é dependência **só** deste módulo (extra `chatgraph[agent]`). Os símbolos de agente
  são exportados de forma lazy no `chatgraph/__init__.py` via `__getattr__` (PEP 562), para que
  quem não instalou o extra não pague o custo nem quebre. Ao adicionar um export de agente,
  registre-o em `_AGENT_EXPORTS` **e** em `__all__` (o `# ruff: noqa: F822` no topo existe por isso).
- O executor **não executa efeitos**: ele devolve uma lista dos tipos de retorno já existentes do
  framework, que o pipeline processa sem alteração. Preserve essa separação.
- Paridade com o Go é o critério de projeto: `prompts.py` e `schema.py` são ports literais.
  Divergências devem ser conscientes e registradas (a atual: `transfer_menu` seleciona menu por
  **name**, porque o client Python não transfere por queue).
- Proteções do turno que existem por motivo específico, não as remova sem substituto: dedup de
  tool por `result_key`, `MAX_ATTEMPTS_PER_TOOL = 2`, guard de self-redirect, alvo de rota
  desconhecido vira "none", transfer inválido falha **antes** de qualquer side effect.

## Convenções

- **Commits em português do Brasil**, Conventional Commits (`feat`, `fix`, `chore`, `refactor`,
  `test`, `docs`, `style`, `perf`) — ex.: `feat(agent): adiciona guardrails de saída`.
- **Logs sempre via `UserLoggerManager`**, nunca `print`: dentro de rota use `usercall.logger`
  (vai para `chatgraph_logs/{user_id}_{company_id}.log`); fora de rota,
  `UserLoggerManager.get_system_logger()`.
- **Injeção de dependência manual** por construtor; sem framework de DI, sem prefixo `I` em
  interfaces. Contratos plugáveis usam `typing.Protocol` (ex.: `HistoryStore`), não ABC.
- **Docstrings e comentários em português**, seguindo o código existente. Comentário bom aqui
  explica *por que* a proteção existe (ver `MAX_REDIRECT_DEPTH`), não o que a linha faz.
- Testes agrupados em classes por unidade sob teste (`Test<Nome>`), fixtures em `conftest.py`,
  HTTP mockado com `respx`, marcadores `@pytest.mark.unit` / `@pytest.mark.integration`.

## Notas do repositório

- **A CLI não está instalada.** `[project.scripts]` no `pyproject.toml` está comentado, então o
  comando `chatgraph` documentado no README não existe; `chatgraph/cli/` só roda via
  `python -m` / import direto. Também é o módulo mais antigo (usa gRPC, imports fora do padrão).
- `[project] dev-dependencies` no `pyproject.toml` é um campo **não padrão** e ignorado pelos
  instaladores; as dev deps efetivas estão em `[dependency-groups] dev`. Existem `poetry.lock` e
  `uv.lock` no repo — confirme qual gerenciador está sendo usado antes de mexer em dependências.
- Não há CI configurado (`.github/workflows/` não existe): a validação antes de commitar é manual.
- `chatgraph/pb/` é **gerado** a partir do protobuf — não edite à mão.

## Contexto adicional

- `PROGRESS.md` — linha do tempo, decisões técnicas com justificativa e backlog priorizado.
  Mantenha-o atualizado ao concluir uma área.
- `docs/gaps-go-to-python.md` e `docs/gaps-python-to-go.md` — paridade com o `chatgraph-go`; é a
  fonte de verdade sobre o que falta portar (timeout por rota, route triggers, `validate_routes`,
  helper de teste tipo `EngineTester`).
- `.github/copilot-instructions.md` define um fluxo de agentes (Architect → Developer →
  CodeReviewer, definidos em `.github/agents/`) usado pelo Copilot; não é carregado pelo Claude
  Code, mas as convenções de código e commit dele são as mesmas resumidas acima.
