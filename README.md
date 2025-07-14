# Bot de Integração Discord-OpenProject

## Visão Geral
Um bot para Discord que integra com o OpenProject para otimizar o fluxo de criação de tarefas. O bot permite que membros da equipe solicitem a criação de tarefas através do Discord, com um processo de aprovação integrado que encaminha solicitações para revisores designados, que podem aprovar ou rejeitar as tarefas antes de serem criadas no OpenProject.

## Requisitos
- Python 3.8+
- Biblioteca discord.py
- python-dotenv
- requests

## Configuração
1. Clone o repositório
2. Instale as dependências:
   ```
   pip install discord.py python-dotenv requests
   ```
3. Crie um arquivo `.env` com as seguintes variáveis:
   ```
   DISCORD_BOT_TOKEN=seu_token_do_bot_discord
   OPENPROJECT_URL=sua_url_do_openproject
   OPENPROJECT_API_KEY=sua_chave_api_do_openproject
   ```
4. Execute o bot:
   ```
   python main.py
   ```

## Arquitetura

### Componentes Principais
- **Interface Discord**: Construída usando discord.py, gerencia interações de usuário, comandos slash e componentes de UI
- **Cliente OpenProject**: Administra a comunicação com a API do OpenProject
- **Cache de Projetos**: Armazena dados de projetos por 1 hora para reduzir chamadas à API
- **Gerenciamento de Tarefas**: Trata da criação de solicitações, fluxo de aprovação e submissão de tarefas

### Fluxo de Dados
1. Usuário inicia uma solicitação de tarefa via comando slash
2. Bot busca a lista de projetos do OpenProject (ou do cache)
3. Usuário seleciona o projeto e fornece detalhes da tarefa
4. Solicitação é enviada para o aprovador designado via mensagem direta
5. Aprovador aceita ou rejeita a solicitação
6. Na aprovação, a tarefa é criada no OpenProject com status "Em andamento"
7. Solicitante recebe notificação de aprovação/rejeição

## Funcionalidades

### Comandos do Discord
- `/solicitar_tarefa` - Inicia o fluxo de trabalho de criação de tarefa

### Componentes de Interface do Usuário
- **Seleção de Projeto**: Menu dropdown com projetos ativos do OpenProject
- **Modal de Detalhes da Tarefa**: Formulário para inserir nome, descrição, estimativa de tempo e datas
- **Botões de Aprovação**: Interface interativa para aprovadores aceitarem/rejeitarem tarefas
- **Modal de Rejeição**: Formulário para fornecer justificativa de rejeição

### Gerenciamento de Tarefas
- Cache de projetos para reduzir carga na API
- Validação de entrada para estimativas de tempo numéricas
- Validação de data no formato DD/MM/AAAA
- Status automático "Em andamento" para todas as tarefas criadas
- Formatação de duração ISO8601 para compatibilidade com OpenProject
- Fluxo completo de aprovação com notificações
- Tratamento de erros para interações com API

### Segurança e Validação
- Valida menções de aprovadores (impede menções a bots)
- Valida entrada numérica para estimativas de tempo
- Valida formato de data e lógica (data fim não pode ser anterior à data início)
- Configuração baseada em variáveis de ambiente
- Autenticação de API via tokens

## Exemplo de Fluxo de Trabalho

1. Membro da equipe usa o comando `/solicitar_tarefa @aprovador`
2. Membro seleciona um projeto do menu dropdown
3. Membro preenche formulário com nome, descrição, estimativa e datas (início/fim)
4. Solicitação é enviada ao aprovador via mensagem direta
5. Aprovador revisa a solicitação e:
   - Aprova, criando a tarefa no OpenProject com status "Em andamento"
   - Rejeita com uma justificativa
6. O solicitante original recebe notificação do resultado

## Descrição das Tarefas no OpenProject

As tarefas criadas no OpenProject através do bot contêm as seguintes informações:
- A descrição original fornecida pelo usuário
- As datas de início e término (quando fornecidas)
- Nome do solicitante da tarefa
- Nome do aprovador da tarefa

## Notas de Implementação Técnica

O bot implementa componentes personalizados de UI do Discord, incluindo menus Select, Modais e Botões para criar um fluxo intuitivo de solicitação de tarefas. Também gerencia paginação de resultados do OpenProject, já que o Discord tem um limite de 25 opções em menus de seleção.

Estimativas de tempo são convertidas de horas decimais (ex: 2.5) para formato de duração ISO8601 (PT2H30M) para compatibilidade com a API do OpenProject. As datas são convertidas do formato DD/MM/AAAA (interface do usuário) para o formato YYYY-MM-DD exigido pela API. A integração mantém uso eficiente da API através de cache e tratamento adequado de erros.