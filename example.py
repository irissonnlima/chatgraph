from chatgraph import ChatbotApp, UserCall, Button, Message, RedirectResponse, Route, ChatbotRouter, BackgroundTask
from dotenv import load_dotenv
from datetime import datetime
import asyncio

load_dotenv()
app = ChatbotApp()

# Rota inicial com emojis
@app.route("start")
def start(rota: Route, usercall:UserCall) -> tuple:
    
    usercall.send('Olá, bem-vindo ao atendimento das Lojas Quero-Quero VerdeCard! 💚')
    
    async def func(usercall: UserCall):
        print('Iniciando a função em segundo plano...')
        await asyncio.sleep(5)
        print('Finalizando a função em segundo plano...')
        usercall.send('Você ainda está aí? 😅')
    BackgroundTask(func, usercall)
    
    message = Message(
        'Selecione uma das opções abaixo para que possamos te ajudar! 😉',
        title="roboto",
        caption="Escolha uma opção:",
        buttons=[
            Button('A', 'Fatura'),
            Button('B', 'Compras'),
            Button('D', 'Lista de compras'),
            Button('C', 'Outros'),
        ],
        display_button=Button('Abrir', 'Abrir')
        )
    usercall.send(message)


@app.route("choice_start")
def choice_start(rota: Route, usercall:UserCall) -> tuple:
    
    if usercall.content_message == 'A':
        return RedirectResponse('fatura')
    elif usercall.content_message == 'B':
        return RedirectResponse('compras')
    elif usercall.content_message == 'C':
        return RedirectResponse('outros')
    elif usercall.content_message == 'Voltar':
        return rota.get_previous()
    else:
        usercall.send('Opção inválida! 😢')
        return

routerA = ChatbotRouter()

@routerA.route("fatura")
async def fat(rota: Route, usercall:UserCall) -> tuple:
    
    
    usercall.send(
        Message(
            detail="Selecione uma das opções abaixo para que possamos te ajudar! 😉",
            buttons=[
                Button(
                    title="Cartão Verdecard 👌💻👥📑",
                    detail="fatura, saldo, negociação e outras opções mais algum texto para testar o tamanho do botão",
                ),
                Button(
                    title="Lojas Quero-Quero ",
                    detail="compras, central de montagens, Palavra! e outras opções",
                ),
                Button(title="Empréstimo Pessoal", detail=""),
                Button(title="Aplicativo ", detail="Quero-Quero PAG"),
                Button(title="PIX|Conta digital", detail=""),
                Button(title="Para Lojistas ", detail=""),
                Button(title="Botões Whatsapp ", detail=""),
                Button(title="Encerrar conversa ", detail=""),
            ],
            display_button=Button("👉 Clique aqui", ""),
            caption="",
        )
    )
# Inicia o chatbot
app.start()
