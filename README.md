### **README - ChatGraph**

# ChatGraph - Framework para Criação de Chatbots

ChatGraph é uma biblioteca desenvolvida para criar chatbots interativos e modulares. Com suporte integrado para gRPC e RabbitMQ, ela permite gerenciar fluxos complexos de mensagens e criar comandos de chatbots que respondem a rotas específicas. Toda interação começa pela rota `start` e deriva para sub-rotas como `start.choice`.

### **Requisitos**
- Python 3.12+
- `pip` para gerenciamento de pacotes

### **Instalação**
A biblioteca ChatGraph pode ser instalada diretamente via `pip`:

```bash
pip install chatgraph
```

## **Configuração**

### **Variáveis de Ambiente**
Crie um arquivo `.env` na raiz do projeto para definir as variáveis necessárias, incluindo detalhes de conexão com RabbitMQ e URI para gRPC. Exemplo:

```env
RABBIT_USER=seu_usuario
RABBIT_PASS=sua_senha
RABBIT_URI=amqp://localhost
RABBIT_QUEUE=chat_queue
RABBIT_PREFETCH=1
RABBIT_VHOST=/
GRPC_URI=grpc://localhost:50051
```

Aqui está uma descrição mais detalhada de cada um dos objetos mencionados. Esses componentes são fundamentais para a estrutura e funcionalidade do ChatGraph, permitindo gerenciar fluxos de chat, interações e estados do usuário de forma eficiente.

### **Tipos de Objetos e Suas Funções**

---

### **1. `UserCall`**
**Localização:** `from .types.request_types import UserCall`

O `UserCall` representa uma solicitação de interação do usuário para o chatbot. Ele encapsula as informações básicas sobre uma mensagem recebida do usuário e fornece detalhes essenciais que o chatbot pode usar para decidir como responder.

#### **Principais Propriedades:**
- **`text`**: A mensagem de texto enviada pelo usuário.
- **`user_id`**: Identificador único do usuário, permitindo o rastreamento e a vinculação de estados.
- **`platform`**: Informação sobre a plataforma usada (por exemplo, WhatsApp, Web, etc.).
- **`timestamp`**: Horário em que a mensagem foi recebida.
- **`metadata`**: Dados adicionais que podem incluir informações contextuais (ex: geolocalização, histórico de navegação).

#### **Uso:**
O `UserCall` é instanciado sempre que uma nova mensagem é recebida, e fornece os dados necessários para que o chatbot processe e determine a resposta apropriada.

---

### **2. `UserState`**
**Localização:** `from .types.request_types import UserState`

`UserState` é usado para representar o estado atual do usuário no sistema de chatbot. Ele guarda o contexto de uma sessão do usuário, permitindo que o chatbot mantenha informações ao longo de múltiplas interações.

#### **Principais Propriedades:**
- **`state_id`**: Identificador único para o estado do usuário.
- **`current_route`**: A rota atual onde o usuário está localizado dentro do fluxo do chatbot.
- **`data`**: Dados de estado armazenados que podem ser usados para tomar decisões em futuras interações (ex: preferências, histórico de escolhas).
- **`last_interaction`**: Timestamp da última interação do usuário.

#### **Uso:**
O `UserState` ajuda a manter o contexto entre as mensagens para que o chatbot possa continuar uma conversa sem perder informações importantes.

---

### **3. `RedirectResponse`**
**Localização:** `from .types.end_types import RedirectResponse`

`RedirectResponse` é usado quando o chatbot precisa redirecionar o usuário para uma rota diferente dentro do fluxo de conversa. Isso é útil para mover o usuário para diferentes partes do chatbot com base na lógica de negócios.

#### **Principais Propriedades:**
- **`target_route`**: Rota para a qual o usuário será redirecionado.
- **`message`**: Mensagem opcional a ser exibida durante o redirecionamento.

#### **Uso:**
Permite criar fluxos mais dinâmicos, onde os usuários podem ser movidos para diferentes rotas dependendo de suas ações e escolhas.

---

### **4. `EndChatResponse`**
**Localização:** `from .types.end_types import EndChatResponse`

