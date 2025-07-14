import aiohttp
import asyncio
import time
import json
from typing import Dict, List, Tuple, Optional, Any, Union
import logging

from config import OPENPROJECT_URL, OPENPROJECT_API_KEY, CACHE_DURATION
from utils.error_handler import OpenProjectError, logger
from utils.date_utils import format_duration

class OpenProjectRepository:
    """
    Repositório para interação com a API do OpenProject.
    Implementa padrão Repository para abstrair chamadas à API.
    """
    
    def __init__(self, base_url: str = OPENPROJECT_URL, api_key: str = OPENPROJECT_API_KEY):
        """
        Inicializa o repositório com as configurações da API.
        
        Args:
            base_url: URL base do OpenProject
            api_key: Chave de API do OpenProject
        """
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        self._projects_cache = []
        self._cache_timestamp = 0
        self._versions_cache = {}  # Cache para versões por projeto
        
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Realiza uma requisição HTTP para a API do OpenProject.
        
        Args:
            method: Método HTTP (GET, POST, etc)
            url: URL completa da requisição
            **kwargs: Argumentos adicionais para a requisição
            
        Returns:
            Dict: Resposta da API em formato JSON
            
        Raises:
            OpenProjectError: Se houver erro na requisição
        """
        if not self.base_url or not self.api_key:
            raise OpenProjectError("URL do OpenProject ou API Key não configurados.")
            
        auth = aiohttp.BasicAuth('apikey', self.api_key)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, 
                    url, 
                    headers=self.headers, 
                    auth=auth, 
                    **kwargs
                ) as response:
                    if response.status >= 400:
                        response_text = await response.text()
                        raise OpenProjectError(
                            f"Erro HTTP: {response.status}",
                            status_code=response.status,
                            api_message=response_text
                        )
                    
                    # Retorna resposta JSON
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão: {str(e)}")
            raise OpenProjectError(f"Erro de conexão: {str(e)}")
        except json.JSONDecodeError:
            raise OpenProjectError("Erro ao decodificar resposta JSON")
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")
            raise OpenProjectError(f"Erro inesperado: {str(e)}")
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """
        Obtém a lista de projetos ativos no OpenProject com cache.
        
        Returns:
            List[Dict]: Lista de projetos ativos
            
        Raises:
            OpenProjectError: Se houver erro na requisição
        """
        # Verifica se o cache é válido
        current_time = time.time()
        if self._projects_cache and current_time - self._cache_timestamp < CACHE_DURATION:
            return self._projects_cache
            
        # Se o cache não for válido, busca projetos na API
        url = f"{self.base_url}/api/v3/projects"
        
        try:
            projects_data = await self._make_request("GET", url)
            
            # Filtra apenas projetos ativos
            projects = []
            for project in projects_data.get('_embedded', {}).get('elements', []):
                if project.get('active', False):
                    projects.append({
                        'id': project.get('id'),
                        'name': project.get('name'),
                        'identifier': project.get('identifier'),
                        'href': project.get('_links', {}).get('self', {}).get('href', '')
                    })
            
            # Atualiza o cache
            self._projects_cache = projects
            self._cache_timestamp = current_time
            
            return projects
            
        except Exception as e:
            # Propaga exceção com mensagem mais detalhada
            raise OpenProjectError(f"Erro ao obter projetos: {str(e)}")
    
    async def get_project_versions(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista de versões disponíveis para um projeto.
        
        Args:
            project_id: ID do projeto
            
        Returns:
            Lista de versões
            
        Raises:
            OpenProjectError: Se houver erro na requisição
        """
        # Verificar o cache de versões
        cache_key = f"project_{project_id}_versions"
        current_time = time.time()
        
        if cache_key in self._versions_cache and current_time - self._versions_cache[cache_key].get('timestamp', 0) < CACHE_DURATION:
            return self._versions_cache[cache_key].get('versions', [])
        
        # Se não estiver em cache, buscar da API
        url = f"{self.base_url}/api/v3/projects/{project_id}/versions"
        
        try:
            versions_data = await self._make_request("GET", url)
            
            # Extrai as versões da resposta
            versions = []
            for version in versions_data.get('_embedded', {}).get('elements', []):
                versions.append({
                    'id': version.get('id'),
                    'name': version.get('name'),
                    'status': version.get('status'),
                    'description': version.get('description', {}).get('raw', ''),
                    'start_date': version.get('startDate'),
                    'due_date': version.get('endDate')
                })
            
            # Atualiza o cache
            self._versions_cache[cache_key] = {
                'versions': versions,
                'timestamp': current_time
            }
            
            return versions
            
        except Exception as e:
            logger.error(f"Erro ao obter versões do projeto {project_id}: {str(e)}")
            raise OpenProjectError(f"Erro ao obter versões: {str(e)}")
    
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma tarefa no OpenProject.
        
        Args:
            task_data: Dados da tarefa a ser criada
            
        Returns:
            Dict: Dados da tarefa criada e link para acesso
            
        Raises:
            OpenProjectError: Se houver erro na criação
        """
        # Validação de dados obrigatórios
        if not task_data.get("project_id"):
            raise OpenProjectError("ID do projeto não especificado.")
            
        if not task_data.get("nome_da_tarefa"):
            raise OpenProjectError("Nome da tarefa não especificado.")
            
        # Prepara descrição
        description = task_data.get('descricao', '')
        data_inicio = task_data.get('data_inicio', '')
        data_fim = task_data.get('data_fim', '')
        solicitante = task_data.get('solicitante_nome', 'Usuario')
        aprovador = task_data.get('aprovador_nome', 'Aprovador')
        version_name = task_data.get('version_name')
        
        description_text = f"{description}\n\n"
        if data_inicio:
            description_text += f"Data de início: {data_inicio}\n"
        if data_fim:
            description_text += f"Data de término: {data_fim}\n"
        if version_name:
            description_text += f"Versão: {version_name}\n"
        description_text += f"Solicitado por: {solicitante}\n"
        description_text += f"Aprovado por: {aprovador}"
        
        # Preparar o payload básico
        payload = {
            "subject": task_data["nome_da_tarefa"],
            "description": {
                "format": "markdown",
                "raw": description_text
            },
            "_links": {
                "project": {
                    "href": f"/api/v3/projects/{task_data['project_id']}"
                },
                "type": { "href": "/api/v3/types/1" }, 
                "status": { "href": "/api/v3/statuses/2" }  # Fixado para "Em andamento" (ID 2)
            }
        }
        
        # Adiciona versão se estiver presente (log para diagnóstico)
        if task_data.get('version_id'):
            version_id = task_data['version_id']
            logger.info(f"Adicionando versão ID {version_id} à tarefa {task_data['nome_da_tarefa']}")
            
            # Formato corrigido para a referência à versão
            payload["_links"]["version"] = {
                "href": f"/api/v3/versions/{version_id}"
            }
        else:
            logger.warning(f"Tarefa '{task_data['nome_da_tarefa']}' sendo criada sem versão")
        
        # Log do payload completo para depuração
        logger.debug(f"Payload para criação de tarefa: {json.dumps(payload, indent=2)}")
        
        # Adiciona datas se fornecidas
        if task_data.get('data_inicio_formatada'):
            payload["startDate"] = task_data['data_inicio_formatada']
        
        if task_data.get('data_fim_formatada'):
            payload["dueDate"] = task_data['data_fim_formatada']
        
        # Adiciona estimativa se fornecida
        if task_data.get('estimativa'):
            estimativa_formato_iso = format_duration(task_data['estimativa'])
            if estimativa_formato_iso:
                payload["estimatedTime"] = estimativa_formato_iso
        
        # Cria a tarefa
        create_url = f"{self.base_url}/api/v3/work_packages"
        
        try:
            # Log da URL para depuração
            logger.debug(f"Enviando requisição para: {create_url}")
            
            created_task = await self._make_request("POST", create_url, json=payload)
            task_id = created_task.get('id')
            
            # Verifica se a versão foi aplicada corretamente
            version_links = created_task.get('_links', {}).get('version', {})
            if version_links and task_data.get('version_id'):
                logger.info(f"Versão aplicada com sucesso à tarefa {task_id}")
            elif task_data.get('version_id'):
                logger.warning(f"Versão não aplicada à tarefa {task_id} embora tenha sido especificada")
            
            # Constrói URL para visualização
            result = {
                "task_id": task_id,
                "task_data": created_task
            }
            
            # Adiciona link para interface se tiver o identificador do projeto
            projects = await self.get_projects()
            for project in projects:
                if str(project.get('id')) == str(task_data['project_id']):
                    result["ui_link"] = f"{self.base_url}/projects/{project['identifier']}/work_packages/{task_id}/overview"
                    break
            
            # Adiciona link API como fallback
            if "ui_link" not in result:
                result["api_link"] = f"{self.base_url}{created_task.get('_links', {}).get('self', {}).get('href', '')}"
            
            return result
            
        except Exception as e:
            # Log detalhado do erro para depuração
            logger.error(f"Erro ao criar tarefa: {str(e)}")
            logger.error(f"Payload que causou o erro: {json.dumps(payload, indent=2)}")
            
            # Propaga exceção com mensagem mais detalhada
            raise OpenProjectError(f"Erro ao criar tarefa: {str(e)}")


class TaskService:
    """
    Serviço para gerenciamento de tarefas.
    Implementa lógica de negócios separada do repositório.
    """
    
    def __init__(self, repository: OpenProjectRepository = None):
        """
        Inicializa o serviço com o repositório.
        
        Args:
            repository: Repositório OpenProject para acesso a dados
        """
        self.repository = repository or OpenProjectRepository()
        self.pending_tasks = {}
    
    def add_pending_task(self, task_id: str, task_details: Dict[str, Any]) -> None:
        """
        Adiciona uma tarefa à lista de pendentes.
        
        Args:
            task_id: Identificador único da tarefa
            task_details: Detalhes da tarefa
        """
        self.pending_tasks[task_id] = task_details
    
    def get_pending_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém uma tarefa pendente pelo seu ID.
        
        Args:
            task_id: Identificador único da tarefa
            
        Returns:
            Dict ou None: Detalhes da tarefa ou None se não encontrada
        """
        return self.pending_tasks.get(task_id)
    
    def remove_pending_task(self, task_id: str) -> None:
        """
        Remove uma tarefa da lista de pendentes.
        
        Args:
            task_id: Identificador único da tarefa
        """
        if task_id in self.pending_tasks:
            del self.pending_tasks[task_id]
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """
        Obtém a lista de projetos ativos.
        
        Returns:
            List[Dict]: Lista de projetos
            
        Raises:
            OpenProjectError: Se houver erro na requisição
        """
        return await self.repository.get_projects()
    
    async def get_project_versions(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista de versões disponíveis para um projeto.
        
        Args:
            project_id: ID do projeto
            
        Returns:
            List[Dict]: Lista de versões
            
        Raises:
            OpenProjectError: Se houver erro na requisição
        """
        return await self.repository.get_project_versions(project_id)
    
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara e cria uma tarefa no OpenProject.
        
        Args:
            task_data: Dados da tarefa a ser criada
            
        Returns:
            Dict: Resultado da criação com links
            
        Raises:
            OpenProjectError: Se houver erro na criação
        """
        # Pré-processamento de dados
        from utils.date_utils import convert_date_format
        
        # Converte datas para o formato da API
        if task_data.get('data_inicio'):
            task_data['data_inicio_formatada'] = convert_date_format(task_data['data_inicio'])
            
        if task_data.get('data_fim'):
            task_data['data_fim_formatada'] = convert_date_format(task_data['data_fim'])
        
        # Cria a tarefa no OpenProject
        return await self.repository.create_task(task_data)


# Instância singleton para uso em todo o bot
task_service = TaskService()