import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from utils.error_handler import error_handler, logger
from services.openproject_service import task_service
from ui.selects import ProjectSelectView
from utils.ui_utils import (
    get_status_info, create_progress_bar, LoadingEmbed, 
    create_approval_buttons, notify_channel
)
import asyncio
import config

class TaskCommands(commands.Cog):
    """Comandos para gerenciamento de tarefas."""
    
    def __init__(self, bot: commands.Bot):
        """
        Inicializa a Cog com referência ao bot.
        
        Args:
            bot: Instância do bot
        """
        self.bot = bot
    
    @app_commands.command(
        name="solicitar_tarefa", 
        description="Solicita a criação de uma nova tarefa no OpenProject."
    )
    @app_commands.describe(
        aprovador="Mencione o usuário que irá aprovar a tarefa (obrigatório)"
    )
    @error_handler
    async def solicitar_tarefa(self, interaction: discord.Interaction, aprovador: discord.Member) -> None:
        """
        Inicia o processo de solicitação de tarefa com interface melhorada.
        
        Args:
            interaction: Interação do Discord
            aprovador: Usuário que irá aprovar a tarefa
        """
        # Usar embed de carregamento para feedback visual
        loading_embed = LoadingEmbed(
            title="⏳ Carregando Projetos",
            description="Buscando projetos disponíveis no OpenProject..."
        )
        
        await interaction.response.send_message(
            embed=loading_embed,
            ephemeral=True
        )
        
        # Validação do aprovador
        if aprovador.bot:
            error_embed = discord.Embed(
                title="❌ Erro na Seleção",
                description="Não é possível selecionar um bot como aprovador.",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="Solução", 
                value="Por favor, mencione um usuário real como aprovador.", 
                inline=False
            )
            
            await interaction.edit_original_response(
                embed=error_embed,
                view=None
            )
            return
        
        try:
            # Busca projetos ativos
            projects = await task_service.get_projects()
            
            if not projects:
                no_projects_embed = discord.Embed(
                    title="⚠️ Nenhum Projeto Encontrado",
                    description="Não foram encontrados projetos ativos no OpenProject.",
                    color=discord.Color.gold()
                )
                no_projects_embed.add_field(
                    name="Sugestão", 
                    value="Verifique se há projetos cadastrados ou contate o administrador.", 
                    inline=False
                )
                
                await interaction.edit_original_response(
                    embed=no_projects_embed,
                    view=None
                )
                return
            
            # Cria interface paginada para seleção de projeto
            view = ProjectSelectView(projects, aprovador)
            
            # Atualiza a mensagem com a interface de seleção
            await interaction.edit_original_response(
                embed=view.embed,
                view=view
            )
            
        except Exception as e:
            logger.error(f"Erro ao buscar projetos: {str(e)}")
            
            error_embed = discord.Embed(
                title="❌ Erro ao Buscar Projetos",
                description=f"Ocorreu um erro ao buscar os projetos do OpenProject.",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="Detalhes do Erro", 
                value=f"```{str(e)}```", 
                inline=False
            )
            error_embed.add_field(
                name="Solução", 
                value="Verifique as configurações de conexão com o OpenProject ou tente novamente mais tarde.", 
                inline=False
            )
            
            await interaction.edit_original_response(
                embed=error_embed,
                view=None
            )