`EndChatResponse` é uma resposta que sinaliza o fim de uma conversa com o chatbot. Pode ser usado para finalizar a sessão de forma limpa e opcionalmente fornecer uma mensagem de encerramento.

#### **Principais Propriedades:**
- **`message`**: Mensagem final que será enviada ao usuário para encerrar a conversa.
- **`feedback_prompt`**: (Opcional) Um prompt para feedback, se desejado.

#### **Uso:**
Usado quando o fluxo do chatbot deve ser encerrado. Garante que a sessão do usuário seja finalizada corretamente e fornece uma experiência de término satisfatória.

---

### **5. `TransferToHuman`**
**Localização:** `from .types.end_types import TransferToHuman`

`TransferToHuman` é uma resposta que permite transferir a interação do usuário para um operador humano. Isso é útil quando o chatbot encontra uma situação que requer suporte humano.

#### **Principais Propriedades:**
- **`message`**: Mensagem para informar ao usuário que ele será transferido para um atendente humano.
- **`department`**: (Opcional) Departamento ou equipe específica para a qual a interação será transferida.

#### **Uso:**
Fornece uma maneira para o chatbot transferir conversas para atendimento humano quando necessário, garantindo uma transição suave.

---

### **6. `Message`**
**Localização:** `from .types.message_types import Message`

O `Message` é um objeto básico que representa uma mensagem de texto enviada pelo chatbot para o usuário. Ele é o bloco de construção fundamental para as respostas do chatbot.

#### **Principais Propriedades:**
- **`text`**: O conteúdo da mensagem que será enviado ao usuário.
- **`metadata`**: Informações adicionais sobre a mensagem (ex: tags, prioridade).

#### **Uso:**
Usado para enviar respostas simples e diretas ao usuário. O `Message` é utilizado em quase todas as interações básicas do chatbot.

---

### **7. `Button`**
**Localização:** `from .types.message_types import Button`

O `Button` representa uma mensagem que inclui botões clicáveis para oferecer ao usuário opções específicas. Ele é essencial para criar fluxos interativos e guiar o usuário para ações específicas.

#### **Principais Propriedades:**
- **`text`**: Texto descritivo acima dos botões.
- **`buttons`**: Lista de opções que aparecem como botões clicáveis.
- **`callback_data`**: (Opcional) Dados que são passados quando um botão é clicado, permitindo lógica adicional.

#### **Uso:**
Facilita a navegação no chatbot ao permitir que o usuário escolha uma ação clicando em um botão, em vez de digitar uma resposta.

---

### **8. `ListElements`**
**Localização:** `from .types.message_types import ListElements`

O `ListElements` é um tipo de mensagem que exibe uma lista de elementos ao usuário, útil para apresentar várias opções de uma só vez.

#### **Principais Propriedades:**
- **`title`**: Título da lista.
- **`items`**: Lista de elementos a serem exibidos.
- **`image_url`**: (Opcional) URL de uma imagem para cada item, se desejado.
- **`description`**: (Opcional) Descrição adicional para cada elemento.

#### **Uso:**
Ideal para cenários em que múltiplas opções precisam ser apresentadas ao usuário, como uma lista de produtos ou serviços.

---

### **9. `Route`**
**Localização:** `from .types.route import Route`

O `Route` gerencia a navegação entre diferentes partes do chatbot. Ele é responsável por direcionar o fluxo de conversação, ajudando a determinar qual é a próxima rota ou passo que o usuário deve seguir.

#### **Principais Funções:**
- **`get_next`**: Retorna a próxima rota a ser seguida no fluxo.
- **`back`**: Permite retornar para uma rota anterior.
- **`forward`**: Avança para uma rota específica.
- **`resolve`**: Determina qual é a rota baseada no estado atual e nas escolhas do usuário.

#### **Uso:**
O `Route` é essencial para criar fluxos conversacionais dinâmicos e adaptáveis. Ele ajuda a definir a progressão lógica do chatbot, permitindo controle total sobre como o usuário navega entre diferentes partes do fluxo.


