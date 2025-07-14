import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Dict, Any, Optional

from utils.error_handler import error_handler, logger
from config import SETTINGS_FILE

# Criar uma instância global para acesso em outros módulos
class ServerSettings:
    """Gerenciador de configurações por servidor."""
    
    def __init__(self):
        """Inicializa o gerenciador de configurações."""
        self.settings = {}
        self.settings_file = SETTINGS_FILE
        self.load_settings()
        
    def load_settings(self):
        """Carrega configurações do arquivo."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar configurações: {e}")
                self.settings = {}
    
    def save_settings(self):
        """Salva configurações no arquivo."""
        try:
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
    
    def get_server_setting(self, guild_id, key, default=None):
        """
        Obtém uma configuração específica para um servidor.
        
        Args:
            guild_id: ID do servidor
            key: Chave da configuração
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da configuração ou valor padrão
        """
        guild_id = str(guild_id)
        if guild_id not in self.settings:
            return default
        return self.settings[guild_id].get(key, default)
    
    def set_server_setting(self, guild_id, key, value):
        """
        Define uma configuração para um servidor.
        
        Args:
            guild_id: ID do servidor
            key: Chave da configuração
            value: Valor da configuração
        """
        guild_id = str(guild_id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        self.settings[guild_id][key] = value
        self.save_settings()

# Instância global para uso em outros módulos
server_settings = ServerSettings()

class SettingsCommands(commands.Cog):
    """Comandos para configuração do bot por servidor."""
    
    def __init__(self, bot):
        """
        Inicializa a Cog com referência ao bot.
        
        Args:
            bot: Instância do bot
        """
        self.bot = bot
    
    @app_commands.command(
        name="configurar", 
        description="Configura opções do bot para este servidor"
    )
    @app_commands.describe(
        canal_notificacoes="Canal para enviar notificações de tarefas criadas"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @error_handler
    async def configure(self, interaction: discord.Interaction, canal_notificacoes: discord.TextChannel = None):
        """
        Configura as opções do bot para o servidor com interface visual.
        
        Args:
            interaction: Interação do Discord
            canal_notificacoes: Canal para notificações
        """
        await interaction.response.defer(ephemeral=True)
        
        # Verificar se é administrador (já feito pelo decorator, mas essa é outra opção)
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="❌ Permissão Negada",
                description="Você precisa ser um administrador para usar este comando.",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(
                embed=error_embed,
                ephemeral=True
            )
            return
            
        guild_id = interaction.guild.id
        
        # Configurar canal de notificações
        if canal_notificacoes:
            server_settings.set_server_setting(
                guild_id, 
                "notification_channel", 
                canal_notificacoes.id
            )
            
            success_embed = discord.Embed(
                title="✅ Configuração Atualizada",
                description=f"O canal de notificações foi definido como {canal_notificacoes.mention}.",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(
                embed=success_embed,
                ephemeral=True
            )
        
        # Criar embed com configurações atuais
        embed = discord.Embed(
            title="⚙️ Configurações do Bot",
            description="Configurações atuais para este servidor.",
            color=discord.Color.blurple()
        )
        
        # Obter configurações atuais
        notification_channel_id = server_settings.get_server_setting(
            guild_id, 
            "notification_channel"
        )
        
        if notification_channel_id:
            channel = self.bot.get_channel(notification_channel_id)
            channel_name = channel.mention if channel else "Canal não encontrado"
            embed.add_field(
                name="Canal de Notificações",
                value=channel_name,
                inline=False
            )
        else:
            embed.add_field(
                name="Canal de Notificações",
                value="Não configurado",
                inline=False
            )
            
        # Adicionar instruções de uso
        embed.add_field(
            name="Como Configurar",
            value="Use `/configurar canal_notificacoes:#canal` para definir o canal de notificações.",
            inline=False
        )
        
        # Só envia se não foi uma atualização
        if not canal_notificacoes:
            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

async def setup(bot):
    """
    Registra a Cog no bot.
    
    Args:
        bot: Instância do bot
    """
    await bot.add_cog(SettingsCommands(bot))