# ChatGraph - Roadmap de Melhorias

## 📋 Visão Geral

Este roadmap define as melhorias planejadas para o projeto ChatGraph, organizadas em sprints priorizados por impacto e esforço.

---

## 🎯 Sprint 1: Fundação (1-2 semanas)

### ✅ Item 3: Console Logging para Usuário

**Prioridade:** 🔴 Alta  
**Status:** 🚧 Em Progresso  
**Responsável:** TBD  
**Prazo:** Semana 1

**Objetivo:** Implementar feedback visual usando Rich Console para informar o usuário sobre o funcionamento da aplicação.

**Escopo:**

- [x] Implementar logging no `UserCall`
  - [x] Método `send()` - feedback de envio de mensagens
  - [x] Método `__send()` - confirmação de mensagem texto
  - [x] Método `__send_file()` - status de upload/validação de arquivos
  - [x] Métodos de atualização de estado
- [ ] Implementar logging no `RouterHTTPClient`
  - [ ] Feedback de inicialização/conexão
  - [ ] Status de requisições HTTP
  - [ ] Erros de comunicação
- [ ] Implementar logging no `MessageConsumer`
  - [ ] Status de conexão RabbitMQ
  - [ ] Mensagens recebidas/processadas
  - [ ] Erros de processamento
- [ ] Implementar logging no `ChatbotApp`
  - [ ] Rotas registradas
  - [ ] Execução de handlers
  - [ ] Transições de estado

**Critérios de Sucesso:**

- ✅ Usuário vê feedback visual de todas as operações principais
- ✅ Erros são exibidos com contexto claro
- ✅ Código usa cores consistentes (verde=sucesso, amarelo=aviso, vermelho=erro)

---

### ✅ Item 4: Testes Unitários do Router

**Prioridade:** 🔴 Alta  
**Status:** ⏳ Pendente  
**Responsável:** TBD  
**Prazo:** Semana 2

**Objetivo:** Expandir cobertura de testes unitários do `RouterHTTPClient`.

**Escopo:**

- [ ] Testes para `set_session_route()`
  - [ ] Sucesso na atualização de rota
  - [ ] Erro quando sessão não existe
  - [ ] Validação de parâmetros
- [ ] Testes para `update_session_observation()`
  - [ ] Sucesso na atualização de observação
  - [ ] Erro quando sessão não existe
  - [ ] Validação de JSON
- [ ] Testes para `end_chat()`
  - [ ] Encerramento com tabulação válida
  - [ ] Erro quando end_action não existe
  - [ ] Validação de parâmetros
- [ ] Testes para `get_end_action()`
  - [ ] Busca de end_action por ID
  - [ ] Erro quando não encontrado
- [ ] Testes para `send_file()`
  - [ ] Envio de referência de arquivo
  - [ ] Validação de payload

**Meta de Cobertura:** 90%+ no `RouterHTTPClient`

---

## 🟡 Sprint 2: Consolidação (1-2 semanas)

### ✅ Item 2: Logging em Nível Debug

**Prioridade:** 🟡 Média  
**Status:** ⏳ Pendente  
**Responsável:** TBD  
**Prazo:** Sprint 2

**Objetivo:** Implementar sistema de logging estruturado para debug e troubleshooting.

**Escopo:**

- [ ] Configurar `logging` do Python
  - [ ] Arquivo de log rotativo
  - [ ] Níveis: DEBUG, INFO, WARNING, ERROR
  - [ ] Formato estruturado com timestamp
- [ ] Adicionar logs DEBUG em:
  - [ ] `RouterHTTPClient` - todas as requisições HTTP
  - [ ] `UserCall` - transformações de dados
  - [ ] `MessageConsumer` - processamento de mensagens
  - [ ] `ChatbotApp` - execução de rotas
- [ ] Criar utilitário de logging centralizado
- [ ] Documentar configuração de logs

**Arquivos de Log:**

- `logs/chatgraph.log` - Log geral
- `logs/chatgraph-error.log` - Apenas erros
- `logs/chatgraph-debug.log` - Debug completo

---

### ✅ Item 5: Testes de Integração do Router

**Prioridade:** 🟡 Média  
**Status:** ⏳ Pendente  
**Responsável:** TBD  
**Prazo:** Sprint 2

**Objetivo:** Criar testes de integração para fluxos completos do Router.

**Escopo:**

- [ ] Teste de fluxo de arquivo completo
  - [ ] Upload → Get → Delete
  - [ ] Validação de existência
  - [ ] Cleanup automático
- [ ] Teste de fluxo de sessão completo
  - [ ] Start → Update Route → Update Observation → End
  - [ ] Validação de estado
- [ ] Teste de fluxo de mensagem
  - [ ] Send Text → Send File → Get Session
