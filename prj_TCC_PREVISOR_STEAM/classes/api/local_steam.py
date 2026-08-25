from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steamspy_api import SteamSpyClient

from typing import Any
from datetime import datetime, timedelta
from time import sleep
import json
import logging
import os
import requests

logger = logging.getLogger("steam.local")

CON_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

# STEAM_APP_LIST_URL API DESCONTINUADA PELA VALVE (404 desde Nov/2024)
STEAM_APP_LIST_URL_DEPRECATED = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"

class LocalClient:
    """
    Cliente para interagir com a Steam API utilizando dados locais.
    """

    # ------------------- App List -------------------
    @classmethod
    def load_app_list(cls, arg_boolForce: bool = False) -> list[dict[str, Any]]:
        """
        Carrega a lista de aplicativos da Steam, utilizando cache local se disponível.
        
        Parâmetros:
        - arg_boolForce (bool): Se True, força o recarregamento da lista
        
        Retorna:
        - Settings._var_listApp (list): A lista de aplicativos da Steam.
        """
        # Verifica se a lista já foi carregada
        if Settings._var_boolAppListLoaded and not arg_boolForce:
            return Settings._var_listApp
        
        # Tenta carregar do cache local
        var_strPath = Settings._var_strAppListPath
        if not arg_boolForce and os.path.exists(var_strPath):
            try:
                # Verifica se o cache é recente
                var_dateMTime = datetime.fromtimestamp(os.path.getmtime(var_strPath))
                if datetime.now() - var_dateMTime < timedelta(days=Settings._var_intCacheAppListMaxAgeDays):
                    # Se for recente, carrega do arquivo
                    Settings._var_listApp = json.loads(open(var_strPath, "r", encoding="utf-8").read())
                    Settings._var_boolAppListLoaded = True
                    return Settings._var_listApp
            except Exception:
                pass

        # Se chegou aqui, precisa buscar da API ou do JSON local
        try:
            var_listData = cls.find_app_list()
            
            # Se retornou lista vazia ou False, tenta carregar do JSON local
            if not var_listData:
                logger.warning("API Steam não retornou dados. Tentando por SteamSpy...")
                var_listDataNovos = SteamSpyClient._fetch_from_steamspy()  # Retorna APENAS novos + modificados

                if not var_listDataNovos:
                    logger.warning("API SteamSpy não retornou dados. Tentando arquivo local...")
                    var_listData = cls._load_from_local_json()
                else:
                    var_listData = cls.mesclar_dados(var_listDataNovos)  # Mescla novos dados do SteamSpy com cache existente
                    
            
            # Se conseguiu dados, salva no cache local
            if var_listData:
                os.makedirs(os.path.dirname(var_strPath), exist_ok=True)
                with open(var_strPath, "w", encoding="utf-8") as f:
                    json.dump(var_listData, f)
                Settings._var_listApp = var_listData
                Settings._var_boolAppListLoaded = True
                logger.info(f"Cache atualizado: {len(var_listData):,} jogos salvos em {var_strPath}")
                return var_listData
            else:
                Settings._var_listApp = []
                return Settings._var_listApp

        except Exception as e:
            logger.error(f"Erro ao buscar da API: {e}")
            logger.info("Tentando carregar do arquivo local...")
            var_listData = cls._load_from_local_json()
            if var_listData:
                Settings._var_listApp = var_listData
                Settings._var_boolAppListLoaded = True
                return var_listData
            Settings._var_listApp = []
            return Settings._var_listApp

    @classmethod
    def find_app_list(cls) -> list[dict[str, Any]]:
        """
        Executa a requisição para obter a lista de aplicativos da Steam diretamente da API.
        Implementa retry automático com backoff exponencial em caso de falha.

        Parâmetros:

        Retorna:
        - var_listData (list): A lista de aplicativos da Steam.
        """
        var_intMaxTentativas = 5
        var_intDelayBase = 5  # segundos
        
        for var_intTentativa in range(var_intMaxTentativas):
            try:
                logger.debug(f"Tentativa {var_intTentativa + 1}/{var_intMaxTentativas} - Buscando lista de aplicativos da Steam...")
                
                # Faz a requisição para a Steam (API descontinuada desde Nov/2024)
                var_respResponse = requests.get(
                    STEAM_APP_LIST_URL_DEPRECATED, 
                    headers=CON_DEFAULT_HEADERS, 
                    timeout=60
                )

                # Verifica se a resposta foi bem-sucedida
                var_respResponse.raise_for_status()

                # Processa os dados recebidos
                var_listData = var_respResponse.json().get("applist", {}).get("apps", [])
                Settings._var_listApp = var_listData
                logger.info(f"Lista de aplicativos carregada com sucesso! ({len(var_listData)} jogos)")
                return var_listData
            
            except requests.exceptions.HTTPError as e:
                # Erros HTTP específicos (503, 500, etc.)
                var_intStatusCode = e.response.status_code if hasattr(e, 'response') else 0
                
                if var_intStatusCode == 404:
                    logger.warning("API Steam GetAppList retornou 404 (endpoint descontinuado)")
                    logger.warning("Tentando por SteamSpy...")
                    var_listDataNovos = SteamSpyClient._fetch_from_steamspy()  # Retorna APENAS novos + modificados

                    if not var_listDataNovos:
                        logger.warning("API SteamSpy não retornou dados. Tentando arquivo local...")
                        logger.info("Usando arquivo JSON local como fallback...")
                        return cls._load_from_local_json()

                    # Mescla o delta com o cache; senão load_app_list() sobrescreve o arquivo.
                    return cls.mesclar_dados(var_listDataNovos)
                
                elif var_intStatusCode == 503:
                    logger.warning("Serviço Steam temporariamente indisponível (503 Service Unavailable)")
                    return False
                elif var_intStatusCode >= 500:
                    logger.warning(f"Erro interno do servidor Steam ({var_intStatusCode})")
                    return False
                else:
                    logger.error(f"Erro HTTP ao buscar lista da Steam: {e}")
                    raise  Exception(f"Erro HTTP não recuperável ao buscar lista da Steam: {e}")  # Erro não recuperável (4xx, etc.)
            
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout ao buscar lista da Steam (tentativa {var_intTentativa + 1}/{var_intMaxTentativas})")
                
                if var_intTentativa < var_intMaxTentativas - 1:
                    var_intDelay = var_intDelayBase * (2 ** var_intTentativa)
                    logger.info(f"Aguardando {var_intDelay}s antes da próxima tentativa...")
                    sleep(var_intDelay)
                else:
                    raise Exception(f"Timeout após {var_intMaxTentativas} tentativas ao buscar lista da Steam")
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Erro de conexão com a API Steam (tentativa {var_intTentativa + 1}/{var_intMaxTentativas})")
                
                if var_intTentativa < var_intMaxTentativas - 1:
                    var_intDelay = var_intDelayBase * (2 ** var_intTentativa)
                    logger.info(f"Aguardando {var_intDelay}s antes da próxima tentativa...")
                    sleep(var_intDelay)
                else:
                    raise Exception(f"Erro de conexão após {var_intMaxTentativas} tentativas: {e}")
            
            except Exception as e:
                logger.error(f"Erro inesperado ao buscar a lista de aplicativos da Steam: {e}")
                raise Exception(f"Erro ao buscar a lista de aplicativos da Steam: {e}")
        
        # Fallback se todas as tentativas falharem
        raise Exception(f"Falha ao buscar lista da Steam após {var_intMaxTentativas} tentativas")

    @classmethod
    def _load_from_local_json(cls) -> list[dict[str, Any]]:
        """
        Carrega a lista de aplicativos do arquivo JSON local (steam_applist.json).
        Usado como fallback quando a API Steam GetAppList está indisponível.
        
        Retorna:
        - var_listData (list): A lista de aplicativos da Steam do arquivo local.
        """
        try:
            # Determina o caminho do arquivo JSON local
            var_strScriptDir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            var_strJsonPath = os.path.join(var_strScriptDir, "resources", "dados", "steam_applist.json")
            
            if not os.path.exists(var_strJsonPath):
                logger.error(f"Arquivo steam_applist.json não encontrado: {var_strJsonPath}")
                logger.error("A API Steam foi descontinuada e o arquivo de fallback não existe.")
                return []
            
            # Lê o arquivo JSON local
            logger.info(f"Carregando do arquivo local: {var_strJsonPath}")
            with open(var_strJsonPath, "r", encoding="utf-8") as f:
                var_listData = json.load(f)
            
            # Obtém data de modificação do arquivo
            var_dateMTime = datetime.fromtimestamp(os.path.getmtime(var_strJsonPath))
            var_intDaysOld = (datetime.now() - var_dateMTime).days
            
            Settings._var_listApp = var_listData
            logger.info(f"Lista carregada do arquivo local! ({len(var_listData):,} apps)")
            logger.info(f"Dados com {var_intDaysOld} dias (última atualização: {var_dateMTime.strftime('%Y-%m-%d')})")
            
            return var_listData
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do steam_applist.json: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar steam_applist.json: {e}")
            return []
        
    @classmethod
    def mesclar_dados(cls, arg_listDataNovos:list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Mescla os dados novos obtidos do SteamSpy com o cache existente, atualizando apenas os jogos que tiveram mudanças.
         - Novos jogos são adicionados
         - Jogos existentes com mudanças (ex: nome) são atualizados
         - Jogos sem mudanças permanecem inalterados

        Parâmetros:
        - arg_listDataNovos (list): Lista de jogos novos/modificados obtidos do SteamSpy

        Retorna:
        - var_listDataMesclada (list): Lista final mesclada de jogos para salvar no cache
        """
        logger.info("Mesclando dados do SteamSpy com cache existente...")
        
        # Determina caminho do cache
        var_strScriptDir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        var_strCachePath = os.path.join(var_strScriptDir, "resources", "dados", "steam_applist.json")
        
        # Carrega cache existente para mesclar
        var_dictCacheExistente = {}
        if os.path.exists(var_strCachePath):
            try:
                with open(var_strCachePath, "r", encoding="utf-8") as f:
                    var_listCacheExistente = json.load(f)
                    var_dictCacheExistente = {
                        jogo["appid"]: jogo 
                        for jogo in var_listCacheExistente 
                        if isinstance(jogo, dict) and "appid" in jogo
                    }
                logger.info(f"Cache existente: {len(var_dictCacheExistente):,} jogos")
            except Exception as e:
                logger.warning(f"Erro ao carregar cache para mesclar: {e}")
        
        # Atualiza/adiciona jogos novos e modificados
        var_intNovosAdicionados = 0
        var_intModificados = 0
        for jogo in arg_listDataNovos:
            var_intAppid = jogo.get("appid")
            if var_intAppid:
                if var_intAppid in var_dictCacheExistente:
                    # Verifica se nome mudou
                    if var_dictCacheExistente[var_intAppid].get("name") != jogo.get("name"):
                        var_intModificados += 1
                else:
                    var_intNovosAdicionados += 1
                var_dictCacheExistente[var_intAppid] = jogo
        
        # Converte dicionário de volta para lista
        var_listDataMesclada = list(var_dictCacheExistente.values())
        
        logger.info(f"Mesclagem concluída: {len(var_listDataMesclada):,} jogos total")
        logger.info(f"  - Novos adicionados: {var_intNovosAdicionados:,}")
        logger.info(f"  - Modificados: {var_intModificados:,}")
        logger.info(f"  - Mantidos: {len(var_listDataMesclada) - var_intNovosAdicionados - var_intModificados:,}")

        return var_listDataMesclada