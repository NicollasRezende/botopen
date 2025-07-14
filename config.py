import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Configurações do OpenProject
OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
OPENPROJECT_API_KEY = os.getenv("OPENPROJECT_API_KEY")

# Configurações de cache
CACHE_DURATION = 3600  # 1 hora em segundos

# Configurações de interface
UI_TIMEOUT = 300  # 5 minutos em segundos
ITEMS_PER_PAGE = 10  # Itens por página em menus paginados

# Cores padrão para interface
COLOR_PRIMARY = 0x3498db  # Azul
COLOR_SUCCESS = 0x2ecc71  # Verde
COLOR_WARNING = 0xf39c12  # Laranja
COLOR_DANGER = 0xe74c3c   # Vermelho
COLOR_INFO = 0x9b59b6     # Roxo

# Emojis para status
STATUS_EMOJIS = {
    "novo": "🆕",
    "em_andamento": "🔄",
    "concluido": "✅",
    "aprovado": "✔️",
    "rejeitado": "❌",
    "feedback": "💬",
    "bloqueado": "🔒",
    "aguardando": "⏳"
}

# Canais padrão
DEFAULT_NOTIFICATION_CHANNEL = os.getenv("DEFAULT_NOTIFICATION_CHANNEL")

# Diretório de dados
DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "server_settings.json")

# Criar diretório de dados se não existir
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)