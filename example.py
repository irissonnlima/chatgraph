from chatgraph import ChatbotApp, UserCall, Button, Message, RedirectResponse, Route, ChatbotRouter, BackgroundTask
from dotenv import load_dotenv
from datetime import datetime
import asyncio

load_dotenv()
app = ChatbotApp()

# Rota inicial com emojis
@app.route("start")
async def start(rota: Route, usercall:UserCall) -> tuple:
    
    usercall.send('Olá, bem-vindo ao atendimento das Lojas Quero-Quero VerdeCard! 💚')
    
    async def func(usercall: UserCall):
        print('Iniciando a função em segundo plano...')
        await asyncio.sleep(5)
        print('Finalizando a função em segundo plano...')
        usercall.send('Você ainda está aí? 😅')
        return await func(usercall)
    
    BackgroundTask(func, usercall)
    
    return BackgroundTask(func, usercall)


@app.route("choice_start")
def choice_start(rota: Route, usercall:UserCall) -> tuple:
    usercall.send('Você foi redirecionado para a rota choice_start.')
    

app.start()