- [ ] Configurar CI/CD para rodar testes
  - [ ] GitHub Actions
  - [ ] Variáveis de ambiente para API de teste

**Meta de Cobertura:** 80%+ nos fluxos principais

---

## 🟢 Sprint 3: Refinamento (Contínuo)

### ✅ Item 1: Ajustar Docstrings

**Prioridade:** 🟢 Baixa  
**Status:** ⏳ Pendente  
**Responsável:** TBD  
**Prazo:** Contínuo

**Objetivo:** Padronizar e melhorar docstrings em todos os módulos.

**Escopo:**

- [ ] Revisar docstrings do `RouterHTTPClient`
  - [ ] Formato Google Style
  - [ ] Args, Returns, Raises
  - [ ] Exemplos de uso
- [ ] Revisar docstrings do `UserCall`
- [ ] Revisar docstrings dos modelos
- [ ] Revisar docstrings do `ChatbotApp`
- [ ] Gerar documentação com Sphinx/MkDocs

**Padrão:**

```python
def method(self, param: str) -> dict:
    """
    Breve descrição do método.
    
    Descrição detalhada se necessário.
    
    Args:
        param: Descrição do parâmetro
        
    Returns:
        Descrição do retorno
        
    Raises:
        ValueError: Quando ocorre X
        Exception: Quando ocorre Y
        
    Example:
        >>> result = method("value")
        >>> print(result)
    """
```

---

### ✅ Item 6: Testes Unitários de Outros Módulos

**Prioridade:** 🟢 Baixa  
**Status:** ⏳ Pendente  
**Responsável:** TBD  
**Prazo:** Contínuo

**Objetivo:** Expandir cobertura de testes para módulos secundários.

**Escopo:**

- [ ] Testes para `ChatbotApp`
  - [ ] Registro de rotas
  - [ ] Execução de handlers
  - [ ] Tratamento de erros
- [ ] Testes para `Message` e subclasses
  - [ ] `TextMessage`
  - [ ] `ImageMessage`
  - [ ] `FileMessage`
- [ ] Testes para tipos de resposta
  - [ ] `RedirectResponse`
  - [ ] `EndChatResponse`
  - [ ] `TransferToMenu`
- [ ] Testes para `MessageConsumer`
  - [ ] Transformação de mensagens
  - [ ] Processamento de erros

**Meta de Cobertura:** 80%+ no projeto

---

### ✅ Item 7: Testes de Integração de Outros Módulos

**Prioridade:** 🟢 Baixa  
**Status:** ⏳ Pendente  
**Responsável:** TBD  
**Prazo:** Backlog

**Objetivo:** Criar testes de integração para módulos que dependem de serviços externos.

**Escopo:**

- [ ] Testes de integração com RabbitMQ
  - [ ] Mock de RabbitMQ com testcontainers
  - [ ] Teste de consumo de mensagens
  - [ ] Teste de processamento completo
- [ ] Testes end-to-end
  - [ ] Mensagem RabbitMQ → Processamento → Resposta API
  - [ ] Múltiplas rotas encadeadas
  - [ ] Cenários de erro

**Infraestrutura Necessária:**

- Docker Compose para serviços de teste
- Testcontainers para RabbitMQ
- API mock ou ambiente de staging

---

## 📊 Métricas de Progresso

### Cobertura de Testes Atual

- **RouterHTTPClient:** 16 testes unitários ✅
- **Modelos:** 78 testes unitários ✅
- **Integração:** 8 testes ✅
- **Total:** ~80% de cobertura

### Meta Final

- **Cobertura total:** 90%+
- **Testes unitários:** 150+
- **Testes de integração:** 20+
- **Documentação:** 100% dos métodos públicos

---

## 🎯 Próximos Passos Imediatos

1. **Esta semana:**
   - ✅ Implementar console logging no `UserCall`
   - ✅ Implementar console logging no `RouterHTTPClient`

2. **Próxima semana:**
   - [ ] Implementar console logging no `MessageConsumer`
   - [ ] Criar testes para métodos faltantes do Router

3. **Mês seguinte:**
   - [ ] Configurar logging estruturado
   - [ ] Criar testes de integração de fluxos completos

---

## 📝 Notas

- **Data de início:** 26 de novembro de 2025
- **Última atualização:** 26 de novembro de 2025
- **Versão:** 1.0.0

**Convenções de Status:**

- ⏳ Pendente
- 🚧 Em Progresso
- ✅ Concluído
- ❌ Cancelado
- 🔄 Em Revisão

**Prioridades:**

- 🔴 Alta - Impacto crítico, implementar primeiro
- 🟡 Média - Importante, mas não urgente
- 🟢 Baixa - Desejável, implementar quando possível
