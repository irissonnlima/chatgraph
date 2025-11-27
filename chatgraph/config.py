"""
Configurações globais do ChatGraph.

Este módulo gerencia as configurações da biblioteca, incluindo
logging, verbosidade e comportamento do console.
"""

import os
from typing import Optional
from rich.console import Console


class ChatGraphConfig:
    """
    Configurações globais do ChatGraph.
    
    Atributos:
        verbose: Habilita/desabilita logs no console (padrão: True)
        console: Instância do Rich Console (pode ser customizada)
        log_level: Nível de log ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    
    Exemplo:
        >>> from chatgraph import config
        >>> config.verbose = False  # Desabilita logs
        >>> config.verbose = True   # Habilita logs
        
        >>> # Ou via variável de ambiente
        >>> # export CHATGRAPH_VERBOSE=false
    """
    
    def __init__(self):
        # Ler de variável de ambiente ou usar padrão
        env_verbose = os.getenv('CHATGRAPH_VERBOSE', 'true').lower()
        self._verbose = env_verbose in ('true', '1', 'yes', 'on')
        
        self._console = Console()
        self._log_level = os.getenv('CHATGRAPH_LOG_LEVEL', 'INFO').upper()
    
    @property
    def verbose(self) -> bool:
        """Retorna se logs estão habilitados."""
        return self._verbose
    
    @verbose.setter
    def verbose(self, value: bool):
        """Define se logs devem ser exibidos."""
        self._verbose = bool(value)
    
    @property
    def console(self) -> Console:
        """Retorna instância do Rich Console."""
        return self._console
    
    @console.setter
    def console(self, value: Console):
        """Define instância customizada do Rich Console."""
        if not isinstance(value, Console):
            raise TypeError('console deve ser uma instância de rich.Console')
        self._console = value
    
    @property
    def log_level(self) -> str:
        """Retorna o nível de log atual."""
        return self._log_level
    
    @log_level.setter
    def log_level(self, value: str):
        """Define o nível de log."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        value = value.upper()
        if value not in valid_levels:
            raise ValueError(f'log_level deve ser um de: {valid_levels}')
        self._log_level = value
    
    def disable_logging(self):
        """Desabilita completamente os logs do console."""
        self._verbose = False
    
    def enable_logging(self):
        """Habilita os logs do console."""
        self._verbose = True
    
    def print(self, message: str, level: str = 'INFO'):
        """
        Imprime mensagem apenas se verbose estiver habilitado.
        
        Args:
            message: Mensagem a ser exibida
            level: Nível do log ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        """
        if not self._verbose:
            return
        
        # Filtrar por nível de log
        level_priority = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        
        current_priority = level_priority.get(self._log_level, 1)
        message_priority = level_priority.get(level.upper(), 1)
        
        if message_priority >= current_priority:
            self._console.print(message)


# Instância global de configuração
config = ChatGraphConfig()


def configure(
    verbose: Optional[bool] = None,
    console: Optional[Console] = None,
    log_level: Optional[str] = None
):
    """
    Configura o ChatGraph globalmente.
    
    Args:
        verbose: Habilita/desabilita logs no console
        console: Instância customizada do Rich Console
        log_level: Nível de log ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    
    Exemplo:
        >>> from chatgraph import configure
        >>> configure(verbose=False)  # Desabilita logs
        >>> configure(log_level='ERROR')  # Mostra apenas erros
    """
    global config
    
    if verbose is not None:
        config.verbose = verbose
    
    if console is not None:
        config.console = console
    
    if log_level is not None:
        config.log_level = log_level
