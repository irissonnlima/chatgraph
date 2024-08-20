# ChatGraph

**ChatGraph** é uma biblioteca Python projetada para facilitar a construção e gerenciamento de chatbots com roteamento flexível. 

Ela oferece uma estrutura para definir rotas de chatbot, processar mensagens e gerenciar o estado do usuário de maneira eficiente.

## Instalação

Você pode instalar o ChatGraph diretamente do PyPI:

```bash
pip install chatgraph
```

Link do PyPI: [ChatGraph no PyPI](https://pypi.org/project/chatgraph/)

## Estrutura da Biblioteca

### 1. `ChatbotApp`

A classe `ChatbotApp` é o núcleo da aplicação do chatbot. Ela gerencia as rotas definidas, processa as mensagens recebidas e lida com a lógica de navegação dentro do chatbot.

- **Métodos principais:**
  - `include_router`: Inclui um conjunto de rotas (definido por `ChatbotRouter`) na aplicação.
  - `route`: Decorador para associar funções a rotas específicas.
  - `start`: Inicia o consumo de mensagens do RabbitMQ.
  - `process_message`: Processa a mensagem recebida e executa a função correspondente à rota atual do usuário.

### 2. `ChatbotRouter`

A classe `ChatbotRouter` permite definir e agrupar rotas que podem ser facilmente incluídas na aplicação principal do chatbot.

- **Métodos principais:**
  - `route`: Decorador para adicionar uma função como uma rota no roteador.
  - `include_router`: Inclui outro roteador dentro do roteador atual, permitindo a construção modular das rotas.

### 3. `MessageConsumer` e `RabbitMessageConsumer`

A classe abstrata `MessageConsumer` define a interface para consumidores de mensagens no sistema do chatbot. A implementação concreta `RabbitMessageConsumer` consome mensagens de uma fila RabbitMQ, processa essas mensagens e envia respostas de acordo.

- **Métodos principais:**
  - `start_consume`: Inicia o consumo de mensagens do RabbitMQ.
  - `on_request`: Processa uma mensagem recebida e envia a resposta correspondente.
  - `load_dotenv`: Carrega as configurações do RabbitMQ a partir de variáveis de ambiente.

### 4. `UserState` e `SimpleUserState`

A classe abstrata `UserState` define a interface para o gerenciamento do estado do usuário. A implementação `SimpleUserState` usa um dicionário em memória para armazenar o estado atual do menu para cada usuário.

- **Métodos principais:**
  - `get_menu`: Retorna o menu atual associado a um ID de cliente.
  - `set_menu`: Define o menu atual para um ID de cliente.

### 5. `Message`

A classe `Message` encapsula os dados de uma mensagem enviada ou recebida pelo chatbot.

- **Atributos:**
  - `type`: Tipo da mensagem (ex. texto, imagem).
  - `text`: Conteúdo da mensagem.
  - `customer_id`: ID do cliente que enviou ou recebeu a mensagem.
  - `channel`: Canal de comunicação utilizado (ex. WhatsApp, SMS).
  - `customer_phone`: Número de telefone do cliente.
  - `company_phone`: Número de telefone da empresa.
  - `status`: Status da mensagem (opcional).

### 6. `ChatbotResponse` e `RedirectResponse`

Essas classes são usadas para definir a resposta do chatbot após o processamento de uma mensagem.

- **`ChatbotResponse`**: Contém uma mensagem de resposta e uma rota opcional.
- **`RedirectResponse`**: Define uma rota para a qual o chatbot deve redirecionar o fluxo.

### 7. `Route` e `RouteError`

A classe `Route` gerencia a navegação entre diferentes partes do fluxo do chatbot, permitindo obter a rota anterior e calcular a próxima rota com base na entrada do usuário.

- **Métodos principais:**
  - `get_previous`: Retorna o caminho anterior ao atual.
  - `get_next`: Monta e retorna o próximo caminho com base em uma parte fornecida.

A classe `RouteError` é uma exceção personalizada usada para indicar problemas relacionados à navegação nas rotas.

## Exemplo de Uso

Aqui está um exemplo básico de como configurar e utilizar o ChatGraph:

```python
from chatgraph import ChatbotApp, ChatbotRouter, SimpleUserState, RabbitMessageConsumer, ChatbotResponse

# Definindo rotas com ChatbotRouter
router = ChatbotRouter()

@router.route("start")
def say_hello():
    return ChatbotResponse(message="Hello! How can I assist you today?", route=".help")

@router.route(".help")
def provide_help():
    return ChatbotResponse(message="Here are some things I can help with: ...")

# Configurando a aplicação do chatbot
user_state = SimpleUserState()
message_consumer = RabbitMessageConsumer.load_dotenv()

app = ChatbotApp(user_state=user_state, message_consumer=message_consumer)
app.include_router(router, prefix="")

# Iniciando o chatbot
app.start()
```

Neste exemplo, o chatbot responde "Hello! How can I assist you today?" quando a rota `HELLO` é acessada e depois direciona o usuário para a rota `HELP`.

## Contribuição

Se você encontrar bugs ou tiver sugestões de melhorias, sinta-se à vontade para abrir uma issue ou enviar um pull request no repositório do projeto.

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para obter mais detalhes.

---

Com **ChatGraph**, você tem a flexibilidade e a simplicidade necessárias para construir chatbots poderosos e altamente configuráveis, integrados, por enquanto, com RabbitMQ para um processamento robusto de mensagens.