### **Estrutura de Rota**
Todas as interações no ChatGraph começam pela rota `start` e se derivam para sub-rotas, criando um fluxo contínuo para gerenciar conversas.

- **Exemplo:** `start`, `start.choice`, `start.choice.about`

## **Uso**

### **Configurando o Chatbot**
```python
from chatgraph import ChatbotApp, UserCall, Button, Route

app = ChatbotApp()

@app.route("start")
def start(usercall: UserCall, rota: Route) -> tuple:
    return (
        'Bem-vindo!',
        Button(
            text="Escolha uma opção:",
            buttons=["Opção 1", "Opção 2"]
        ),
        rota.get_next('.choice')
    )

@app.route("start.choice")
def start_choice(usercall: UserCall, rota: Route) -> tuple:
    if usercall.text == "Opção 1":
        return 'Você escolheu a Opção 1!'
    elif usercall.text == "Opção 2":
        return 'Você escolheu a Opção 2!'
    
app.start()
```

## **Estrutura da Biblioteca**

```
chatgraph/
│
├── auth/
│   └── credentials.py  # Gerenciamento de credenciais
├── bot/
│   ├── chatbot_model.py  # Lógica principal do chatbot
│   └── chatbot_router.py  # Roteamento de rotas do chatbot
├── cli/
│   └── main.py  # Implementação do CLI
├── gRPC/
│   └── gRPCCall.py  # Implementação de comunicação gRPC
├── messages/
│   └── message_consumer.py  # Consumidor de mensagens RabbitMQ
└── types/
    ├── request_types.py  # Definição de tipos de requisições
    ├── message_types.py  # Definição de tipos de mensagens
    ├── end_types.py  # Tipos de finalização de chat
    └── route.py  # Gerenciamento de rotas
```

## **Exemplo de Configuração de Rota**

### **Estrutura de Fluxo**
```python
from chatgraph import ChatbotApp, UserCall, Button, Route

app = ChatbotApp()

@app.route("start")
def start(usercall: UserCall, rota: Route)->tuple:
    return (
        'Oi', 
        Button(
            text="Olá, eu sou o chatbot da empresa X. Como posso te ajudar?",
            buttons=["saber mais", "falar com atendente"],
        ),
        rota.get_next('.choice')
    )

@app.route("start.choice")
def start_choice(usercall: UserCall, rota: Route)->tuple:
    if usercall.text == "saber mais":
        return (
            'Sobre o que você quer saber mais?',
            Button(
                text="Sobre a empresa",
                buttons=["sobre produtos", "sobre serviços"],
            ),
            rota.get_next('.about')
        )
    elif usercall.text == "falar com atendente":
        return 'Ok'
    
app.start()
```

## **CLI**

### **Comandos Disponíveis**
1. **Listar campanhas:**
   ```bash
   chatgraph campaigns
   ```
2. **Filtrar campanhas usando regex:**
   ```bash
   chatgraph campaigns --regex "promo"
   ```
3. **Deletar um estado de usuário:**
   ```bash
   chatgraph delete-ustate 12345
   ```
   **Alias:** `delete-user-state`, `del-ustate`, `dus`

### **Aliases e Flexibilidade**
Para facilitar o uso, alguns comandos possuem apelidos. Por exemplo, o comando para deletar estados de usuário pode ser chamado de múltiplas formas:
```bash
chatgraph delete-user-state 12345
chatgraph del-ustate 12345
chatgraph dus 12345
```

## **Contribuição**
1. Faça um fork do repositório.
2. Crie uma nova branch (`git checkout -b minha-nova-feature`).
3. Faça commit das suas alterações (`git commit -am 'Adiciona nova feature'`).
4. Envie para a branch (`git push origin minha-nova-feature`).
5. Crie um novo Pull Request.

## **Licença**
Este projeto é licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

Esse README fornece instruções detalhadas sobre como instalar, configurar e usar a biblioteca ChatGraph, incluindo a estrutura de rotas e exemplos de implementação para facilitar o desenvolvimento de chatbots com fluxos claros e intuitivos.