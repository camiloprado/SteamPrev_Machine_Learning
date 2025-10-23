
import os
from typing import Any

class Settings:
    """
    Classe para gerenciar todas as configurações do sistema.
    """
    _var_dictSettings = {}

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
    def build(cls):
        """
        Constrói as configurações iniciais do sistema.
        """
        cls.steam_api_settings()
        
        cls._var_dictSettings["max_tentativas"] = 3

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
