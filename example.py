from chatgraph import ChatbotApp, UserCall, Button, Message, RedirectResponse, Route, ChatbotRouter, EndChatResponse
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
    
    return rota.get_next('choice_start') 


@app.route("choice_start")
def choice_start(rota: Route, usercall:UserCall) -> tuple:
    
    if usercall.text == 'A':
        return RedirectResponse('fatura')
    elif usercall.text == 'B':
        return RedirectResponse('compras')
    elif usercall.text == 'C':
        return RedirectResponse('outros')
    elif usercall.text == 'Voltar':
        return rota.get_previous()
    else:
        usercall.send('Opção inválida! 😢')
        return

routerA = ChatbotRouter()

@routerA.route("fatura")
def fat(rota: Route, usercall:UserCall) -> tuple:
    
    usercall.send('Você selecionou a opção fatura! 😊')
    return rota.get_next('compras')

@routerA.route("compras")
def comp(rota: Route, usercall:UserCall) -> tuple:
    
    usercall.send('Você selecionou a opção compras! 😊')
    return rota.get_next('outros')

routerB = ChatbotRouter()

@routerB.route("outros")
def outros(rota: Route, usercall:UserCall) -> tuple:
    
    usercall.send('Você selecionou a opção outros! 😊')
    return rota.get_next('start')

routerA.include_router(routerB)

app.include_router(routerA)
# Inicia o chatbot
app.start()
