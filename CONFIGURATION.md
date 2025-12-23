# ChatGraph - Exemplos de Configuração

Este documento mostra como configurar o ChatGraph para controlar a verbosidade e logging.

## 📋 Índice

1. [Desabilitando Logs Completamente](#desabilitando-logs-completamente)
2. [Configurando via Código](#configurando-via-código)
3. [Configurando via Variável de Ambiente](#configurando-via-variável-de-ambiente)
4. [Configurando Nível de Log](#configurando-nível-de-log)
5. [Customizando o Console](#customizando-o-console)

---

## 1. Desabilitando Logs Completamente

### Opção A: Usando `configure()`

```python
from chatgraph import ChatbotApp, configure

# Desabilitar todos os logs antes de usar o chatbot
configure(verbose=False)

app = ChatbotApp()

@app.route('start')
async def start(rota, usercall):
    # Nenhum log será exibido
    await usercall.send('Mensagem')
```

### Opção B: Usando o objeto `config`

```python
from chatgraph import ChatbotApp, config

# Desabilitar logs
config.verbose = False

# Ou usar métodos
config.disable_logging()

app = ChatbotApp()
```

### Opção C: Via Variável de Ambiente

```bash
# Linux/Mac
export CHATGRAPH_VERBOSE=false

# Windows (PowerShell)
$env:CHATGRAPH_VERBOSE="false"

# Windows (CMD)
set CHATGRAPH_VERBOSE=false
```

```python
from chatgraph import ChatbotApp

# A configuração será lida automaticamente da variável de ambiente
app = ChatbotApp()
```

---

## 2. Configurando via Código

### Configuração Completa

```python
from chatgraph import configure
from rich.console import Console

# Configurar tudo de uma vez
configure(
    verbose=True,           # Habilita logs
    log_level='INFO',       # Nível de log
    console=Console()       # Console customizado (opcional)
)
```

### Habilitando/Desabilitando Dinamicamente

```python
from chatgraph import config, ChatbotApp

app = ChatbotApp()

@app.route('start')
async def start(rota, usercall):
    # Logs habilitados
    await usercall.send('Mensagem 1')
    
    # Desabilitar temporariamente
    config.disable_logging()
    await usercall.send('Mensagem 2')  # Sem log
    
    # Habilitar novamente
    config.enable_logging()
    await usercall.send('Mensagem 3')  # Com log
```

---

## 3. Configurando via Variável de Ambiente

### Arquivo `.env`

```env
# Habilita/desabilita logs (true|false|1|0|yes|no|on|off)
CHATGRAPH_VERBOSE=true

# Nível de log (DEBUG|INFO|WARNING|ERROR|CRITICAL)
CHATGRAPH_LOG_LEVEL=INFO
```

### Carregar no código

```python
from dotenv import load_dotenv
from chatgraph import ChatbotApp

# Carregar variáveis de ambiente
load_dotenv()

# ChatGraph lerá automaticamente:
# - CHATGRAPH_VERBOSE
# - CHATGRAPH_LOG_LEVEL

app = ChatbotApp()
```

---

## 4. Configurando Nível de Log

### Níveis Disponíveis

- `DEBUG` - Mostra tudo (mais detalhado)
- `INFO` - Informações normais (padrão)
- `WARNING` - Apenas avisos e erros
- `ERROR` - Apenas erros
- `CRITICAL` - Apenas erros críticos

### Exemplo

```python
from chatgraph import configure

# Mostrar apenas avisos e erros
configure(log_level='WARNING')

# Mostrar tudo (debug)
configure(log_level='DEBUG')

# Mostrar apenas erros
configure(log_level='ERROR')
```

### Via Variável de Ambiente

```bash
export CHATGRAPH_LOG_LEVEL=WARNING
```

---

## 5. Customizando o Console

### Console Customizado

```python
from chatgraph import configure
from rich.console import Console

# Criar console customizado
custom_console = Console(
    width=120,              # Largura personalizada
    force_terminal=True,    # Forçar cores
    color_system='256',     # Sistema de cores
    legacy_windows=False    # Suporte Windows moderno
)

# Configurar ChatGraph para usar seu console
configure(console=custom_console)
```

### Console que grava em arquivo

```python
from chatgraph import configure
from rich.console import Console

# Console que grava em arquivo
with open('chatgraph.log', 'w', encoding='utf-8') as f:
    console_with_file = Console(file=f, record=True)
    configure(console=console_with_file)
    
    # Usar chatbot normalmente
    # Logs serão gravados no arquivo
```

---

## 📦 Exemplo Completo de Produção

```python
import os
from dotenv import load_dotenv
from chatgraph import ChatbotApp, configure, config
from rich.console import Console

# Carregar .env
load_dotenv()

# Configuração baseada no ambiente
is_production = os.getenv('ENVIRONMENT') == 'production'

if is_production:
    # Em produção: apenas erros
    configure(
        verbose=True,
        log_level='ERROR'
    )
else:
    # Em desenvolvimento: tudo
    configure(
        verbose=True,
        log_level='DEBUG'
    )

# Criar aplicação
app = ChatbotApp()

@app.route('start')
async def start(rota, usercall):
    await usercall.send('Olá!')
    
@app.route('option')
async def option(rota, usercall):
    # Suprimir logs temporariamente
    old_verbose = config.verbose
    config.verbose = False
    
    try:
        # Operação silenciosa
        await usercall.send('Processando...')
    finally:
        # Restaurar configuração
        config.verbose = old_verbose

# Iniciar
app.start()
```

---

## 🎯 Casos de Uso Comuns

### 1. Biblioteca em Produção (sem logs)

```python
from chatgraph import configure

configure(verbose=False)
```

### 2. Desenvolvimento (tudo detalhado)

```python
from chatgraph import configure

configure(
    verbose=True,
    log_level='DEBUG'
)
```

### 3. Testes Automatizados (silencioso)

```python
from chatgraph import config

# No conftest.py ou setup de testes
config.verbose = False
```

### 4. Logs apenas para erros

```python
from chatgraph import configure

configure(
    verbose=True,
    log_level='ERROR'
)
```

---

## 🔍 Verificando Configuração Atual

```python
from chatgraph import config

print(f'Verbose: {config.verbose}')
print(f'Log Level: {config.log_level}')
print(f'Console: {config.console}')
```

---

## ⚙️ Valores Padrão

| Configuração | Padrão | Variável de Ambiente |
|---|---|---|
| `verbose` | `True` | `CHATGRAPH_VERBOSE` |
| `log_level` | `INFO` | `CHATGRAPH_LOG_LEVEL` |
| `console` | `Console()` | - |

---

## 📝 Notas Importantes

1. **Configuração Global**: As configurações afetam todas as instâncias do ChatGraph
2. **Thread-Safe**: A configuração é segura para uso em ambientes multi-thread
3. **Performance**: Desabilitar logs (`verbose=False`) melhora ligeiramente a performance
4. **Compatibilidade**: Funciona em Linux, macOS e Windows

---

## 🐛 Troubleshooting

### Logs não aparecem mesmo com `verbose=True`

- Verifique se há variável de ambiente `CHATGRAPH_VERBOSE=false`
- Verifique o `log_level` (se estiver em `ERROR`, não mostrará `INFO`)

### Logs aparecem mesmo com `verbose=False`

- Certifique-se de configurar **antes** de criar instâncias
- Verifique se há múltiplas configurações conflitantes

### Caracteres quebrados no Windows

```python
from rich.console import Console

console = Console(legacy_windows=False)
configure(console=console)
```
