import discord
from typing import Dict, Any, Optional, List, Union
import asyncio

from config import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING, STATUS_EMOJIS

class LoadingEmbed(discord.Embed):
    """Embed especial para indicar carregamento."""
    
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None):
        """
        Cria um embed com aparência de carregamento.
        
        Args:
            title: Título do embed (padrão: "⏳ Carregando...")
            description: Descrição do embed (padrão: "Por favor, aguarde...")
        """
        super().__init__(
            title=title or "⏳ Carregando...",
            description=description or "Por favor, aguarde enquanto processamos sua solicitação.",
            color=COLOR_WARNING
        )
        # Adicionar animação com caracteres unicode
        self.add_field(
            name="Status", 
            value="```\n⠋ Processando...\n```", 
            inline=False
        )

def create_progress_bar(progress: float, length: int = 10) -> str:
    """
    Cria uma barra de progresso visual usando caracteres Unicode.
    
    Args:
        progress: Valor de 0 a 1 representando o progresso
        length: Comprimento da barra em caracteres
        
    Returns:
        String contendo a barra de progresso visual
    """
    filled = int(progress * length)
    empty = length - filled
    
    # Usando blocos completos e vazios para visual
    return "█" * filled + "░" * empty

def get_status_info(status_id: int) -> Dict[str, Any]:
    """
    Retorna informações de status com cores e emojis.
    
    Args:
        status_id: ID do status no OpenProject
        
    Returns:
        Dicionário com informações do status
    """
    status_map = {
        1: {"name": "Novo", "emoji": "🆕", "color": discord.Color.light_grey(), "progress": 0.0},
        2: {"name": "Em Andamento", "emoji": "🔄", "color": discord.Color.blue(), "progress": 0.25},
        3: {"name": "Resolvido", "emoji": "✔️", "color": discord.Color.green(), "progress": 0.75},
        4: {"name": "Feedback", "emoji": "💬", "color": discord.Color.gold(), "progress": 0.5},
        5: {"name": "Fechado", "emoji": "🎯", "color": discord.Color.dark_green(), "progress": 1.0},
        6: {"name": "Rejeitado", "emoji": "❌", "color": discord.Color.red(), "progress": 0.0},
        # Outros status conforme necessário
    }
    
    return status_map.get(status_id, {"name": "Desconhecido", "emoji": "❓", "color": discord.Color.default(), "progress": 0.0})

def create_approval_buttons(task_id: str) -> tuple:
    """
    Cria botões de aprovação/rejeição com emojis.
    
    Args:
        task_id: ID da tarefa sendo processada
        
    Returns:
        Tupla com (view, approve_button, reject_button)
    """
    view = discord.ui.View(timeout=None)
    
    approve_button = discord.ui.Button(
        label="Aprovar Tarefa", 
        emoji="✅",
        style=discord.ButtonStyle.success, 
        custom_id=f"approve_{task_id}"
    )
    
    reject_button = discord.ui.Button(
        label="Reprovar Tarefa", 
        emoji="❌",
        style=discord.ButtonStyle.danger, 
        custom_id=f"reject_{task_id}"
    )
    
    view.add_item(approve_button)
    view.add_item(reject_button)
    return view, approve_button, reject_button

async def notify_channel(bot, channel_id: int, task_details: Dict[str, Any], openproject_link: str):
    """
    Notifica um canal público sobre tarefa aprovada.
    
    Args:
        bot: Instância do bot
        channel_id: ID do canal para notificação
        task_details: Detalhes da tarefa aprovada
        openproject_link: Link para a tarefa no OpenProject
    """
    from utils.error_handler import logger
    
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            return
            
        embed = discord.Embed(
            title="🔔 Nova Tarefa Criada",
            url=openproject_link,
            description=f"**{task_details['nome_da_tarefa']}**",
            color=discord.Color.brand_green()
        )
        
        # Adicionar campos com informações
        embed.add_field(name="Projeto", value=task_details['project_name'], inline=True)
        embed.add_field(name="Solicitado por", value=task_details['solicitante_nome'], inline=True)
        embed.add_field(name="Aprovado por", value=task_details['aprovador_nome'], inline=True)
        
        # Tags para facilitar busca e filtros
        tags = []
        if task_details.get('estimativa'):
            try:
                estimativa = float(task_details['estimativa'])
                if estimativa > 8:
                    tags.append("⏱️ Grande")
                else:
                    tags.append("⏱️ Pequena")
            except (ValueError, TypeError):
                pass
                
        if tags:
            embed.add_field(name="Tags", value=" ".join(tags), inline=False)
            
        # Adicionar timestamp
        from datetime import datetime
        embed.timestamp = datetime.utcnow()
        
        await channel.send(embed=embed)
    except Exception as e:
        # Log do erro mas não falha o processo principal
        logger.error(f"Erro ao notificar canal: {str(e)}")

class ConfirmationView(discord.ui.View):
    """View com botões para confirmação."""
    
    def __init__(self, timeout: int = 180):
        """
        Inicializa a view com botões de confirmação.
        
        Args:
            timeout: Tempo em segundos antes da view expirar
        """
        super().__init__(timeout=timeout)
        self.value = None
        
        # Botão de confirmação
        confirm_button = discord.ui.Button(
            label="Confirmar",
            style=discord.ButtonStyle.success,
            emoji="✅"
        )
        confirm_button.callback = self.confirm_callback
        
        # Botão de cancelamento
        cancel_button = discord.ui.Button(
            label="Cancelar",
            style=discord.ButtonStyle.secondary,
            emoji="❌"
        )
        cancel_button.callback = self.cancel_callback
        
        self.add_item(confirm_button)
        self.add_item(cancel_button)
    
    async def confirm_callback(self, interaction: discord.Interaction):
        """Callback para confirmação."""
        self.value = True
        await interaction.response.defer()
        self.stop()
    
    async def cancel_callback(self, interaction: discord.Interaction):
        """Callback para cancelamento."""
        self.value = False
        await interaction.response.defer()
        self.stop()