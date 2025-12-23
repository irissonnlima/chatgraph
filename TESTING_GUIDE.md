# Guia Completo de Testes - ChatGraph

Este documento contém informações detalhadas sobre a estrutura de testes do ChatGraph, incluindo testes unitários e de integração.

## 📂 Estrutura de Testes

```
tests/
├── __init__.py                  # Pacote principal de testes
├── unit/                        # Testes unitários (rápidos, isolados, usam mocks)
│   ├── __init__.py
│   ├── conftest.py              # Fixtures para testes unitários
│   ├── test_router_http_client.py
│   ├── test_models_actions.py
│   ├── test_models_message.py
│   └── test_models_userstate.py
└── integration/                 # Testes de integração (chamadas reais para APIs)
    ├── __init__.py
    ├── conftest.py              # Fixtures para testes de integração
    └── test_router_client_integration.py
```

## 🎯 Diferenças: Testes Unitários vs Integração

### Testes Unitários (`tests/unit/`)

**Características:**

- ✅ Testam componentes **isolados**
- ✅ Usam **mocks** (respx) para simular respostas HTTP
- ✅ **Rápidos** (executam em segundos)
- ✅ **Não dependem** de serviços externos
- ✅ Executam em **qualquer ambiente**
- ✅ Não requerem configuração adicional

**Quando usar:**

- Durante desenvolvimento ativo (feedback rápido)
- Em pre-commit hooks
- Para testar lógica de negócio
- Para validar estrutura de dados (dataclasses)
- Para testar tratamento de erros

**Exemplos:**

- Validar que `UserState.to_dict()` serializa corretamente
- Verificar inicialização de `RouterHTTPClient`
- Testar que mocks de API retornam tipos corretos

### Testes de Integração (`tests/integration/`)

**Características:**

- ✅ Testam **integração real** com APIs externas
- ✅ Validam **contratos** e **formatos de resposta** reais
- ✅ Detectam **mudanças na API** que podem quebrar o código
- ❌ **Lentos** (dependem de latência de rede)
- ❌ Dependem de **serviços disponíveis**
- ❌ Requerem **credenciais** e **ambiente configurado**

**Quando usar:**

- Antes de releases/deploys
- Para validar integração com API real
- Para detectar breaking changes na API
- Em pipelines CI/CD (com variáveis de ambiente)
- Para smoke tests em staging/production

**Exemplos:**

- Validar que `get_all_sessions()` retorna estrutura esperada da API real
- Verificar que autenticação funciona com credenciais reais
- Testar que uploads de arquivo funcionam corretamente

## 🚀 Executando Testes

### Testes Unitários (Recomendado para desenvolvimento)

```bash
# Todos os testes unitários
poetry run pytest tests/unit/ -v

# Arquivo específico
poetry run pytest tests/unit/test_router_http_client.py -v

# Classe específica
poetry run pytest tests/unit/test_router_http_client.py::TestRouterHTTPClientInit -v

# Teste específico
poetry run pytest tests/unit/test_router_http_client.py::TestRouterHTTPClientInit::test_init_with_basic_params -v

# Com cobertura
poetry run pytest tests/unit/ --cov=chatgraph --cov-report=html
poetry run start htmlcov/index.html  # Abre relatório no navegador
```

### Testes de Integração (Requer configuração)

#### 1️⃣ Configure as Variáveis de Ambiente

**Opção 1: Arquivo `.env`**

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite .env e adicione:
ROUTER_API_BASE_URL=https://api.example.com/v1/actions
ROUTER_API_USERNAME=seu_usuario
ROUTER_API_PASSWORD=sua_senha
```

**Opção 2: Export no terminal (Linux/Mac)**

```bash
export ROUTER_API_BASE_URL="https://api.example.com/v1/actions"
export ROUTER_API_USERNAME="seu_usuario"
export ROUTER_API_PASSWORD="sua_senha"
export ROUTER_API_TIMEOUT="60.0"
export TEST_USER_ID="user_test_001"
export TEST_COMPANY_ID="company_test_001"
```

**Opção 3: PowerShell (Windows)**

```powershell
$env:ROUTER_API_BASE_URL="https://api.example.com/v1/actions"
$env:ROUTER_API_USERNAME="seu_usuario"
$env:ROUTER_API_PASSWORD="sua_senha"
```

#### 2️⃣ Execute os Testes

```bash
# Todos os testes de integração
poetry run pytest tests/integration/ -v

# Usando marker
poetry run pytest -m integration -v

# Teste específico
poetry run pytest tests/integration/test_router_client_integration.py::TestRouterHTTPClientIntegrationSessions::test_get_all_sessions_real_api -v

# Com mais detalhes de erro
poetry run pytest tests/integration/ -vv
```

#### 3️⃣ Skip Automático

Se as variáveis **não estiverem configuradas**, os testes serão automaticamente pulados:

```
SKIPPED: Variáveis de ambiente não configuradas: ROUTER_API_BASE_URL. 
Configure as variáveis para executar testes de integração.
```

### Executando Todos os Testes

```bash
# Todos (unitários + integração)
poetry run pytest -v

# Apenas unitários (excluir integração)
poetry run pytest -m "not integration" -v

# Com cobertura completa
poetry run pytest --cov=chatgraph --cov-report=html --cov-report=term
```

## 🏷️ Markers do Pytest

Configurados em `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: marks tests as unit tests (fast, isolated, uses mocks)",
    "integration: marks tests as integration tests (slow, requires external services)",
]
```

**Uso:**

```bash
# Apenas testes unitários
poetry run pytest -m unit -v

# Apenas testes de integração
poetry run pytest -m integration -v

