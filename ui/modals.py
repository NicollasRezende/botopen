import discord
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from utils.date_utils import validate_date, compare_dates
from utils.error_handler import error_handler, logger
from utils.ui_utils import create_approval_buttons

class TaskDetailsModal(discord.ui.Modal):
    """Modal para entrada de detalhes da tarefa."""
    
    def __init__(self, title: str, task_data: Dict[str, Any], bot):
        """
        Inicializa o modal com os campos necessários.
        
        Args:
            title: Título do modal
            task_data: Dados iniciais da tarefa
            bot: Instância do bot para acesso a dados
        """
        super().__init__(title=title)
        self.bot = bot
        self.task_data = task_data
        
        # Log dos dados recebidos para diagnóstico
        logger.debug(f"Dados recebidos no modal: {task_data}")
        
        # Campo para nome da tarefa
        self.task_name = discord.ui.TextInput(
            label="Nome da Tarefa",
            placeholder="Digite o nome da tarefa",
            required=True
        )
        self.add_item(self.task_name)
        
        # Campo para descrição (multilinhas)
        self.task_description = discord.ui.TextInput(
            label="Descrição",
            placeholder="Digite a descrição da tarefa",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.task_description)
        
        # Campo para estimativa de horas
        self.task_estimate = discord.ui.TextInput(
            label="Estimativa (horas)",
            placeholder="Digite a estimativa em horas (ex: 2.5)",
            required=False
        )
        self.add_item(self.task_estimate)
        
        # Campo para data de início
        self.start_date = discord.ui.TextInput(
            label="Data de Início",
            placeholder="Digite a data de início (DD/MM/AAAA)",
            required=False
        )
        self.add_item(self.start_date)
        
        # Campo para data de término
        self.due_date = discord.ui.TextInput(
            label="Data de Término",
            placeholder="Digite a data de término (DD/MM/AAAA)",
            required=False
        )
        self.add_item(self.due_date)
    
    @error_handler
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """
        Processa o envio do formulário com validação completa.
        
        Args:
            interaction: Interação do Discord
        """
        await interaction.response.defer(ephemeral=True)
        
        # Validação do formato da estimativa
        if self.task_estimate.value and not self.task_estimate.value.replace('.', '', 1).isdigit():
            error_embed = discord.Embed(
                title="❌ Erro de Validação",
                description="A estimativa deve conter apenas números (ex: 2.5).",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="Solução", 
                value="Por favor, insira um número válido ou deixe em branco.", 
                inline=False
            )
            
            await interaction.followup.send(
                embed=error_embed,
                ephemeral=True
            )
            return
        
        # Validação do formato das datas
        if not validate_date(self.start_date.value):
            error_embed = discord.Embed(
                title="❌ Erro de Validação",
                description="A data de início deve estar no formato DD/MM/AAAA (ex: 15/05/2025).",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(
                embed=error_embed,
                ephemeral=True
            )
            return
            
        if not validate_date(self.due_date.value):
            error_embed = discord.Embed(
                title="❌ Erro de Validação",
                description="A data de término deve estar no formato DD/MM/AAAA (ex: 30/05/2025).",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(
                embed=error_embed,
                ephemeral=True
            )
            return
        
        # Validação de consistência entre datas
        is_valid, error_message = compare_dates(self.start_date.value, self.due_date.value)
        if not is_valid:
            error_embed = discord.Embed(
                title="❌ Erro de Validação",
                description=error_message,
                color=discord.Color.red()
            )
            
            await interaction.followup.send(
                embed=error_embed,
                ephemeral=True
            )
            return
        
        # Recupera dados do projeto selecionado
        from services.openproject_service import task_service
        
        project_id = self.task_data.get("project_id")
        project_name = self.task_data.get("project_name")
        aprovador = self.task_data.get("aprovador")
        
        if not project_id:
            error_embed = discord.Embed(
                title="❌ Erro",
                description="Nenhum projeto selecionado. Por favor, tente novamente.",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(
                embed=error_embed,
                ephemeral=True
            )
            return
        
        # Consolida os dados da tarefa - ADICIONANDO INFORMAÇÕES DE VERSÃO
        task_details = {
            "nome_da_tarefa": self.task_name.value,
            "descricao": self.task_description.value,
            "estimativa": self.task_estimate.value,
            "data_inicio": self.start_date.value,
            "data_fim": self.due_date.value,
            "status": "Em andamento",  # Status fixo
            "status_id": 2,  # ID fixo para "Em andamento"
            "project_id": project_id,
            "project_name": project_name,
            "solicitante_id": interaction.user.id,
            "solicitante_nome": interaction.user.display_name,
            "analista_id": aprovador.id,
            "analista_nome": aprovador.display_name,
            # Adicionando informações de versão
            "version_id": self.task_data.get("version_id"),
            "version_name": self.task_data.get("version_name")
        }
        
        # Log para diagnóstico
        logger.info(f"Dados da tarefa consolidados: project_id={project_id}, version_id={self.task_data.get('version_id')}")
        
        # Gera um ID único para a solicitação e armazena
        task_id = f"{interaction.user.id}_{interaction.id}"
        task_service.add_pending_task(task_id, task_details)
        
        # Criar botões de aprovação com emojis
        view, approve_button, reject_button = create_approval_buttons(task_id)
        
        # Define callbacks para botões
        async def approve_callback(interaction_analista: discord.Interaction):
            from cogs.task_commands import handle_approval
            await handle_approval(interaction_analista, task_id, True)
        
        async def reject_callback(interaction_analista: discord.Interaction):
            # Abre modal para justificar rejeição
            reject_modal = RejectReasonModal(task_id)
            await interaction_analista.response.send_modal(reject_modal)

        approve_button.callback = approve_callback
        reject_button.callback = reject_callback
        
        # Prepara mensagem detalhada para o aprovador com embed rico
        dm_embed = discord.Embed(
            title="✅ Nova Solicitação de Tarefa",
            description=f"**{task_details['nome_da_tarefa']}**",
            color=discord.Color.blue()
        )
        
        # Adicionar campos organizados
        dm_embed.add_field(name="Projeto", value=task_details['project_name'], inline=True)
        
        # Adiciona campo de versão se disponível
        if task_details.get('version_name'):
            dm_embed.add_field(name="Versão", value=task_details['version_name'], inline=True)
            
        dm_embed.add_field(name="Status Inicial", value="Em andamento", inline=True)
        dm_embed.add_field(name="Solicitante", value=interaction.user.display_name, inline=True)
        
        dm_embed.add_field(name="Estimativa", value=task_details['estimativa'] or "Não especificada", inline=True)
        dm_embed.add_field(name="Data de Início", value=task_details['data_inicio'] or "Não especificada", inline=True)
        dm_embed.add_field(name="Data de Término", value=task_details['data_fim'] or "Não especificada", inline=True)
        
        dm_embed.add_field(name="Descrição", value=task_details['descricao'] or "Não especificada", inline=False)
        
        dm_embed.set_footer(text=f"ID da Solicitação: {task_id}")
        dm_embed.timestamp = datetime.utcnow()
        
        # Envia mensagem ao aprovador
        await aprovador.send(embed=dm_embed, view=view)
        
        # Prepara mensagem de confirmação para o solicitante
        confirm_embed = discord.Embed(
            title="📤 Solicitação Enviada",
            description=f"Sua solicitação para a tarefa **{task_details['nome_da_tarefa']}** foi enviada para aprovação.",
            color=discord.Color.green()
        )
        confirm_embed.add_field(name="Aprovador", value=aprovador.display_name, inline=True)
        confirm_embed.add_field(name="Projeto", value=task_details['project_name'], inline=True)
        
        # Adiciona campo de versão se disponível
        if task_details.get('version_name'):
            confirm_embed.add_field(name="Versão", value=task_details['version_name'], inline=True)
            
        confirm_embed.set_footer(text="Você receberá uma notificação quando for processada.")
        confirm_embed.timestamp = datetime.utcnow()
        
        # Envia confirmação ao solicitante
        await interaction.followup.send(
            embed=confirm_embed,
            ephemeral=True
        )
        
        # Log de auditoria
        logger.info(
            f"Nova solicitação de tarefa: ID={task_id}, Projeto={project_name}, "
            f"Versão={task_details.get('version_name', 'Nenhuma')}, "
            f"Solicitante={interaction.user.display_name}, Aprovador={aprovador.display_name}"
        )


class RejectReasonModal(discord.ui.Modal):
    """Modal para justificativa de rejeição de tarefa."""
    
    def __init__(self, task_id: str):
        """
        Inicializa o modal com o campo para justificativa.
        
        Args:
            task_id: ID da tarefa sendo rejeitada
        """
        super().__init__(title="Justificativa de Rejeição")
        self.task_id = task_id
        
        # Campo para o motivo da rejeição
        self.reject_reason = discord.ui.TextInput(
            label="Motivo da Rejeição",
            placeholder="Digite o motivo pelo qual está rejeitando esta tarefa",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reject_reason)
    
    @error_handler
    async def on_submit(self, interaction: discord.Interaction) -> None:
        """
        Processa o envio da justificativa de rejeição.
        
        Args:
            interaction: Interação do Discord
        """
        # Encaminha para o handler de aprovação com flag de rejeição
        from cogs.task_commands import handle_approval
        await handle_approval(interaction, self.task_id, False, self.reject_reason.value)