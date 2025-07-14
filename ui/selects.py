import discord
from typing import List, Dict, Any, Optional, Callable
from discord.interactions import Interaction
from datetime import datetime

from utils.string_utils import truncate_string
from utils.error_handler import error_handler, logger
from config import ITEMS_PER_PAGE, COLOR_PRIMARY

class ProjectSelect(discord.ui.Select):
    """Menu dropdown para seleção de projetos do OpenProject."""
    
    def __init__(self, projects: List[Dict[str, Any]], aprovador: discord.Member, page: int = 0):
        """
        Inicializa o select com as opções de projetos.
        
        Args:
            projects: Lista de projetos disponíveis
            aprovador: Usuário que irá aprovar a tarefa
            page: Página atual para paginação
        """
        self.aprovador = aprovador
        self.all_projects = projects
        self.page = page
        
        # Calcula índices para a página atual
        start_idx = page * ITEMS_PER_PAGE
        end_idx = min(start_idx + ITEMS_PER_PAGE, len(projects))
        
        # Projetos da página atual
        current_page_projects = projects[start_idx:end_idx]
        
        options = []
        for project in current_page_projects:
            # Adiciona ícone visual para os projetos
            options.append(discord.SelectOption(
                label=truncate_string(project['name'], 90),
                value=str(project['id']),
                description=f"ID: {project['id']}"[:100],
                emoji="📂"  # Ícone de pasta para todos os projetos
            ))
        
        super().__init__(
            placeholder=f"Selecione um projeto (Página {page+1}/{self.total_pages})",
            min_values=1, 
            max_values=1, 
            options=options
        )
    
    @property
    def total_pages(self) -> int:
        """Calcula o número total de páginas."""
        return (len(self.all_projects) - 1) // ITEMS_PER_PAGE + 1
    
    @error_handler
    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Processa a seleção do projeto e mostra as versões disponíveis.
        
        Args:
            interaction: Interação do Discord
        """
        # Identifica o projeto selecionado
        selected_project_id = self.values[0]
        selected_project_name = None
        
        # Busca o nome correspondente ao ID
        for option in self.options:
            if option.value == selected_project_id:
                selected_project_name = option.label
                break
        
        # Prepara dados parciais do projeto
        project_data = {
            "project_id": selected_project_id,
            "project_name": selected_project_name,
            "aprovador": self.aprovador
        }
        
        # Armazena temporariamente os dados
        if not hasattr(interaction.client, 'project_data'):
            interaction.client.project_data = {}
        interaction.client.project_data[interaction.user.id] = project_data
        
        # Feedback visual de carregamento
        loading_embed = discord.Embed(
            title="⏳ Carregando Versões",
            description=f"Buscando as versões disponíveis para o projeto **{selected_project_name}**...",
            color=discord.Color.gold()
        )
        
        await interaction.response.edit_message(
            embed=loading_embed,
            view=None
        )
        
        try:
            # Buscar versões para este projeto
            from services.openproject_service import task_service
            versions = await task_service.get_project_versions(selected_project_id)
            
            if not versions:
                # Se não houver versões, mostra um aviso e vai direto para o modal de tarefa
                no_versions_embed = discord.Embed(
                    title="⚠️ Nenhuma Versão Encontrada",
                    description=f"O projeto **{selected_project_name}** não possui versões definidas.",
                    color=discord.Color.orange()
                )
                no_versions_embed.add_field(
                    name="Próximos Passos", 
                    value="Criando a tarefa sem especificar uma versão...", 
                    inline=False
                )
                
                await interaction.edit_original_response(
                    embed=no_versions_embed
                )
                
                # Pequeno delay para o usuário ler a mensagem
                import asyncio
                await asyncio.sleep(2)
                
                # Abre modal para coletar detalhes da tarefa
                from ui.modals import TaskDetailsModal
                task_modal = TaskDetailsModal(
                    title=f"Detalhes da Tarefa - {selected_project_name}", 
                    task_data=project_data,
                    bot=interaction.client
                )
                
                # Enviamos um novo modal como uma nova interação, após o edit_original_response
                await interaction.followup.send(
                    "Preencha os detalhes da tarefa:",
                    ephemeral=True,
                    view=TaskModalButton(project_data)
                )
                
            else:
                # Exibe select para escolher a versão
                version_select_view = VersionSelectView(
                    versions, 
                    selected_project_id, 
                    selected_project_name, 
                    self.aprovador
                )
                
                await interaction.edit_original_response(
                    embed=version_select_view.embed,
                    view=version_select_view
                )
                
        except Exception as e:
            # Em caso de erro, exibe mensagem
            error_embed = discord.Embed(
                title="❌ Erro ao Carregar Versões",
                description=f"Erro ao buscar versões do projeto: {str(e)}",
                color=discord.Color.red()
            )
            
            await interaction.edit_original_response(
                embed=error_embed
            )
            logger.error(f"Erro ao buscar versões do projeto {selected_project_id}: {str(e)}")


class TaskModalButton(discord.ui.View):
    """Botão que abre o modal de criação de tarefa."""
    
    def __init__(self, task_data: Dict[str, Any]):
        """
        Inicializa o botão para abrir o modal.
        
        Args:
            task_data: Dados para a criação da tarefa
        """
        super().__init__(timeout=180)
        self.task_data = task_data
        
        # Adiciona botão para preencher detalhes
        continue_button = discord.ui.Button(
            label="Preencher Detalhes da Tarefa", 
            style=discord.ButtonStyle.primary,
            emoji="📝"
        )
        continue_button.callback = self.show_modal
        self.add_item(continue_button)
    
    @error_handler
    async def show_modal(self, interaction: discord.Interaction):
        """Abre o modal de detalhes da tarefa."""
        from ui.modals import TaskDetailsModal
        
        task_modal = TaskDetailsModal(
            title=f"Detalhes da Tarefa - {self.task_data['project_name']}", 
            task_data=self.task_data,
            bot=interaction.client
        )
        
        await interaction.response.send_modal(task_modal)


class VersionSelect(discord.ui.Select):
    """Menu dropdown para seleção de versões do projeto."""
    
    def __init__(self, versions: List[Dict[str, Any]], project_id: str, project_name: str, aprovador: discord.Member, page: int = 0):
        """
        Inicializa o select com as opções de versões.
        
        Args:
            versions: Lista de versões disponíveis
            project_id: ID do projeto selecionado
            project_name: Nome do projeto selecionado
            aprovador: Usuário que irá aprovar a tarefa
            page: Página atual para paginação
        """
        self.versions = versions
        self.project_id = project_id
        self.project_name = project_name
        self.aprovador = aprovador
        self.page = page
        
        # Calcula índices para a página atual
        items_per_page = ITEMS_PER_PAGE
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(versions))
        
        # Versões da página atual
        current_page_versions = versions[start_idx:end_idx]
        
        options = []
        for version in current_page_versions:
            # Adiciona ícone visual para as versões
            status_emoji = "🟢" if version.get('status') == 'open' else "🔴"  # Verde para aberto, vermelho para fechado
            
            options.append(discord.SelectOption(
                label=truncate_string(version['name'], 90),
                value=str(version['id']),
                description=f"Status: {version.get('status', 'N/A')}"[:100],
                emoji=status_emoji
            ))
        
        # Adiciona opção para "Sem versão" no final
        options.append(discord.SelectOption(
            label="Sem versão específica",
            value="0",
            description="Criar tarefa sem associar a uma versão",
            emoji="⚪"
        ))
        
        super().__init__(
            placeholder=f"Selecione a versão (Página {page+1}/{self.total_pages})",
            min_values=1, 
            max_values=1, 
            options=options
        )
    
    @property
    def total_pages(self) -> int:
        """Calcula o número total de páginas."""
        return max(1, (len(self.versions) - 1) // ITEMS_PER_PAGE + 1)
    
    @error_handler
    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Processa a seleção da versão e abre o modal de tarefa.
        
        Args:
            interaction: Interação do Discord
        """
        # Identifica a versão selecionada
        selected_version_id = self.values[0]
        selected_version_name = "Sem versão específica"
        
        # Busca o nome correspondente ao ID, se não for "Sem versão"
        if selected_version_id != "0":
            for option in self.options:
                if option.value == selected_version_id:
                    selected_version_name = option.label
                    break
        
        # Prepara dados completos para a tarefa
        task_data = {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "version_id": selected_version_id if selected_version_id != "0" else None,
            "version_name": selected_version_name if selected_version_id != "0" else None,
            "aprovador": self.aprovador
        }
        
        # Armazena temporariamente os dados
        if not hasattr(interaction.client, 'task_data'):
            interaction.client.task_data = {}
        interaction.client.task_data[interaction.user.id] = task_data
        
        # Feedback visual da seleção
        confirmation_embed = discord.Embed(
            title="✅ Versão Selecionada",
            description=f"Projeto: **{self.project_name}**\nVersão: **{selected_version_name}**",
            color=discord.Color.green()
        )
        confirmation_embed.set_footer(text="Abrindo formulário para detalhes da tarefa...")
        
        # Primeiro edita a mensagem para dar feedback
        await interaction.response.edit_message(
            embed=confirmation_embed,
            view=None  # Remove a view atual
        )
        
        # Em seguida, envia um botão para abrir o modal
        await interaction.followup.send(
            "Clique no botão abaixo para preencher os detalhes da tarefa:",
            ephemeral=True,
            view=TaskModalButton(task_data)
        )


