import logging
import traceback
import functools
import discord
from typing import Callable, Any, Awaitable

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("discord_bot")

def error_handler(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    Decorador para tratamento de erros centralizado.
    
    Args:
        func: Função assíncrona a ser decorada
        
    Returns:
        Função decorada com tratamento de erros
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erro em {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Se for um comando do Discord, notificar o usuário
            if len(args) > 0 and hasattr(args[0], "followup"):
                interaction = args[0]
                try:
                    # Tenta enviar mensagem ao usuário
                    await interaction.followup.send(
                        "Ocorreu um erro ao processar seu comando. " +
                        "O erro foi registrado e será analisado.", 
                        ephemeral=True
                    )
                except Exception as follow_error:
                    # Se não conseguir enviar a mensagem, apenas loga
                    logger.error(f"Erro ao notificar usuário: {str(follow_error)}")
            return None
    return wrapper

class TaskError(Exception):
    """Exceção personalizada para erros relacionados a tarefas."""
    pass

class OpenProjectError(Exception):
    """Exceção personalizada para erros na API do OpenProject."""
    def __init__(self, message: str, status_code: int = None, api_message: str = None):
        self.status_code = status_code
        self.api_message = api_message
        super().__init__(message)