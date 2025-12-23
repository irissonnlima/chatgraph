"""
Exemplo de uso do ChatGraph com controle de logging.

Este exemplo demonstra como:
1. Habilitar/desabilitar logs
2. Configurar nível de log
3. Usar variáveis de ambiente
"""

from chatgraph import ChatbotApp, configure, config
from chatgraph.types.route import Route
from chatgraph.types.usercall import UserCall


# ==============================================================================
# Exemplo 1: Desabilitando logs completamente
# ==============================================================================
def example_1_no_logs():
    """Chatbot sem nenhum log de console."""
    print('\n=== Exemplo 1: Sem logs ===\n')

    # Desabilitar logs
    configure(verbose=False)

    app = ChatbotApp()

    @app.route('start')
    async def start(rota: Route, usercall: UserCall):
        # Nenhum log será exibido, mas a mensagem será enviada
        await usercall.send('Olá! Sem logs.')


# ==============================================================================
# Exemplo 2: Logs apenas para erros
# ==============================================================================
def example_2_only_errors():
    """Chatbot que mostra apenas erros."""
    print('\n=== Exemplo 2: Apenas erros ===\n')

    # Mostrar apenas erros
    configure(verbose=True, log_level='ERROR')

    app = ChatbotApp()

    @app.route('start')
    async def start(rota: Route, usercall: UserCall):
        # Logs INFO não serão exibidos
        await usercall.send('Mensagem normal')  # Sem log

        try:
            # Simular erro
            raise ValueError('Erro de teste')
        except ValueError as e:
            # Este erro SERÁ exibido
            await usercall.send(f'Erro: {e}')


# ==============================================================================
# Exemplo 3: Modo debug (tudo detalhado)
# ==============================================================================
def example_3_debug_mode():
    """Chatbot em modo debug com todos os detalhes."""
    print('\n=== Exemplo 3: Modo Debug ===\n')

    # Modo debug
    configure(verbose=True, log_level='DEBUG')

    app = ChatbotApp()

    @app.route('start')
    async def start(rota: Route, usercall: UserCall):
        # Todos os logs serão exibidos
        await usercall.send('Iniciando...')
        await usercall.set_observation({'step': 1})
        await usercall.set_route('choice')
        await usercall.send('Concluído!')


# ==============================================================================
# Exemplo 4: Controle dinâmico
# ==============================================================================
def example_4_dynamic_control():
    """Habilita/desabilita logs dinamicamente."""
    print('\n=== Exemplo 4: Controle Dinâmico ===\n')

    app = ChatbotApp()

    @app.route('start')
    async def start(rota: Route, usercall: UserCall):
        # Logs habilitados
        config.enable_logging()
        await usercall.send('Esta mensagem tem log')

        # Desabilitar temporariamente
        config.disable_logging()
        await usercall.send('Esta mensagem NÃO tem log')

        # Habilitar novamente
        config.enable_logging()
        await usercall.send('Esta mensagem tem log novamente')


# ==============================================================================
# Exemplo 5: Configuração para produção
# ==============================================================================
def example_5_production():
    """Configuração recomendada para produção."""
    print('\n=== Exemplo 5: Produção ===\n')

    import os

    # Detectar ambiente
    is_production = os.getenv('ENVIRONMENT') == 'production'

    if is_production:
        # Produção: apenas erros
        configure(verbose=True, log_level='ERROR')
    else:
        # Desenvolvimento: tudo
        configure(verbose=True, log_level='DEBUG')

    app = ChatbotApp()

    @app.route('start')
    async def start(rota: Route, usercall: UserCall):
        await usercall.send('Configurado para o ambiente correto!')


# ==============================================================================
# Exemplo 6: Verificando configuração atual
# ==============================================================================
def example_6_check_config():
    """Verifica a configuração atual."""
    print('\n=== Exemplo 6: Verificar Configuração ===\n')

    from chatgraph import config

    print(f'Verbose: {config.verbose}')
    print(f'Log Level: {config.log_level}')
    print(f'Console: {type(config.console).__name__}')


# ==============================================================================
# Exemplo 7: Usando variáveis de ambiente
# ==============================================================================
def example_7_env_vars():
    """Usa variáveis de ambiente para configurar."""
    print('\n=== Exemplo 7: Variáveis de Ambiente ===\n')

    import os
    from dotenv import load_dotenv

    # Criar .env com:
    # CHATGRAPH_VERBOSE=false
    # CHATGRAPH_LOG_LEVEL=ERROR

    load_dotenv()

    # ChatGraph lê automaticamente as variáveis
    app = ChatbotApp()

    print(f'Verbose (do .env): {config.verbose}')
    print(f'Log Level (do .env): {config.log_level}')


# ==============================================================================
# Exemplo 8: Para testes automatizados
# ==============================================================================
def example_8_testing():
    """Configuração para testes automatizados."""
    print('\n=== Exemplo 8: Testes Automatizados ===\n')

    # No conftest.py ou setup de testes
    config.verbose = False

    app = ChatbotApp()

    @app.route('start')
    async def start(rota: Route, usercall: UserCall):
        # Testes rodam silenciosamente
        await usercall.send('Test message')

    # Executar testes...
    print('✓ Testes executam sem logs no console')


# ==============================================================================
# Main
# ==============================================================================
if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('ChatGraph - Exemplos de Configuração de Logging')
    print('=' * 60)

    # Executar exemplos
    example_1_no_logs()
    example_2_only_errors()
    example_3_debug_mode()
    example_4_dynamic_control()
    example_5_production()
    example_6_check_config()
    example_7_env_vars()
    example_8_testing()

    print('\n' + '=' * 60)
    print('Exemplos concluídos!')
    print('=' * 60 + '\n')

    # Dica
    print('💡 Dica: Para usar em seu projeto:')
    print('   from chatgraph import configure')
    print('   configure(verbose=False)  # Desabilitar logs')
    print()
