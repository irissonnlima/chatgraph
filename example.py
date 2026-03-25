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
    TransferToMenu,
)
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()
app = ChatbotApp()


@dataclass
class Teste:
    atributo1: str
    atributo2: int


# Rota inicial com emojis
@app.route('start')
async def start(rota: Route, usercall: UserCall):
    welcome_message = Message(
        'Bem-vindo ao nosso chatbot! 😊🚀\nEscolha uma opção para continuar:',
    )

    await usercall.send(welcome_message)
    return TransferToMenu(
        'default',
        'Olá, estou transferindo para o novo menu!',
    )


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

    obs = usercall.observation
    obs['contador'] = obs.get('contador', 0) + 1
    usercall.observation = obs

    return Route('before_end_chat')


@app.route('before_end_chat')
async def before_end_chat(usercall: UserCall, rota: Route):
    teste = Teste(atributo1='valor1', atributo2=42)
    obs = usercall.observation
    obs['teste_dataclass'] = teste.__dict__
    usercall.observation = obs
    return RedirectResponse('receber_btns')


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