# Excluir testes de integração
poetry run pytest -m "not integration" -v
```

## 📊 Cobertura de Testes

### Gerar Relatório de Cobertura

```bash
# Gerar HTML
poetry run pytest tests/unit/ --cov=chatgraph --cov-report=html

# Abrir no navegador
poetry run start htmlcov/index.html  # Windows
open htmlcov/index.html              # macOS
xdg-open htmlcov/index.html          # Linux

# Terminal + HTML
poetry run pytest tests/unit/ --cov=chatgraph --cov-report=html --cov-report=term

# Com percentual mínimo (falha se < 80%)
poetry run pytest tests/unit/ --cov=chatgraph --cov-fail-under=80
```

### Taskipy (Atalhos)

Configurado em `pyproject.toml`:

```bash
# Executar testes com cobertura
poetry run task test

# Abrir relatório de cobertura
poetry run task start_cov
```

## 🔧 Configuração de Fixtures

### Fixtures de Testes Unitários (`tests/unit/conftest.py`)

```python
@pytest.fixture
def http_client_base_url():
    """URL base para testes unitários."""
    return 'http://localhost:8080/v1/actions'

@pytest.fixture
def respx_mock():
    """Mock HTTP com respx."""
    with respx.mock:
        yield respx
```

### Fixtures de Testes de Integração (`tests/integration/conftest.py`)

```python
@pytest.fixture
def skip_if_no_integration_env():
    """Skip se variáveis não configuradas."""
    # Implementado automaticamente

@pytest.fixture
async def real_http_client(integration_base_url, integration_username, integration_password):
    """Cliente HTTP real para testes de integração."""
    client = RouterHTTPClient(
        base_url=integration_base_url,
        username=integration_username,
        password=integration_password,
    )
    yield client
    await client.close()
```

## 🎨 Escrevendo Novos Testes

### Teste Unitário (com mock)

```python
import pytest
from chatgraph.services.router_http_client import RouterHTTPClient

@pytest.mark.asyncio
async def test_get_all_sessions(http_client_base_url, respx_mock):
    """Testa get_all_sessions com mock."""
    # Configurar mock
    respx_mock.get(f'{http_client_base_url}/session/').mock(
        return_value=httpx.Response(200, json={'data': []})
    )
    
    # Executar
    client = RouterHTTPClient(base_url=http_client_base_url)
    result = await client.get_all_sessions()
    
    # Validar
    assert isinstance(result, list)
    
    # Cleanup
    await client.close()
```

### Teste de Integração (API real)

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_all_sessions_real(real_http_client):
    """Testa get_all_sessions com API real."""
    async with real_http_client as client:
        sessions = await client.get_all_sessions()
        
        # Validar estrutura
        assert isinstance(sessions, list)
        if sessions:
            assert hasattr(sessions[0], 'chat_id')
            assert hasattr(sessions[0], 'platform')
```

## 🐛 Troubleshooting

### Problema: Testes de integração falhando

**Solução:**

1. Verifique variáveis de ambiente:

   ```bash
   echo $ROUTER_API_BASE_URL
   ```

2. Teste conectividade:

   ```bash
   curl $ROUTER_API_BASE_URL/session/
   ```

3. Valide credenciais
4. Execute com `-vv` para logs detalhados:

   ```bash
   poetry run pytest tests/integration/ -vv
   ```

### Problema: Testes unitários lentos

**Solução:**

- Execute testes paralelos (requer `pytest-xdist`):

  ```bash
  poetry add --group dev pytest-xdist
  poetry run pytest tests/unit/ -n auto
  ```

### Problema: Erro "respx not installed"

**Solução:**

```bash
poetry add --group dev respx
```

### Problema: Imports falhando

**Solução:**

```bash
# Reinstalar dependências
poetry install

# Verificar PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## 📝 Boas Práticas

### Durante Desenvolvimento

1. ✅ Execute testes unitários **frequentemente** (são rápidos)
2. ✅ Escreva testes **antes** de implementar (TDD)
3. ✅ Mantenha cobertura acima de **80%**
4. ✅ Use `respx` para mockar HTTP

### Antes de Commitar

1. ✅ Execute **todos os testes unitários**
2. ✅ Verifique cobertura de código
3. ✅ Execute linter: `poetry run task lint`
4. ✅ Formate código: `poetry run task format`

### Antes de Deploy

1. ✅ Execute **testes de integração** com staging
2. ✅ Valide com API real
3. ✅ Execute smoke tests
4. ✅ Verifique logs de erros

### Em CI/CD

1. ✅ Execute testes unitários em **todos os commits**
2. ✅ Execute testes de integração em **staging/production**
3. ✅ Configure variáveis de ambiente secretas
4. ✅ Gere relatórios de cobertura

## 🔐 Segurança

### Nunca commite

- ❌ Credenciais reais (`.env`)
- ❌ Tokens de API
- ❌ Senhas em código

### Sempre

- ✅ Use `.env.example` como template
- ✅ Configure secrets no CI/CD
- ✅ Use variáveis de ambiente
- ✅ Adicione `.env` ao `.gitignore`

## 📚 Recursos Adicionais

- [pytest Documentation](https://docs.pytest.org/)
- [respx Documentation](https://lundberg.github.io/respx/)
- [httpx Documentation](https://www.python-httpx.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

## 🎯 Checklist de Qualidade

Antes de fazer merge:

- [ ] Todos os testes unitários passando
- [ ] Cobertura > 80%
- [ ] Testes de integração validados (se aplicável)
- [ ] Código formatado (`poetry run task format`)
- [ ] Sem warnings de lint (`poetry run task lint`)
- [ ] Documentação atualizada
- [ ] CHANGELOG.md atualizado (se aplicável)

---

**Última atualização:** 14 de novembro de 2025
