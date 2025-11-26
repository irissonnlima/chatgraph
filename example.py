from chatgraph import (
    ChatbotApp,
    UserCall,
    Route,
    EndChatResponse,
    RedirectResponse,
    Message,
    File,
    Button,
    TextMessage,
    UserState,
)
from dotenv import load_dotenv
from datetime import datetime
import asyncio

load_dotenv()
app = ChatbotApp()


# Rota inicial com emojis
@app.route('start')
async def start(rota: Route, usercall: UserCall):
    await usercall.send('Essa é uma mensagem de teste!')

    msg = Message('Me responsta para ir para a próxima rota!')
    await usercall.send('Essa é uma mensagem de teste!')
    await usercall.send(msg)

    return Route('choice_start')


@app.route('choice_start')
async def choice_start(rota: Route, usercall: UserCall):
    file = File.from_path('image.png')
    await usercall.send(file)

    msg_com_btns = Message(
        'Teste com Botões',
        buttons=[
            Button('Voltar'),
            Button('Encerrar'),
            Button('Mandar outra foto'),
        ],
    )
    await usercall.send(msg_com_btns)

    return Route('receber_btns')


@app.route('receber_btns')
async def receber_btns(rota: Route, usercall: UserCall):
    resposta = usercall.content_message

    if resposta == 'Voltar':
        return RedirectResponse('start')
    elif resposta == 'Encerrar':
        return EndChatResponse('voll_ended')
    elif resposta == 'Mandar outra foto':
        return RedirectResponse('choice_start')
    else:
        await usercall.send('Opção inválida!')
        msg_com_btns = Message(
            'Teste com Botões',
            buttons=[
                Button('Voltar'),
                Button('Encerrar'),
                Button('Mandar outra foto'),
            ],
        )
        await usercall.send(msg_com_btns)
        return Route(rota.current)


app.start()