# Função para processamento de aprovação/rejeição
@error_handler
async def handle_approval(interaction: discord.Interaction, task_id: str, approved: bool, reject_reason: Optional[str] = None) -> None:
    """
    Processa aprovação ou rejeição de solicitação de tarefa com interface aprimorada.
    
    Args:
        interaction: Interação do Discord
        task_id: ID da tarefa sendo processada
        approved: True para aprovação, False para rejeição
        reject_reason: Motivo da rejeição (se aplicável)
    """
    await interaction.response.defer(ephemeral=True)
    
    # Verifica se a tarefa existe na fila
    task_details = task_service.get_pending_task(task_id)
    if not task_details:
        not_found_embed = discord.Embed(
            title="❌ Tarefa Não Encontrada",
            description="Esta solicitação de tarefa não foi encontrada ou já foi processada.",
            color=discord.Color.red()
        )
        
        await interaction.followup.send(
            embed=not_found_embed,
            ephemeral=True
        )
        return
    
    # Obtém o usuário solicitante
    try:
        solicitante = await interaction.client.fetch_user(task_details["solicitante_id"])
    except Exception as e:
        logger.error(f"Erro ao buscar solicitante: {str(e)}")
        
        error_embed = discord.Embed(
            title="❌ Erro ao Buscar Solicitante",
            description="Não foi possível localizar o usuário que solicitou esta tarefa.",
            color=discord.Color.red()
        )
        error_embed.add_field(
            name="Detalhes do Erro", 
            value=f"```{str(e)}```", 
            inline=False
        )
        
        await interaction.followup.send(
            embed=error_embed,
            ephemeral=True
        )
        return
    
    if approved:
        # Adiciona o nome do aprovador
        task_details["aprovador_nome"] = interaction.user.display_name
        
        try:
            # Cria a tarefa no OpenProject com feedback visual
            processing_embed = discord.Embed(
                title="⏳ Criando Tarefa",
                description=f"Enviando tarefa '{task_details['nome_da_tarefa']}' para o OpenProject...",
                color=discord.Color.gold()
            )
            
            await interaction.followup.send(
                embed=processing_embed,
                ephemeral=True
            )
            
            # Cria a tarefa no OpenProject
            logger.info(f"Criando tarefa no OpenProject: {task_details['nome_da_tarefa']}")
            result = await task_service.create_task(task_details)
            
            # Extrai link e ID da tarefa
            task_link = result.get("ui_link") or result.get("api_link")
            task_id_op = result.get("task_id")
            
            # Embed de sucesso para o solicitante
            success_embed = discord.Embed(
                title="✅ Tarefa Aprovada e Criada",
                description=f"**{task_details['nome_da_tarefa']}**",
                color=discord.Color.green(),
                url=task_link
            )
            success_embed.add_field(name="ID no OpenProject", value=task_id_op, inline=True)
            success_embed.add_field(name="Aprovado por", value=interaction.user.display_name, inline=True)
            success_embed.add_field(name="Projeto", value=task_details['project_name'], inline=True)
            
            # Adiciona barra de progresso para status
            status_info = get_status_info(2)  # ID 2 = Em andamento
            progress_bar = create_progress_bar(status_info["progress"])
            success_embed.add_field(
                name="Status", 
                value=f"{status_info['emoji']} {progress_bar} {status_info['name']}", 
                inline=False
            )
            
            success_embed.add_field(name="Link", value=f"[Abrir no OpenProject]({task_link})", inline=False)
            success_embed.timestamp = datetime.utcnow()
            
            # Notifica o solicitante
            await solicitante.send(embed=success_embed)
            
            # Embed de confirmação para o aprovador
            approve_embed = discord.Embed(
                title="✅ Tarefa Aprovada com Sucesso",
                description=f"A tarefa **{task_details['nome_da_tarefa']}** foi criada no OpenProject.",
                color=discord.Color.green(),
                url=task_link
            )
            approve_embed.add_field(name="ID", value=task_id_op, inline=True)
            approve_embed.add_field(name="Solicitante", value=task_details['solicitante_nome'], inline=True)
            approve_embed.timestamp = datetime.utcnow()
            
            # Atualiza a mensagem com o resultado
            await interaction.edit_original_response(
                embed=approve_embed
            )
            
            # Enviar para o canal de notificações, se configurado
            from cogs.settings_commands import server_settings
            if interaction.guild:
                notification_channel_id = server_settings.get_server_setting(
                    interaction.guild.id, 
                    "notification_channel",
                    config.DEFAULT_NOTIFICATION_CHANNEL
                )
                
                if notification_channel_id:
                    await notify_channel(
                        interaction.client, 
                        int(notification_channel_id), 
                        task_details, 
                        task_link
                    )
            
            # Enviar sistema de feedback após um breve delay
            await asyncio.sleep(3)
            feedback_embed = discord.Embed(
                title="📊 Avaliação do Processo",
                description="Por favor, avalie sua experiência com esta solicitação de tarefa:",
                color=discord.Color.blurple()
            )
            feedback_embed.add_field(name="⭐", value="Excelente", inline=True)
            feedback_embed.add_field(name="👍", value="Bom", inline=True)
            feedback_embed.add_field(name="👎", value="Precisa melhorar", inline=True)
            
            feedback_message = await solicitante.send(embed=feedback_embed)
            
            # Adicionar reações para feedback
            await feedback_message.add_reaction("⭐")
            await feedback_message.add_reaction("👍")
            await feedback_message.add_reaction("👎")
            
            # Log de auditoria
            logger.info(
                f"Tarefa aprovada: ID={task_id}, OpenProject ID={task_id_op}, "
                f"Aprovador={interaction.user.display_name}"
            )
            
            # Tentar criar uma thread para discussão
            try:
                if hasattr(interaction, "message") and interaction.message:
                    thread = await interaction.message.create_thread(
                        name=f"Tarefa: {task_details['nome_da_tarefa']}",
                        auto_archive_duration=1440  # 1 dia
                    )
                    
                    thread_embed = discord.Embed(
                        title="📝 Thread de Discussão",
                        description="Esta thread foi criada para discussão da tarefa. Todos os envolvidos podem colaborar aqui.",
                        color=discord.Color.brand_green()
                    )
                    thread_embed.add_field(
                        name="Link OpenProject", 
                        value=f"[Acessar Tarefa]({task_link})",
                        inline=False
                    )
                    
                    await thread.send(embed=thread_embed)
                    
                    # Adicionar os participantes
                    if interaction.guild:
                        solicitante_member = interaction.guild.get_member(solicitante.id)
                        if solicitante_member:
                            await thread.add_user(solicitante_member)
            except Exception as thread_error:
                # Apenas log, não interrompe o fluxo
                logger.error(f"Erro ao criar thread: {str(thread_error)}")
            
        except Exception as e:
            # Notifica erro na criação com embed visual
            error_embed = discord.Embed(
                title="⚠️ Erro na Criação da Tarefa",
                description=f"A tarefa '{task_details['nome_da_tarefa']}' foi aprovada, mas não pôde ser criada no OpenProject.",
                color=discord.Color.orange()
            )
            error_embed.add_field(
                name="Detalhes do Erro", 
                value=f"```{str(e)}```", 
                inline=False
            )
            error_embed.add_field(
                name="Próximos Passos", 
                value="Por favor, contate o administrador para resolver este problema.", 
                inline=False
            )
            
            # Enviar para o solicitante
            await solicitante.send(embed=error_embed)
            
            # Notificar o aprovador
            await interaction.edit_original_response(
                embed=error_embed
            )
            
            # Log de erro
            logger.error(f"Erro ao criar tarefa aprovada: {str(e)}")
    else:
        # Processa rejeição com embed visual
        motivo = reject_reason or "Não especificado"
        
        # Embed de rejeição para o solicitante
        reject_embed = discord.Embed(
            title="❌ Tarefa Reprovada",
            description=f"**{task_details['nome_da_tarefa']}**",
            color=discord.Color.red()
        )
        reject_embed.add_field(name="Reprovado por", value=interaction.user.display_name, inline=True)
        reject_embed.add_field(name="Projeto", value=task_details['project_name'], inline=True)
        reject_embed.add_field(name="Motivo", value=motivo, inline=False)
        reject_embed.timestamp = datetime.utcnow()
        
        # Notifica o solicitante
        await solicitante.send(embed=reject_embed)
        
        # Embed de confirmação para o aprovador
        approve_reject_embed = discord.Embed(
            title="❌ Tarefa Reprovada",
            description=f"A tarefa '{task_details['nome_da_tarefa']}' foi reprovada.",
            color=discord.Color.red()
        )
        approve_reject_embed.add_field(name="Solicitante", value=task_details['solicitante_nome'], inline=True)
        approve_reject_embed.add_field(name="Motivo", value=motivo, inline=False)
        approve_reject_embed.timestamp = datetime.utcnow()
        
        # Notifica o aprovador
        await interaction.followup.send(
            embed=approve_reject_embed,
            ephemeral=True
        )
        
        # Log de auditoria
        logger.info(
            f"Tarefa rejeitada: ID={task_id}, "
            f"Aprovador={interaction.user.display_name}, Motivo={motivo}"
        )
    
    # Remove a tarefa da lista de pendências
    task_service.remove_pending_task(task_id)
    
    try:
        # Desabilita os botões na mensagem original
        original_message = interaction.message
        if original_message:
            view = discord.ui.View.from_message(original_message)
            if view:
                for item in view.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True
                await original_message.edit(view=view)
    except Exception as e:
        logger.error(f"Erro ao atualizar mensagem original: {str(e)}")


# Função para setup da Cog
async def setup(bot: commands.Bot) -> None:
    """
    Registra a Cog no bot.
    
    Args:
        bot: Instância do bot
    """
    await bot.add_cog(TaskCommands(bot))