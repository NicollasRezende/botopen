import discord
from discord.ext import commands
import asyncio
import os
import sys
import traceback

import config
from utils.error_handler import logger

# Configura permissões do bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True  # Para o sistema de feedback com reações

# Inicializa o bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """Evento disparado quando o bot está pronto."""
    logger.info(f"Bot conectado como {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Discord.py versão: {discord.__version__}")
    logger.info("-" * 40)
    
    # Configura status personalizado
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="tarefas no OpenProject"
        )
    )
    
    try:
        # Sincroniza comandos slash
        synced = await bot.tree.sync()
        logger.info(f"Sincronizados {len(synced)} comandos slash")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")

async def setup_cogs():
    """Carrega todas as Cogs do diretório cogs/."""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            cog_name = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                logger.info(f"Cog carregada: {cog_name}")
            except Exception as e:
                logger.error(f"Erro ao carregar cog {cog_name}: {e}")
                traceback.print_exc()

@bot.event
async def on_reaction_add(reaction, user):
    """Processa reações para o sistema de feedback."""
    # Ignora reações do próprio bot
    if user.bot:
        return
        
    # Verifica se é uma reação de feedback (mensagem do bot com título específico)
    message = reaction.message
    if message.author.id != bot.user.id:
        return
        
    # Verifica se a mensagem tem embeds e se o título do primeiro embed é o de feedback
    if not message.embeds or not message.embeds[0].title or "Avaliação do Processo" not in message.embeds[0].title:
        return
        
    # Registra o feedback (em uma implementação completa, salvaria em banco de dados)
    feedback_map = {
        "⭐": "Excelente",
        "👍": "Bom", 
        "👎": "Precisa melhorar"
    }
    
    # Verifica se é uma das reações esperadas
    emoji = str(reaction.emoji)
    if emoji in feedback_map:
        logger.info(f"Feedback recebido de {user.display_name}: {feedback_map[emoji]}")
        
        # Opcional: enviar agradecimento via DM
        try:
            await user.send(
                embed=discord.Embed(
                    title="🙏 Obrigado pelo feedback!",
                    description=f"Agradecemos sua avaliação: **{feedback_map[emoji]}**",
                    color=discord.Color.blue()
                )
            )
        except:
            # Se não puder enviar DM, apenas continua
            pass

async def main():
    """Função principal do bot."""
    # Verifica variáveis de ambiente
    if not config.DISCORD_BOT_TOKEN:
        logger.error("Erro: Token do Discord não configurado em .env")
        return
        
    if not config.OPENPROJECT_URL:
        logger.error("Aviso: URL do OpenProject não configurada em .env")
        
    if not config.OPENPROJECT_API_KEY:
        logger.error("Aviso: API Key do OpenProject não configurada em .env")
    
    # Carrega cogs
    await setup_cogs()
    
    # Inicia o bot
    try:
        logger.info("Iniciando o bot...")
        await bot.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot desligado manualmente")
        await bot.close()
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
        traceback.print_exc()
    finally:
        if not bot.is_closed():
            await bot.close()
        logger.info("Bot finalizado")

# Ponto de entrada
if __name__ == "__main__":
    asyncio.run(main())