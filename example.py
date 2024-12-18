if __name__ == '__main__':
    from chatgraph import ChatbotApp, UserCall, Button, ListElements, Message, RedirectResponse, Route, ChatbotRouter, EndChatResponse
    from dotenv import load_dotenv
    from datetime import datetime

    load_dotenv()
    app = ChatbotApp()

    # Rota inicial com emojis
    @app.route("start")
    def start(rota: Route, usercall:UserCall) -> tuple:
        
        print(rota, usercall)
        usercall.send('👋 Olá!')
        return (
            '👋 Olá!',
            '😊 Como posso ajudar você hoje?',
            Button(
                text="🛒 Sou o assistente virtual das Lojas Quero-Quero. Escolha uma opção:",
                buttons=["🛍️ Ver ofertas", "👨‍💼 Atendimento", "📦 Acompanhar pedido"],
            ),
            rota.get_next('.choice')  # Direciona para a próxima rota
        )

    # Segunda rota - Escolha da opção
    @app.route("start.choice")
    def start_choice(usercall: UserCall, rota: Route) -> tuple:
        usercall.send(Button(
            text="🔎 O que você gostaria de fazer agora?",
            buttons=["🏠 Ver produtos", "📞 Contato suporte", "🔙 Voltar"],
        ))

        usercall.send(ListElements(
            text="✨ Algumas sugestões para você:",
            elements={
                '🛋️ Móveis e decoração': '🎉 Descontos imperdíveis!',
                '🔧 Construção': '🛠️ Tudo o que você precisa.',
                '📱 Tecnologia': '📢 Promoções especiais em eletrônicos!'
            },
            button_title='👉 Clique aqui para ver mais detalhes'
        ))

        usercall.send(Message('🛎️ Se precisar de mais informações, é só escolher uma opção acima!'))
        
        return (
            '🎯 Aguardo sua escolha!',
            rota.get_next('start.rota-b')  # Direciona para a sub-rota
        )

    # Router com rotas adicionais
    router = ChatbotRouter()

    @router.route("start")
    def start_router(usercall: UserCall, rota: Route) -> tuple:
        usercall.obs['data'] = str(datetime.now())  # Grava a data da interação

        return (
            RedirectResponse('.choice'),
        )

    @router.route("start.choice.rota-b")
    def start_choice_rota_b(usercall: UserCall, rota: Route) -> tuple:
        usercall.send('👋 Até logo! Volte sempre! 😊')
        return EndChatResponse('📝 Conversa finalizada com sucesso.', '👍 Obrigado por utilizar o chatbot!')

    # Inclui o router no aplicativo
    app.include_router(router, prefix='.rota-b')

    # Inicia o chatbot
    app.start()
