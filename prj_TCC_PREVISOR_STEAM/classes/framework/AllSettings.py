
import os
import logging
from typing import Any

class Settings:
    """
    Classe para gerenciar todas as configurações do sistema.
    """
    _var_dictSettings = {}

    @classmethod
    def bd_settings_default(cls):
        """
        Configurações padrão do banco de dados.
        """
        cls._var_strDBName: str = "default_db"
        cls._var_strDBUser: str = "postgres"
        cls._var_strDBPassword: str = "postgres"
        cls._var_strDBHost: str = "localhost"
        cls._var_strDBPort: str = "5433"

    @classmethod
    def bd_settings_steam(cls):
        """
        Configurações do banco de dados Steam.
        """
        cls._var_strDBName: str = "steam_data"
        cls._var_strDBUser: str = "postgres"
        cls._var_strDBPassword: str = "postgres"
        cls._var_strDBHost: str = "localhost"
        cls._var_strDBPort: str = "5433"

    @classmethod 
    def bd_settings_previsao(cls):
        """
        Configurações do banco de dados de previsão.
        """
        cls._var_strDBName: str = "previsao_steam"
        cls._var_strDBUser: str = "postgres"
        cls._var_strDBPassword: str = "postgres"
        cls._var_strDBHost: str = "localhost"
        cls._var_strDBPort: str = "5433"
        
    @classmethod
    def steam_api_settings(cls):
        """
        Configurações para a Steam API.
        """
        cls._var_strItadApiKey: str | None = os.getenv("ITAD_API_KEY")
        # Permite ajuste dinâmico via env para evitar throttling em E2E local (ex.: STEAM_ASYNC_CONCURRENCY=2)
        cls._var_intAsyncConcurrency: int = int(os.getenv("STEAM_ASYNC_CONCURRENCY", "5"))
        cls._var_intCacheAppListMaxAgeDays: int = 30
        cls._var_strAppListPath: str = "resources/dados/steam_applist.json"
        cls._var_listApp: list[dict[str, Any]] = []
        cls._var_boolAppListLoaded = False

    @classmethod
    def configure_logging(cls):
        """
        Configura o sistema de logging do projeto.
        """
        # Obtém o nível de logging da variável de ambiente (padrão: INFO)
        var_strLogLevel = os.getenv("LOG_LEVEL", "INFO").upper()
        var_intLogLevel = getattr(logging, var_strLogLevel, logging.INFO)
        
        # Configuração básica do logging
        logging.basicConfig(
            level=var_intLogLevel,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),  # Output para console
                # Opcional: adicionar FileHandler para salvar logs em arquivo
                # logging.FileHandler('resources/logs/app.log', encoding='utf-8')
            ]
        )
        
        # Define o nível de logging para bibliotecas externas (evitar spam)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        cls._var_dictSettings["log_level"] = var_strLogLevel

    @classmethod
    def build(cls):
        """
        Constrói as configurações iniciais do sistema.
        """
        cls.configure_logging()  # Configura o logging primeiro
        cls.steam_api_settings()
        cls.bd_settings_default()
        cls.bd_settings_previsao()
        cls._var_dictSettings["max_tentativas"] = 3
        cls._var_dictSettings["steam_itad_api_key"] = cls._var_strItadApiKey
        cls._var_dictSettings["path_data_app_details"] = "resources/dados/steam_app_details.json"
        cls._var_dictSettings["db_name"] = cls._var_strDBName
        cls._var_dictSettings["db_user"] = cls._var_strDBUser
        cls._var_dictSettings["db_password"] = cls._var_strDBPassword
        cls._var_dictSettings["db_host"] = cls._var_strDBHost
        cls._var_dictSettings["db_port"] = cls._var_strDBPort
        cls._var_dictSettings["dias_para_atualizacao"] = 90
        cls._var_dictSettings["partes_por_serie"] = 200

    @classmethod
    def remove_setting(cls, arg_strKey: str):
        """
        Remove uma configuração do dicionário de configurações.

        Parâmetros:
        - arg_strKey (str): A chave da configuração.

        Retorna:
        - None
        """
        if arg_strKey in cls._var_dictSettings:
            del cls._var_dictSettings[arg_strKey]

    @classmethod
    def list_settings(cls):
        """
        Lista todas as configurações do dicionário de configurações.

        Retorna:
        - Um iterável com todas as chaves e valores das configurações.
        """
        return cls._var_dictSettings.items()

Settings.build()
