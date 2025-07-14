import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Dict, Any
from datetime import datetime

from services.openproject_service import task_service
from utils.error_handler import error_handler, logger
from utils.ui_utils import get_status_info, create_progress_bar

class TaskDashboard(discord.ui.View):
    """Dashboard interativo para visualização de tarefas pendentes."""
    
    def __init__(self, pending_tasks: List[Dict[str, Any]]):
        """
        Inicializa o dashboard com os dados das tarefas.
        
        Args:
            pending_tasks: Lista de tarefas pendentes
        """
        super().__init__(timeout=180)
        self.pending_tasks = pending_tasks
        self.current_page = 0
        self.tasks_per_page = 5
        self.total_pages = max(1, (len(pending_tasks) - 1) // self.tasks_per_page + 1)
        
        # Adicionar botões de navegação
        self.prev_button = discord.ui.Button(
            label="Anterior", 
            emoji="◀️",
            disabled=True,
            style=discord.ButtonStyle.secondary
        )
        self.prev_button.callback = self.prev_page
        
        self.next_button = discord.ui.Button(
            label="Próxima",
            emoji="▶️",
            disabled=self.total_pages <= 1,
            style=discord.ButtonStyle.secondary
        )
        self.next_button.callback = self.next_page
        
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        
        # Adicionar botão para atualizar
        self.refresh_button = discord.ui.Button(
            label="Atualizar",
            emoji="🔄",
            style=discord.ButtonStyle.primary
        )
        self.refresh_button.callback = self.refresh
        self.add_item(self.refresh_button)
    
    def get_current_embed(self) -> discord.Embed:
        """
        Cria um embed para a página atual do dashboard.
        
        Returns:
            discord.Embed: Embed formatado com as tarefas da página atual
        """
        embed = discord.Embed(
            title="📋 Dashboard de Tarefas Pendentes",
            description="Visualização das tarefas aguardando aprovação.",
            color=discord.Color.blue()
        )
        
        start_idx = self.current_page * self.tasks_per_page
        end_idx = min(start_idx + self.tasks_per_page, len(self.pending_tasks))
        
        if not self.pending_tasks:
            embed.add_field(
                name="Nenhuma tarefa pendente",
                value="Não há tarefas aguardando aprovação no momento.",
                inline=False
            )
            return embed
        
        for i, task in enumerate(self.pending_tasks[start_idx:end_idx], start=1):
            status_emoji = "🟡"  # Amarelo para pendente
            
            # Cria uma barra de progresso visual
            progress_bar = create_progress_bar(0.0)  # 0% de progresso para pendentes
            
            embed.add_field(
                name=f"{status_emoji} {task['nome_da_tarefa']}",
                value=(
                    f"**Projeto:** {task['project_name']}\n"
                    f"**Solicitante:** {task['solicitante_nome']}\n"
                    f"**Status:** {progress_bar} Pendente\n"
                    f"**Estimativa:** {task['estimativa'] or 'N/A'}\n"
                    f"**ID:** `{task['task_id'] if 'task_id' in task else 'N/A'}`"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages} • Total: {len(self.pending_tasks)} tarefas")
        embed.timestamp = datetime.utcnow()
        return embed
    
    @error_handler
    async def prev_page(self, interaction: discord.Interaction):
        """
        Navega para a página anterior.
        
        Args:
            interaction: Interação do Discord
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = False
            await interaction.response.edit_message(
                embed=self.get_current_embed(),
                view=self
            )
    
    @error_handler
    async def next_page(self, interaction: discord.Interaction):
        """
        Navega para a próxima página.
        
        Args:
            interaction: Interação do Discord
        """
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.prev_button.disabled = False
            self.next_button.disabled = self.current_page >= self.total_pages - 1
            await interaction.response.edit_message(
                embed=self.get_current_embed(),
                view=self
            )
    
    @error_handler
    async def refresh(self, interaction: discord.Interaction):
        """
        Atualiza o dashboard com dados recentes.
        
        Args:
            interaction: Interação do Discord
        """
        # Primeiro fornece feedback visual de atualização
        loading_embed = discord.Embed(
            title="⏳ Atualizando Dashboard",
            description="Buscando as tarefas pendentes mais recentes...",
            color=discord.Color.gold()
        )
        
        await interaction.response.edit_message(
            embed=loading_embed,
            view=None
        )
        
        try:
            # Na implementação real, você buscaria os dados atualizados
            # Para o exemplo, vamos apenas mostrar a mensagem de sucesso
            
            # Obter tarefas pendentes atualizadas
            pending_tasks = []
            for task_id, task_details in task_service.pending_tasks.items():
                task_info = task_details.copy()
                task_info['task_id'] = task_id
                pending_tasks.append(task_info)
                
            self.pending_tasks = pending_tasks
            self.total_pages = max(1, (len(pending_tasks) - 1) // self.tasks_per_page + 1)
            self.current_page = 0
            
            # Atualizar os botões
            self.prev_button.disabled = True
            self.next_button.disabled = self.total_pages <= 1
            
            # Renderizar o dashboard atualizado
            updated_embed = self.get_current_embed()
            updated_embed.description = "✅ Dashboard atualizado com sucesso!"
            
            await interaction.edit_original_response(
                embed=updated_embed,
                view=self
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar dashboard: {str(e)}")
            
            # Exibir mensagem de erro
            error_embed = discord.Embed(
                title="❌ Erro ao Atualizar",
                description=f"Ocorreu um erro ao atualizar o dashboard: {str(e)}",
                color=discord.Color.red()
            )
            
            await interaction.edit_original_response(
                embed=error_embed
            )

class DashboardCommands(commands.Cog):
    """Comandos para visualização e gerenciamento de dashboards."""
    
    def __init__(self, bot):
        """
        Inicializa a Cog com referência ao bot.
        
        Args:
            bot: Instância do bot
        """
        self.bot = bot
    
    @app_commands.command(
        name="dashboard", 
        description="Mostra um dashboard das tarefas pendentes de aprovação"
    )
    @error_handler
    async def dashboard(self, interaction: discord.Interaction):
        """
        Mostra um dashboard interativo das tarefas pendentes.
        
        Args:
            interaction: Interação do Discord
        """
        await interaction.response.defer(ephemeral=True)
        
        # Obter tarefas pendentes do serviço
        pending_tasks = []
        for task_id, task_details in task_service.pending_tasks.items():
            task_info = task_details.copy()
            task_info['task_id'] = task_id
            pending_tasks.append(task_info)
        
        # Criar e enviar o dashboard
        view = TaskDashboard(pending_tasks)
        
        # Customização do embed de acordo com a quantidade de tarefas
        if pending_tasks:
            await interaction.followup.send(
                embed=view.get_current_embed(),
                view=view,
                ephemeral=True
            )
        else:
            # Mensagem especial para nenhuma tarefa
            empty_embed = discord.Embed(
                title="📋 Dashboard de Tarefas",
                description="Não há tarefas pendentes de aprovação no momento.",
                color=discord.Color.blue()
            )
            empty_embed.add_field(
                name="Criar Nova Tarefa", 
                value="Use o comando `/solicitar_tarefa` para solicitar a criação de uma nova tarefa.", 
                inline=False
            )
            empty_embed.set_footer(text="O dashboard será atualizado automaticamente quando novas tarefas forem solicitadas.")
            
            await interaction.followup.send(
                embed=empty_embed,
                ephemeral=True
            )

async def setup(bot):
    """
    Registra a Cog no bot.
    
    Args:
        bot: Instância do bot
    """
    await bot.add_cog(DashboardCommands(bot))