class VersionSelectView(discord.ui.View):
    """View para seleção de versões com paginação."""
    
    def __init__(self, versions: List[Dict[str, Any]], project_id: str, project_name: str, aprovador: discord.Member):
        """
        Inicializa a view com controles de paginação.
        
        Args:
            versions: Lista de versões disponíveis
            project_id: ID do projeto selecionado
            project_name: Nome do projeto selecionado
            aprovador: Usuário que irá aprovar a tarefa
        """
        super().__init__(timeout=300)  # 5 minutos
        self.versions = versions
        self.project_id = project_id
        self.project_name = project_name
        self.aprovador = aprovador
        self.current_page = 0
        self.total_pages = max(1, (len(versions) - 1) // ITEMS_PER_PAGE + 1)
        
        # Cria embed informativo
        self.embed = discord.Embed(
            title="🏷️ Selecione a Versão",
            description=f"Projeto: **{project_name}**\n\nEscolha a versão para criar a tarefa ou selecione 'Sem versão específica'.",
            color=COLOR_PRIMARY
        )
        self.embed.add_field(
            name="Versões encontradas", 
            value=f"**{len(versions)}** versões disponíveis", 
            inline=True
        )
        self.embed.add_field(
            name="Aprovador", 
            value=aprovador.display_name, 
            inline=True
        )
        self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
        self.embed.timestamp = datetime.utcnow()
        
        # Adiciona o select inicial
        self.update_select()
        
        # Adiciona botões de navegação com emojis (apenas se houver mais de uma página)
        if self.total_pages > 1:
            self.prev_button = discord.ui.Button(
                label="Anterior", 
                emoji="◀️",
                disabled=True,
                style=discord.ButtonStyle.secondary,
                custom_id="prev"
            )
            self.prev_button.callback = self.prev_page
            
            self.next_button = discord.ui.Button(
                label="Próxima", 
                emoji="▶️",
                disabled=self.total_pages <= 1,
                style=discord.ButtonStyle.secondary,
                custom_id="next"
            )
            self.next_button.callback = self.next_page
            
            self.add_item(self.prev_button)
            self.add_item(self.next_button)
        
        # Botão para voltar à seleção de projeto
        self.back_button = discord.ui.Button(
            label="Voltar para Projetos", 
            emoji="🔙",
            style=discord.ButtonStyle.secondary,
            custom_id="back"
        )
        self.back_button.callback = self.back_to_projects
        self.add_item(self.back_button)
    
    def update_select(self) -> None:
        """Atualiza o select com as versões da página atual."""
        # Remove o select existente, se houver
        for item in self.children[:]:
            if isinstance(item, VersionSelect):
                self.remove_item(item)
        
        # Adiciona o novo select
        self.add_item(VersionSelect(
            self.versions, 
            self.project_id,
            self.project_name,
            self.aprovador, 
            self.current_page
        ))
    
    @error_handler
    async def prev_page(self, interaction: discord.Interaction) -> None:
        """
        Navega para a página anterior.
        
        Args:
            interaction: Interação do Discord
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_select()
            
            # Atualiza estado dos botões
            if hasattr(self, 'prev_button'):
                self.prev_button.disabled = self.current_page == 0
            if hasattr(self, 'next_button'):
                self.next_button.disabled = False
            
            # Atualiza o footer do embed
            self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
            
            await interaction.response.edit_message(
                embed=self.embed,
                view=self
            )
    
    @error_handler
    async def next_page(self, interaction: discord.Interaction) -> None:
        """
        Navega para a próxima página.
        
        Args:
            interaction: Interação do Discord
        """
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_select()
            
            # Atualiza estado dos botões
            if hasattr(self, 'prev_button'):
                self.prev_button.disabled = False
            if hasattr(self, 'next_button'):
                self.next_button.disabled = self.current_page >= self.total_pages - 1
            
            # Atualiza o footer do embed
            self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
            
            await interaction.response.edit_message(
                embed=self.embed, 
                view=self
            )
    
    @error_handler
    async def back_to_projects(self, interaction: discord.Interaction) -> None:
        """
        Volta para a seleção de projetos.
        
        Args:
            interaction: Interação do Discord
        """
        # Feedback visual de carregamento
        loading_embed = discord.Embed(
            title="⏳ Voltando para Projetos",
            description="Carregando a lista de projetos...",
            color=discord.Color.gold()
        )
        
        await interaction.response.edit_message(
            embed=loading_embed,
            view=None
        )
        
        try:
            # Busca projetos novamente
            from services.openproject_service import task_service
            projects = await task_service.get_projects()
            
            # Cria view de seleção de projetos
            project_view = ProjectSelectView(projects, self.aprovador)
            
            # Atualiza a mensagem
            await interaction.edit_original_response(
                embed=project_view.embed,
                view=project_view
            )
            
        except Exception as e:
            # Em caso de erro, mostra mensagem de erro
            error_embed = discord.Embed(
                title="❌ Erro ao Carregar Projetos",
                description=f"Não foi possível carregar a lista de projetos: {str(e)}",
                color=discord.Color.red()
            )
            
            await interaction.edit_original_response(
                embed=error_embed
            )


class ProjectSelectView(discord.ui.View):
    """View para seleção de projetos com paginação."""
    
    def __init__(self, projects: List[Dict[str, Any]], aprovador: discord.Member):
        """
        Inicializa a view com controles de paginação.
        
        Args:
            projects: Lista de projetos disponíveis
            aprovador: Usuário que irá aprovar a tarefa
        """
        super().__init__(timeout=300)  # 5 minutos
        self.projects = projects
        self.aprovador = aprovador
        self.current_page = 0
        self.total_pages = (len(projects) - 1) // ITEMS_PER_PAGE + 1
        
        # Cria embed informativo
        self.embed = discord.Embed(
            title="🔍 Selecione um Projeto",
            description="Escolha um projeto para criar a tarefa.\nUtilize os botões abaixo para navegar entre as páginas.",
            color=COLOR_PRIMARY
        )
        self.embed.add_field(
            name="Projetos encontrados", 
            value=f"**{len(projects)}** projetos ativos no OpenProject", 
            inline=True
        )
        self.embed.add_field(
            name="Aprovador", 
            value=aprovador.display_name, 
            inline=True
        )
        self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
        self.embed.timestamp = datetime.utcnow()
        
        # Adiciona o select inicial
        self.update_select()
        
        # Adiciona botões de navegação com emojis
        self.prev_button = discord.ui.Button(
            label="Anterior", 
            emoji="◀️",
            disabled=True,
            style=discord.ButtonStyle.secondary,
            custom_id="prev"
        )
        self.prev_button.callback = self.prev_page
        
        self.next_button = discord.ui.Button(
            label="Próxima", 
            emoji="▶️",
            disabled=self.total_pages <= 1,
            style=discord.ButtonStyle.secondary,
            custom_id="next"
        )
        self.next_button.callback = self.next_page
        
        self.refresh_button = discord.ui.Button(
            label="Atualizar", 
            emoji="🔄",
            style=discord.ButtonStyle.primary,
            custom_id="refresh"
        )
        self.refresh_button.callback = self.refresh_projects
        
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.refresh_button)
    
    def update_select(self) -> None:
        """Atualiza o select com os projetos da página atual."""
        # Remove o select existente, se houver
        for item in self.children[:]:
            if isinstance(item, ProjectSelect):
                self.remove_item(item)
        
        # Adiciona o novo select
        self.add_item(ProjectSelect(
            self.projects, 
            self.aprovador, 
            self.current_page
        ))
    
    @error_handler
    async def prev_page(self, interaction: discord.Interaction) -> None:
        """
        Navega para a página anterior.
        
        Args:
            interaction: Interação do Discord
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_select()
            
            # Atualiza estado dos botões
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = False
            
            # Atualiza o footer do embed
            self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
            
            await interaction.response.edit_message(
                embed=self.embed,
                view=self
            )
    
    @error_handler
    async def next_page(self, interaction: discord.Interaction) -> None:
        """
        Navega para a próxima página.
        
        Args:
            interaction: Interação do Discord
        """
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_select()
            
            # Atualiza estado dos botões
            self.prev_button.disabled = False
            self.next_button.disabled = self.current_page >= self.total_pages - 1
            
            # Atualiza o footer do embed
            self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
            
            await interaction.response.edit_message(
                embed=self.embed, 
                view=self
            )
    
    @error_handler
    async def refresh_projects(self, interaction: discord.Interaction) -> None:
        """
        Atualiza a lista de projetos.
        
        Args:
            interaction: Interação do Discord
        """
        # Feedback visual de carregamento
        loading_embed = discord.Embed(
            title="⏳ Atualizando Projetos",
            description="Buscando a lista atualizada de projetos no OpenProject...",
            color=discord.Color.gold()
        )
        
        await interaction.response.edit_message(
            embed=loading_embed,
            view=None
        )
        
        try:
            # Busca projetos atualizados
            from services.openproject_service import task_service
            self.projects = await task_service.get_projects()
            
            # Atualiza a paginação
            self.total_pages = (len(self.projects) - 1) // ITEMS_PER_PAGE + 1
            self.current_page = 0
            
            # Atualiza o embed
            self.embed.clear_fields()
            self.embed.add_field(
                name="Projetos encontrados", 
                value=f"**{len(self.projects)}** projetos ativos no OpenProject", 
                inline=True
            )
            self.embed.add_field(
                name="Aprovador", 
                value=self.aprovador.display_name, 
                inline=True
            )
            self.embed.set_footer(text=f"Página {self.current_page + 1} de {self.total_pages}")
            self.embed.timestamp = datetime.utcnow()
            
            # Atualiza os botões e select
            self.update_select()
            self.prev_button.disabled = True
            self.next_button.disabled = self.total_pages <= 1
            
            # Envia a mensagem atualizada
            await interaction.edit_original_response(
                embed=self.embed,
                view=self
            )
            
        except Exception as e:
            # Em caso de erro, mostra mensagem de erro
            error_embed = discord.Embed(
                title="❌ Erro ao Atualizar",
                description=f"Não foi possível atualizar a lista de projetos: {str(e)}",
                color=discord.Color.red()
            )
            
            await interaction.edit_original_response(
                embed=error_embed
            )