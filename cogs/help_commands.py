import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict

from utils.error_handler import error_handler

class HelpView(discord.ui.View):
    """View interativa para menu de ajuda."""
    
    def __init__(self):
        """Inicializa a view com menu de tópicos de ajuda."""
        super().__init__(timeout=300)
        
        # Adiciona um menu select para navegação
        options = [
            discord.SelectOption(
                label="Comandos Básicos", 
                description="Comandos básicos do bot",
                value="basic",
                emoji="📚"
            ),
            discord.SelectOption(
                label="Fluxo de Trabalho", 
                description="Como funciona o processo de tarefas",
                value="workflow",
                emoji="🔄"
            ),
            discord.SelectOption(
                label="Criar Tarefas", 
                description="Como solicitar e aprovar tarefas",
                value="tasks",
                emoji="✅"
            ),
            discord.SelectOption(
                label="Resolução de Problemas", 
                description="Soluções para problemas comuns",
                value="issues",
                emoji="🛠️"
            )
        ]
        
        self.help_select = discord.ui.Select(
            placeholder="Selecione um tópico de ajuda...",
            options=options
        )
        self.help_select.callback = self.on_select
        self.add_item(self.help_select)
        
        # Cria os embeds para cada seção
        self.embeds = {
            "basic": discord.Embed(
                title="📚 Comandos Básicos",
                description="Os comandos básicos do bot Discord-OpenProject",
                color=discord.Color.blue()
            ).add_field(
                name="/solicitar_tarefa",
                value="Inicia o processo de solicitação de uma nova tarefa no OpenProject",
                inline=False
            ).add_field(
                name="/dashboard",
                value="Mostra um painel com as tarefas pendentes de aprovação",
                inline=False
            ).add_field(
                name="/configurar",
                value="Permite configurar o bot para o servidor (apenas para administradores)",
                inline=False
            ).add_field(
                name="/ajuda",
                value="Mostra esta tela de ajuda",
                inline=False
            ),
            
            "workflow": discord.Embed(
                title="🔄 Fluxo de Trabalho",
                description="Como funciona o processo de tarefas",
                color=discord.Color.gold()
            ).add_field(
                name="Passo 1: Solicitação",
                value="Um usuário solicita a criação de uma tarefa usando o comando `/solicitar_tarefa`",
                inline=False
            ).add_field(
                name="Passo 2: Aprovação",
                value="O aprovador recebe a solicitação via mensagem privada e decide aprovar ou rejeitar",
                inline=False
            ).add_field(
                name="Passo 3: Criação",
                value="Se aprovada, a tarefa é criada automaticamente no OpenProject",
                inline=False
            ).add_field(
                name="Passo 4: Notificação",
                value="O solicitante recebe uma notificação com o link para a tarefa criada",
                inline=False
            ).add_field(
                name="Passo 5: Feedback",
                value="O solicitante pode fornecer feedback sobre o processo usando reações",
                inline=False
            ),
            
            "tasks": discord.Embed(
                title="✅ Criar Tarefas",
                description="Como solicitar e aprovar tarefas",
                color=discord.Color.green()
            ).add_field(
                name="Para solicitar uma tarefa:",
                value="1. Use `/solicitar_tarefa @aprovador`\n"
                      "2. Selecione um projeto na lista\n"
                      "3. Preencha os detalhes da tarefa no formulário\n"
                      "4. Aguarde a notificação de aprovação ou rejeição",
                inline=False
            ).add_field(
                name="Para aprovar uma tarefa:",
                value="1. Verifique a mensagem privada recebida\n"
                      "2. Revise os detalhes da tarefa\n"
                      "3. Clique em `Aprovar Tarefa` ou `Reprovar Tarefa`\n"
                      "4. Se reprovar, informe o motivo no formulário",
                inline=False
            ).add_field(
                name="Campos da tarefa:",
                value="**Nome da Tarefa**: Nome descritivo (obrigatório)\n"
                      "**Descrição**: Detalhes e contexto da tarefa\n"
                      "**Estimativa**: Tempo estimado em horas (ex: 2.5)\n"
                      "**Data de Início**: No formato DD/MM/AAAA\n"
                      "**Data de Término**: No formato DD/MM/AAAA",
                inline=False
            ),
            
            "issues": discord.Embed(
                title="🛠️ Resolução de Problemas",
                description="Soluções para problemas comuns",
                color=discord.Color.red()
            ).add_field(
                name="Não recebo mensagens do bot",
                value="Verifique se suas configurações de privacidade permitem mensagens diretas de membros do servidor.",
                inline=False
            ).add_field(
                name="Erro ao buscar projetos",
                value="Pode haver um problema de conexão com o OpenProject. Tente novamente ou contate o administrador.",
                inline=False
            ).add_field(
                name="Erro de validação de data",
                value="Certifique-se de usar o formato DD/MM/AAAA (ex: 15/05/2025).",
                inline=False
            ).add_field(
                name="Tarefa aprovada, mas não criada no OpenProject",
                value="Houve um erro na API do OpenProject. O erro foi registrado e o administrador foi notificado.",
                inline=False
            ).add_field(
                name="Como mudar o aprovador?",
                value="Infelizmente, não é possível mudar o aprovador após enviar a solicitação. Você precisará cancelar e criar uma nova solicitação.",
                inline=False
            ).add_field(
                name="Precisa de mais ajuda?",
                value="Contate o administrador do sistema para suporte adicional.",
                inline=False
            )
        }
        
        # Embed inicial
        self.current_embed = discord.Embed(
            title="🔍 Ajuda do Bot Discord-OpenProject",
            description="Selecione um tópico no menu abaixo para ver informações detalhadas.",
            color=discord.Color.blurple()
        ).add_field(
            name="Tópicos Disponíveis",
            value="📚 **Comandos Básicos**: Lista dos comandos disponíveis\n"
                  "🔄 **Fluxo de Trabalho**: Como funciona o processo\n"
                  "✅ **Criar Tarefas**: Como solicitar e aprovar tarefas\n"
                  "🛠️ **Resolução de Problemas**: Soluções para problemas comuns",
            inline=False
        )
    
    @error_handler
    async def on_select(self, interaction: discord.Interaction):
        """
        Callback quando um tópico é selecionado.
        
        Args:
            interaction: Interação do Discord
        """
        selected = self.help_select.values[0]
        self.current_embed = self.embeds.get(selected, self.current_embed)
        await interaction.response.edit_message(embed=self.current_embed)

class HelpCommands(commands.Cog):
    """Comandos de ajuda e suporte."""
    
    def __init__(self, bot):
        """
        Inicializa a Cog com referência ao bot.
        
        Args:
            bot: Instância do bot
        """
        self.bot = bot
    
    @app_commands.command(name="ajuda", description="Mostra ajuda sobre o bot e seus comandos")
    @error_handler
    async def help_command(self, interaction: discord.Interaction):
        """
        Mostra menu interativo de ajuda.
        
        Args:
            interaction: Interação do Discord
        """
        await interaction.response.defer(ephemeral=True)
        
        view = HelpView()
        await interaction.followup.send(
            embed=view.current_embed,
            view=view,
            ephemeral=True
        )

async def setup(bot):
    """
    Registra a Cog no bot.
    
    Args:
        bot: Instância do bot
    """
    await bot.add_cog(HelpCommands(bot))