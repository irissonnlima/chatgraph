import asyncio
from typing import Any, Callable
import threading

class BackgroundTask:
    def __init__(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """
        Inicia uma função de forma assíncrona em segundo plano e printa sua saída.
        
        Args:
            func (Callable): A função a ser executada.
            args (Any): Argumentos posicionais a serem passados para a função.
            kwargs (Any): Argumentos nomeados a serem passados para a função.
        """
        
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("A função fornecida deve ser uma coroutine (async def).")
        
        self.args = args
        self.kwargs = kwargs
        self.func = func

    async def run(self):
        """
        Executa a função em segundo plano.
        """
        return await self.func(*self.args, **self.kwargs)