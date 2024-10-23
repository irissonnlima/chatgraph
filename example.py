
if __name__ == '__main__':
    from chatgraph import ChatbotApp, UserCall, ChatbotResponse, RedirectResponse, Element, EndChatResponse, Route
    from dotenv import load_dotenv
    from datetime import datetime
    
    load_dotenv()
    
    app = ChatbotApp()
    
    optin = []
    
    @app.route("start")
    def start(usercall: UserCall):
        if usercall.customer_id in optin:
            return RedirectResponse('.com_optin')
        
        return RedirectResponse('.sem_optin')
    
    @app.route('.com_optin')
    def com_optin(usercall: UserCall):
        text = '''
        Olá, seja muito bem-vindo ao atendimento das Lojas e cartão Quero-Quero/Quero-Quero PAG. *Esperamos que você esteja bem!* 😉💚 
        
        Desejamos que tua experiência de atendimento neste canal seja incrível! Para isso, selecione a opção na qual precisa de auxílio dos nossos especialistas. 
        
        Vamos lá?
        '''
        return ChatbotResponse(text, 'start.menu_inicial')
    
    @app.route('.sem_optin')
    def sem_optin(usercall: UserCall):
        
        usercall.send_text(
            'Olá, seja muito bem-vindo ao atendimento das Lojas e Cartão Quero-Quero/Quero-Quero PAG.\n\n*Esperamos que você esteja bem!* 💚 '
        )   
        
        text = '''Para prosseguir com seu atendimento, é necessário que você leia e aceite os Termos de Uso deste canal.
            
            *Ao aceitar, você concorda com os Termos de Uso e declara estar ciente da nossa Política de Privacidade.*

            É rápido e seguro, você pode acessar sem receio! 😉

            👉 [Aceito os Termos de Uso]
            👉 [Política de Privacidade]
            '''
        usercall.send_text(text)
        
        usercall.send_button(
            text='O que você deseja fazer?',
            buttons=[
                'Ok, eu aceito!', 
                'Não aceito'
                ]
        )
        return ChatbotResponse(route='.choice')
    
    @app.route('.sem_optin.choice')
    def sem_optin_choice(usercall: UserCall):
        
        if usercall.text == 'Ok, eu aceito!':
            optin.append(usercall.customer_id)
            agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            text = f'''
            Aceite realizado com sucesso em {agora}!

            Com este aceite, você concorda em *receber notificações, ofertas e outras mensagens através do WhatsApp.* 📲
            *Caso mude de ideia,* você pode desativar as mensagens a qualquer momento clicando em [link de opt-out].

            Agora sim, vamos continuar com o atendimento! 🤩
            '''
            usercall.send_text(text)
        elif usercall.text == 'Não aceito':
            text ='''
            Ah, que pena! 😕

            Se mudar de ideia, você pode aceitar os nossos termos para receber mensagens e ofertas a qualquer momento, *basta clicar no link* 🔗 
            
            [link aqui].

            Vamos seguir com o atendimento! 😀
            '''
            usercall.send_text(text)
        else:
            return ChatbotResponse('Por favor, escolha uma das opções.')
        return RedirectResponse('start.menu_inicial')
    
    @app.route('.menu_inicial')
    def menu_inicial(usercall: UserCall):
        
        usercall.send_list(
            text='Desejamos que tua experiência de atendimento neste canal seja incrível! \n\nPara isso, selecione a opção na qual precisa de auxílio dos nossos especialistas.',
            button_title='Vamos lá?',
            element_list=[
                Element('Cartão Quero-Quero 💳', 'Fatura, saldo, negociação e outras opções '),
                Element('Lojas Quero-Quero 🛒 💚', 'Compras, Palavra! e outras opções'),
                Element('Empréstimo Pessoal 💰', 'Dinheiro na hora? Vem conhecer nosso empréstimo pessoal!'),
                Element('App Quero-Quero PAG 📲', 'A informação na palma da sua mão!'),
                Element('PIX e Conta digital 📳','Dúvidas sobre acesso e transações'),
                Element('Para Lojistas 🏬','Informações sobre seu negócio'),
                Element('SOS enchentes 🤝','Fique por dentro e saiba como ajudar'),
                Element('Encerrar a conversa 👋','Não tem nenhuma dúvida? Clica aqui para finalizar o atendimento')
            ]
        )
        return ChatbotResponse(route='.choice')
    
    @app.route('.menu_inicial.choice')
    def menu_inicial_choice(usercall: UserCall):
        usercall.menu = 'APP'
        if usercall.text == 'Cartão Quero-Quero 💳':
            return RedirectResponse('.cartao')
        elif usercall.text == 'Lojas Quero-Quero 🛒 💚':
            return RedirectResponse('.all')
        elif usercall.text == 'Empréstimo Pessoal 💰':
            return RedirectResponse('.all')
        elif usercall.text == 'App Quero-Quero PAG 📲':
            return RedirectResponse('.all')
        elif usercall.text == 'PIX e Conta digital 📳':
            return RedirectResponse('.all')
        elif usercall.text == 'Para Lojistas 🏬':
            return RedirectResponse('.all')
        elif usercall.text == 'SOS enchentes 🤝':
            return RedirectResponse('.all')
        elif usercall.text == 'Encerrar a conversa 👋':
            return EndChatResponse('encerramento','Até mais! 😊')
        else:
            return ChatbotResponse('Por favor, escolha uma das opções.')
    
    @app.route('.menu_inicial.choice.all')
    def all_routes(usercall: UserCall):
        usercall.send_text('Em desenvolvimento...')
        return ChatbotResponse(route='start.menu_inicial')
    
    @app.route('.menu_inicial.choice.cartao')
    def cartao(usercall: UserCall):
        usercall.send_list(
            text='Entendi! Vamos falar sobre o teu cartão!',
            button_title='Escolha uma opção',
            element_list=[
                Element('Envio de fatura 📩', 'Para consultar a fatura, receber o código de barras e PDF.'),
                Element('Saldo ou limite 🧾', 'Verifique o valor disponível, vencimento e melhor dia de compras.'),
                Element('Negociação de dívida 🤝', 'Para verificar saldo devedor e negociar seus débitos.'),
                Element('Cartão/cadastro 💳', 'Atualize seus dados, consulte bloqueios e status de aprovação.'),
                Element('Dúvidas sobre fatura ❓', 'Informar pagamento da fatura e verificar meios de pagamento disponíveis.'),
                Element('Empréstimo pessoal 💰', 'Dinheiro na hora? Vem conhecer nosso empréstimo pessoal!'),
                Element('Solicitar cartão 🗣 💳', 'Para solicitar seu cartão QQ PAG ou gerar segunda via.'),
                Element('Outras informações 🔜', 'Não encontrou o que precisava? Clica aqui para que eu possa te ajudar!'),
                Element('Encerrar a conversa 👋', 'Não tem mais nenhuma dúvida? Clica aqui para finalizar o atendimento.')
            ]
        )
        return ChatbotResponse(route='.choice')
    
    @app.route('.menu_inicial.choice.cartao.choice')
    def cartao_choice(usercall: UserCall, route: Route):
        match usercall.text:
            case 'Encerrar a conversa 👋':
                usercall.send_text('Entendi! Até mais! 😊')
                return EndChatResponse('encerramento', 'Até mais! 😊')
            case _:
                
                usercall.send_text('Entendi, porém não foi desenvolvido!')
                return RedirectResponse(route.previous)
    
    
    
    app.start()