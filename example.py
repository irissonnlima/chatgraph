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


@app.route('choice_start')
async def choice_start(rota: Route, usercall: UserCall):
    usercall.logger.debug(
        f'Conteúdo recebido em choice_start: {usercall.content_message}'
    )
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
    usercall.logger.debug(f'Contador atualizado: {obs["contador"]}')

    return Route('before_end_chat')


@app.route('before_end_chat')
async def before_end_chat(usercall: UserCall, rota: Route):
    teste = Teste(atributo1='valor1', atributo2=42)
    obs = usercall.observation
    obs['teste_dataclass'] = teste.__dict__
    usercall.observation = obs
    usercall.logger.debug(f'Observação atualizada: {obs}')
    return RedirectResponse('receber_btns')


@app.route('receber_btns')
async def receber_btns(rota: Route, usercall: UserCall):
    resposta = usercall.content_message
    usercall.logger.info(f'Resposta recebida: {resposta}')

    if resposta == 'Voltar':
        return RedirectResponse('start')
    elif resposta == 'Encerrar':
        return EndChatResponse('voll_ended')
    elif resposta == 'Mandar outra foto':
        return RedirectResponse('choice_start')
    else:
        usercall.logger.warning(f'Opção inválida recebida: {resposta}')
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


@app.route('area_restrita', auth_level='internal')
async def area_restrita(usercall: UserCall):
    usercall.logger.info('Usuário acessou área restrita')
    await usercall.send('Você está em uma área protegida. Acesso autorizado!')
    return RedirectResponse('choice_start')


app.start()
