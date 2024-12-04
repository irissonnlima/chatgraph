
if __name__ == '__main__':
    from chatgraph import ChatbotApp, UserCall, Button, ListElements, Message, RedirectResponse, Route, ChatbotRouter, EndChatResponse
    from dotenv import load_dotenv
    from datetime import datetime
    
    load_dotenv()
    
    app = ChatbotApp()
    
    
    @app.route("start")
    def start(rota: Route)->tuple:
        print(rota)
        return (
            'Oi', 
            'Tudo bem?',
            Button(
                text="Olá, eu sou o chatbot da empresa X. Como posso te ajudar?",
                buttons=["saber mais", "falar com atendente"],
            ),
            rota.get_next('.choice')
        )
    
    @app.route("start.choice")
    def start_choice(usercall: UserCall, rota: Route)->tuple:
        usercall.send(Button(
            text="Escolha uma opção",
            buttons=["saber mais", "falar com atendente"],
        ))
        usercall.send(ListElements(
            text="Escolha uma opção",
            elements={
                    'Título': 'descricao',
                    'Título': 'descricao',
                    'Título': 'descricao'
                },
            button_title='Abra o botão'
        ))
        
        usercall.send(Message('Escolha uma opção'))
        usercall.send('Escolha uma opção')
        
        return (
            'oi',
            rota.get_next('.rota-b'),
            )
    
    router = ChatbotRouter()
    
    @router.route("start")
    def start(usercall: UserCall, rota: Route)->tuple:
        usercall.obs['data'] = str(datetime.now())
        
        return (
            RedirectResponse('.choice'),
        )
    
    @router.route("start.choice")
    def start_choice(usercall: UserCall, rota: Route)->tuple:
        usercall.send('Até mais!')
        return EndChatResponse('Cadastro finalizado App', 'Uma obs de teste')
    
    app.include_router(router, prefix='.choice.rota-b')
    app.start()
