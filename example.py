from chatgraph import (
    ChatbotApp,
    UserCall,
    Route,
    EndChatResponse,
    RedirectResponse,
    Message,
    File,
    Button,
    User,
    UserIdentity,
    UserData,
    UserInternal,
    TextMessage,
    UserState,
    TransferToMenu,
)
from chatgraph.logger import get_system_logger
from dotenv import load_dotenv
from dataclasses import dataclass


load_dotenv()
_logger = get_system_logger()
_logger.info('Aplicação inicializada')
app = ChatbotApp()


@dataclass
class Teste:
    atributo1: str
    atributo2: int


# Rota inicial com emojis
@app.route('start')
async def start(rota: Route, usercall: UserCall):
    usercall.logger.info('Usuário entrou na rota start')
    welcome_message = Message(
        'Bem-vindo ao nosso chatbot! 😊🚀\n Vou te redirecionar para uma área restrita',
    )

    await usercall.send(welcome_message)
    return RedirectResponse('perguntar_cpf')


@app.route('perguntar_cpf')
async def perguntar_cpf(rota: Route, usercall: UserCall):
    usercall.logger.info('Usuário entrou na rota perguntar_cpf')
    await usercall.send('Por favor, informe seu CPF:')
    return Route('receber_cpf')


@app.route('receber_cpf')
async def receber_cpf(rota: Route, usercall: UserCall):
    cpf = usercall.content_message
    usercall.logger.info(f'CPF recebido: {cpf}')
    await usercall.add_observation({'cpf': cpf})
    await usercall.send(f'CPF {cpf} recebido com sucesso!')
    return RedirectResponse('area_restrita')


@app.route('area_restrita', auth_level='internal/read/write')
async def area_restrita(usercall: UserCall):
    usercall.logger.info('Usuário acessou área restrita')
    await usercall.send('Você está em uma área protegida. Acesso autorizado!')
    return RedirectResponse('choice_start')


@app.route('enviar_btns')
async def enviar_btns(usercall: UserCall):
    usercall.logger.info('Usuário entrou na rota enviar_btns')
    buttons = [
        Button('Reiniciar'),
        Button('Encerrar'),
    ]
    message = Message(text_message='Escolha uma opção:', buttons=buttons)
    await usercall.send(message)
    return Route('receber_btns')


@app.route('receber_btns')
async def receber_btns(usercall: UserCall):
    usercall.logger.info('Usuário entrou na rota receber_btns')
    choice = usercall.content_message

    usercall.logger.info(f'Opção escolhida: {choice}')
    if choice == 'Reiniciar':
        return RedirectResponse('start')
    elif choice == 'Encerrar':
        await usercall.send('Encerrando o chat. Até mais!')
        return EndChatResponse('voll_ended')
    else:
        await usercall.send('Opção inválida. Por favor, escolha novamente.')
        return Route('enviar_btns')


app.start()
