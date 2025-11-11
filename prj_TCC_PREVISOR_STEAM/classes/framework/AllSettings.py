
import os
import logging
from typing import Any
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Settings:
    """
    Classe para gerenciar todas as configurações do sistema.
    """
    _var_dictSettings = {}

    @classmethod
    def bd_settings_default(cls):
        """
        Configurações padrão do banco de dados.
        Lê as configurações do arquivo .env ou usa valores padrão.
        """
        cls._var_strDBName: str = os.getenv("DB_NAME", "default_db")
        cls._var_strDBUser: str = os.getenv("DB_USER", "postgres")
        cls._var_strDBPassword: str = os.getenv("DB_PASSWORD", "postgres")
        cls._var_strDBHost: str = os.getenv("DB_HOST", "localhost")
        cls._var_strDBPort: str = os.getenv("DB_PORT", "5433")

    @classmethod
    def bd_settings_steam(cls):
        """
        Configurações do banco de dados Steam.
        Lê as configurações do arquivo .env ou usa valores padrão.
        """
        cls._var_strDBName: str = os.getenv("DB_NAME", "steam_data")
        cls._var_strDBUser: str = os.getenv("DB_USER", "postgres")
        cls._var_strDBPassword: str = os.getenv("DB_PASSWORD", "postgres")
        cls._var_strDBHost: str = os.getenv("DB_HOST", "localhost")
        cls._var_strDBPort: str = os.getenv("DB_PORT", "5433")

    @classmethod 
    def bd_settings_previsao(cls):
        """
        Configurações do banco de dados de previsão.
        Lê as configurações do arquivo .env ou usa valores padrão.
        """
        cls._var_strDBName: str = os.getenv("DB_NAME", "previsao_steam")
        cls._var_strDBUser: str = os.getenv("DB_USER", "postgres")
        cls._var_strDBPassword: str = os.getenv("DB_PASSWORD", "postgres")
        cls._var_strDBHost: str = os.getenv("DB_HOST", "localhost")
        cls._var_strDBPort: str = os.getenv("DB_PORT", "5433")
    
    @classmethod
    def steam_api_details(cls) -> dict:
        """
        Configurações da API de Detalhes da Steam.

        Retorna:
        - dict: Configurações da API de Detalhes da Steam.
        """
        var_intBatchesSize: int = int(os.getenv("STEAM_BATCH_SIZE_DETAILS", "200"))
        var_intDelayBetweenBatches: int = int(os.getenv("STEAM_DELAY_BETWEEN_BATCHES_DETAILS", "120"))
        var_intAsyncConcurrency: int = int(os.getenv("STEAM_ASYNC_CONCURRENCY_DETAILS", "1"))
        return {
            "BatchSize": var_intBatchesSize,
            "Delay": var_intDelayBetweenBatches,
            "Concurrency": var_intAsyncConcurrency
        }

    @classmethod
    def steam_api_itad(cls) -> dict:
        """
        Configurações da API de ITAD da Steam.

        Retorna:
        - dict: Configurações da API de ITAD da Steam.
        """
        var_intBatchesSize: int = int(os.getenv("STEAM_BATCH_SIZE_ITAD", "200"))
        var_intDelayBetweenBatches: int = int(os.getenv("STEAM_DELAY_BETWEEN_BATCHES_ITAD", "120"))
        var_intAsyncConcurrency: int = int(os.getenv("STEAM_ASYNC_CONCURRENCY_ITAD", "1"))
        return {
            "BatchSize": var_intBatchesSize,
            "Delay": var_intDelayBetweenBatches,
            "Concurrency": var_intAsyncConcurrency
        }
    
    @classmethod
    def steam_api_reviews(cls) -> dict:
        """
        Configurações da API de Reviews da Steam.

        Retorna:
        - dict: Configurações da API de Reviews da Steam.
        """
        var_intBatchesSize: int = int(os.getenv("STEAM_BATCH_SIZE_REVIEWS", "500"))
        var_intDelayBetweenBatches: int = int(os.getenv("STEAM_DELAY_BETWEEN_BATCHES_REVIEWS", "60"))
        var_intAsyncConcurrency: int = int(os.getenv("STEAM_ASYNC_CONCURRENCY_REVIEWS", "3"))
        return {
            "BatchSize": var_intBatchesSize,
            "Delay": var_intDelayBetweenBatches,
            "Concurrency": var_intAsyncConcurrency
        }

    @classmethod
    def steam_api_settings(cls):
        """
        Configurações para a Steam API.
        """
        cls._var_strItadApiKey: str | None = os.getenv("ITAD_API_KEY")
        cls._var_intCacheAppListMaxAgeDays: int = 30
        cls._var_strAppListPath: str = "resources/dados/steam_applist.json"
        cls._var_listApp: list[dict[str, Any]] = []
        cls._var_boolAppListLoaded = False
        cls._var_dictConfigAPI = {
            "detalhes": cls.steam_api_details(),
            "reviews": cls.steam_api_reviews(),
            "itad": cls.steam_api_itad()
        }

    @classmethod
    def configure_logging(cls):
        """
        Configura o sistema de logging do projeto.
        """
        # Obtém o nível de logging da variável de ambiente (padrão: INFO)
        var_strLogLevel = os.getenv("LOG_LEVEL", "INFO").upper()
        var_strLogLevelSupabase = os.getenv("LOG_LEVEL_SUPABASE", "WARNING").upper()
        var_intLogLevel = getattr(logging, var_strLogLevel, logging.INFO)
        var_intLogLevelSupabase = getattr(logging, var_strLogLevelSupabase, logging.WARNING)
        var_logLogLevelSupabase = logging.WARNING

        # Cria o diretório de logs se não existir
        var_strLogDir = "resources/logs"
        os.makedirs(var_strLogDir, exist_ok=True)
        
        # Configuração básica do logging
        logging.basicConfig(
            level=var_intLogLevel,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),  # Output para console
                # Opcional: adicionar FileHandler para salvar logs em arquivo
                logging.FileHandler(os.path.join(var_strLogDir, 'app.log'), encoding='utf-8')
            ]
        )
        
        # Define o nível de logging para bibliotecas externas (evitar spam)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        # Desabilita logs HTTP do httpx (usado pelo Supabase)
        logging.getLogger("httpx").setLevel(var_logLogLevelSupabase)
        logging.getLogger("httpcore").setLevel(var_logLogLevelSupabase)

        cls._var_dictSettings["log_level"] = var_strLogLevel

    @classmethod
    def build(cls):
        """
        Constrói as configurações iniciais do sistema.
        """
        load_dotenv()
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
