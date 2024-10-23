
if __name__ == '__main__':
    from chatgraph import ChatbotApp, UserCall, Button, ListElements, Message, RedirectResponse, Route
    from dotenv import load_dotenv
    from datetime import datetime
    
    load_dotenv()
    
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