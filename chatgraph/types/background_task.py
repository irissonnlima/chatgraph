import asyncio
from typing import Any, Callable
import threading

def BackgroundTask(func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Inicia uma função de forma assíncrona em segundo plano e printa sua saída.

    :param func: Função assíncrona a ser executada.
    :param args: Argumentos posicionais para a função.
    :param kwargs: Argumentos nomeados para a função.
    """
    if asyncio.iscoroutinefunction(func):
        def start_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(func(*args, **kwargs))

        # Executa o loop de eventos em uma thread separada
        thread = threading.Thread(target=start_loop)
        thread.start()
    else:
        raise TypeError("A função fornecida deve ser uma coroutine (async def).")
