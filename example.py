from chatgraph import ChatbotApp, UserCall, Button, ListElements, Message, RedirectResponse, Route, ChatbotRouter, EndChatResponse
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
app = ChatbotApp()

# Rota inicial com emojis
@app.route("start")
def start(rota: Route, usercall:UserCall) -> tuple:
    
    print(rota, usercall)
    usercall.send('Olá, bem-vindo ao atendimento das Lojas Quero-Quero VerdeCard! 💚')
    
    usercall.send('Selecione uma das opções abaixo para que possamos te ajudar! 😉')
    
    usercall.send(ListElements(
        text="oi",
        elements={
            'Cartão Quero-Quero 💳': 'fatura, saldo, negociação e outras opções',
            'Lojas Quero-Quero 🛒 💚': 'compras, central de montagens, Palavra! e outras opções',
            'Empréstimo Pessoal 💰': '',
            'Aplicativo 📲': 'Quero-Quero PAG ',
            'PIX e Conta digital 📳': '',
            'Para Lojistas 🏬': '',
            'Botões Whatsapp ✅': '',
            'Encerrar a conversa 👋': '',
        },
        button_title='👉 Clique aqui'
    ))
    
    return rota.get_next('start.choice') 

# Segunda rota - Escolha da opção
@app.route("start.choice")
def start_choice(usercall: UserCall, rota: Route) -> tuple:
    texto = usercall.text
    
    match texto:
        case 'Empréstimo Pessoal 💰':
            usercall.send('Você selecionou a opção Empréstimo Pessoal 💰')
            # return EndChatResponse('Abandono de atendimento', 'teste de chatbot')
            
        case _:
            usercall.send('Você selecionou a opção Cartão Quero-Quero 💳')
            # return EndChatResponse('Abandono de atendimento', 'teste de chatbot')

# Inicia o chatbot
app.start()
