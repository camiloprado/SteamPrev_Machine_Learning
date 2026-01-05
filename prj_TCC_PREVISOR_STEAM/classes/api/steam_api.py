from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

from typing import Any, Sequence
from datetime import datetime, timedelta, timezone
from time import sleep
import asyncio, random, json, logging, os, re, aiohttp, requests, traceback

logger = logging.getLogger(__name__)

CON_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

# STEAM_APP_LIST_URL API DESCONTINUADA PELA VALVE (404 desde Nov/2024)
# Usando arquivo JSON local steam_applist.json com dados históricos
STEAM_APP_LIST_URL_DEPRECATED = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
STEAM_APP_LIST_LOCAL_FALLBACK = "prj_TCC_PREVISOR_STEAM/resources/dados/steam_applist.json"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
ITAD_LOOKUP_URL = "https://api.isthereanydeal.com/lookup/id/title/v1"
ITAD_HISTORY_URL = "https://api.isthereanydeal.com/games/history/v2"
ITAD_LOOKUP_IDS_URL = "https://api.isthereanydeal.com/games/lookup/v1"


class SteamClient:
    """
    Cliente para interagir com a Steam API.
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
                logger.warning("API Steam não retornou dados. Tentando arquivo local...")
                var_listData = cls._load_from_local_json()
            
            # Se conseguiu dados, salva no cache local
            if var_listData:
                os.makedirs(os.path.dirname(var_strPath), exist_ok=True)
                with open(var_strPath, "w", encoding="utf-8") as f:
                    json.dump(var_listData, f)
                Settings._var_listApp = var_listData
                Settings._var_boolAppListLoaded = True
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
                logger.info(f"Tentativa {var_intTentativa + 1}/{var_intMaxTentativas} - Buscando lista de aplicativos da Steam...")
                
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
                    logger.warning(f"API Steam GetAppList retornou 404 (endpoint descontinuado)")
                    logger.info(f"Usando arquivo JSON local como fallback...")
                    return cls._load_from_local_json()
                elif var_intStatusCode == 503:
                    logger.warning(f"Serviço Steam temporariamente indisponível (503 Service Unavailable)")
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

    # ------------------- Find appid -------------------
    @classmethod
    def find_appid(cls, arg_strName: str) -> int | None:
        """
        Encontra o appid de um jogo pelo seu nome.
        
        Parâmetros:
        - arg_strName (str): O nome do jogo.
        
        Retorna:
        - var_intAppid (int | None): O appid do jogo ou None se não encontrado.
        """
        var_listApps = cls.load_app_list()
        var_strAlvo = arg_strName.strip().lower()
        for var_dictApp in var_listApps:
            if var_dictApp.get("name", "").lower() == var_strAlvo:
                var_intAppid = var_dictApp.get("appid")
                return var_intAppid
        var_strPadrao = re.sub(r"[^a-z0-9]", "", var_strAlvo)
        for var_dictApp in var_listApps:
            var_strNome = var_dictApp.get("name")
            if isinstance(var_strNome, str) and re.sub(r"[^a-z0-9]", "", var_strNome.lower()) == var_strPadrao:
                var_intAppid = var_dictApp.get("appid")
                return var_intAppid
        return None

    # ------------------- Steam details -------------------
    @classmethod
    def fetch_details(cls, arg_intAppid: int) -> dict:
        """
        Busca os detalhes de um jogo na Steam pelo seu appid.

        Parâmetros:
        - arg_intAppid (int): O appid do jogo.

        Retorna:
        - var_dictDetails (dict): Um dicionário com os detalhes do jogo ou um dicionário vazio se não encontrado.
        """
        try:
            var_dictParams = {"appids": arg_intAppid, "l": "brazilian"}
            var_respResponse = requests.get(
                STEAM_DETAILS_URL,
                params=var_dictParams,
                headers=CON_DEFAULT_HEADERS,
                timeout=30,
            )
            var_respResponse.raise_for_status()
            var_dictData = var_respResponse.json()
            if var_dictData and str(arg_intAppid) in var_dictData and var_dictData[str(arg_intAppid)]["success"]:
                var_dictDetails = var_dictData[str(arg_intAppid)]["data"]
                return var_dictDetails
        except Exception as e:
            pass
        return {}

    # ------------------- Async bulk details com batches -------------------
    @classmethod
    async def fetch_details_bulk_batched(cls, arg_seqAppids: Sequence[int]) -> None:
        """
        Busca os detalhes de múltiplos jogos na Steam de forma assíncrona, processando em batches.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.

        Retorna:
        - var_dictAllResults (dict): Um dicionário com todos os detalhes dos jogos.
        """
        var_dictConfigAPI = Settings.steam_api_details()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        var_intDelay = var_dictConfigAPI.get("Delay", 120)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTentativaMaxima = var_dictConfigAPI.get("max_tentativas", 3)
        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        logger.info(f"")
        logger.info(f"=== PROCESSAMENTO EM BATCHES ===")
        logger.info(f"Total de itens: {var_intTotalItems:,}")
        logger.info(f"Tamanho do batch: {var_intBatchSize:,}")
        logger.info(f"Total de batches: {var_intTotalBatches}")
        logger.info(f"Delay entre batches: {var_intDelay}s")
        logger.info(f"Concorrência por batch: {var_intAsyncConcurrency}")
        logger.info(f"Tempo Estimado para conclusão total do Batch: {(var_intTotalBatches * var_intDelay)/60:.1f} minutos")
        logger.info(f"================================\n")
        
        var_dictAllResults = {}
        
        for var_intBatchNum in range(var_intTotalBatches):
            var_intStart = var_intBatchNum * var_intBatchSize
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]
            
            logger.info(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")
            
            # Processa o batch atual
            var_listBatchResults = await cls.fetch_details_bulk(var_listBatch)
            var_listDetails = []
            for var_dictResult in var_listBatchResults:
                # Valida se o resultado não é None ou exceção
                if var_dictResult is None or isinstance(var_dictResult, Exception):
                    continue
                
                if not isinstance(var_dictResult, dict):
                    logger.warning(f"Resultado inválido (não é dict): {type(var_dictResult)}")
                    continue
                
                var_dictResult = {
                    "appid": var_dictResult.get("APPID"),
                    "detalhes": var_dictResult.get("data"),
                    "ultima_atualizacao": datetime.utcnow().isoformat(sep=' ', timespec='microseconds')
                }
                var_listDetails.append(var_dictResult)

            # Insere no PostgreSQL (Docker) em vez de Supabase
            if var_listDetails:
                PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=var_listDetails)
                logger.info(f"Dados de detalhes inseridos com sucesso no PostgreSQL ({len(var_listDetails)} registros).")
            else:
                logger.warning("Nenhum dado válido para inserir neste batch.")

            # Aguarda entre batches (exceto no último)
            if var_intBatchNum < var_intTotalBatches - 1:
                logger.info(f"Aguardando {var_intDelay}s antes do próximo batch...\n")
                await asyncio.sleep(var_intDelay)

        logger.info(f"===========PROCESSAMENTO COMPLETO! (Detalhes)==========")
        logger.info(f"Total processado: {len(var_listDetails):,} sucessos de {var_intTotalItems:,} itens ({len(var_dictAllResults)/var_intTotalItems:.2%})")

    # ------------------- Async bulk details -------------------
    @classmethod
    async def fetch_details_bulk(cls, arg_seqAppids: Sequence[int]) -> list[dict]:
        """
        Busca os detalhes de múltiplos jogos na Steam de forma assíncrona.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.

        Retorna:
        - var_listResults (list[dict]): Uma lista de dicionários com os detalhes dos jogos.
        """
        try:
            var_dictConfigAPI = Settings.steam_api_details()
            var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
            # Controle de concorrência
            var_semSemaphore = asyncio.Semaphore(var_intAsyncConcurrency)

            # Contadores de erro
            var_intErrosHTTP = 0
            var_intErrosForbidden = 0
            var_intErrosTooManyRequests = 0
            var_intErrosTimeout = 0
            var_intErrosOutros = 0
            var_intAusentes = 0
            
            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> dict | str | None:
                """
                Worker assíncrono para buscar detalhes de um único appid.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.
                
                Retorna:
                - var_dictDetails (dict | None): Um dicionário com os detalhes do jogo ou None se não encontrado.
                """
                nonlocal var_intErrosHTTP, var_intErrosForbidden, var_intErrosTooManyRequests, var_intErrosTimeout, var_intErrosOutros, var_intAusentes
                async with var_semSemaphore:
                    # Pequena espera para evitar throttling
                    await asyncio.sleep(random.random() * 0.3)
                    var_dictParams = {"appids": arg_intAppid, "l": "brazilian"}
                    try:
                        # Faz a requisição assíncrona
                        async with arg_clientSession.get(STEAM_DETAILS_URL, params=var_dictParams, timeout=30) as var_respResponse:
                            var_respResponse.raise_for_status()
                            # Processa os dados recebidos
                            var_dictData = await var_respResponse.json()
                            if var_dictData and var_dictData.get(str(arg_intAppid), {}).get("success"):
                                var_dictDetails = var_dictData[str(arg_intAppid)]
                                var_dictDetails["APPID"] = arg_intAppid
                                return var_dictDetails
                            elif var_dictData and var_dictData.get(str(arg_intAppid), {}).get("success") is False:
                                # Caso não retorne dados válidos (success=False ou dados ausentes)
                                var_intAusentes += 1
                                var_dictDetails = var_dictData[str(arg_intAppid)]
                                var_dictDetails["data"] = "AUSENTE"
                                var_dictDetails["APPID"] = arg_intAppid
                                return var_dictDetails
                            else:
                                var_intAusentes += 1
                                return None
                    except aiohttp.ClientError as e_http:
                        # Captura erros específicos de HTTP (conexão, timeout, status).
                        var_intErrosHTTP += 1
                        if hasattr(e_http, 'status'):
                            if e_http.status == 403:
                                var_intErrosForbidden += 1
                            elif e_http.status == 429:
                                var_intErrosTooManyRequests += 1
                            else:
                                logger.warning(f"AppID {arg_intAppid}: Erro HTTP status {e_http.status}")
                        return None
                    except asyncio.TimeoutError:
                        # Captura erro de timeout.
                        var_intErrosTimeout += 1
                        return None
                    except Exception:
                        # Captura outros erros não classificados.
                        var_intErrosOutros += 1
                        return None

            # Executa os workers assíncronos
            async with aiohttp.ClientSession(headers=CON_DEFAULT_HEADERS) as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, var_intAppid)) for var_intAppid in arg_seqAppids]
                logger.info(f"Iniciando busca de 'DETALHES' assíncrona para {len(var_listTasks)} AppIDs com concorrência {var_intAsyncConcurrency}...")
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.info("Busca assíncrona concluída.")

            # Conta None's e filtra a lista de forma segura
            var_intContNones = sum(1 for item in var_listOut if item is None)
            var_listOut = [item for item in var_listOut if item is not None]
            
            var_intFalha = sum(1 for item in var_listOut if item.get("data") == "AUSENTE") + var_intContNones
            logger.info(f"--- Busca concluída: ---")
            logger.info(f"{len(var_listOut)-var_intFalha} sucesso(s) ({(len(var_listOut)-var_intFalha)/(len(arg_seqAppids)):.2%}),")
            logger.info(f"{var_intFalha} falha(s) ({var_intFalha/len(arg_seqAppids):.2%}).")
            logger.info(f"--- Detalhamento dos erros: ---")
            logger.info(f"* HTTP: {var_intErrosHTTP} (403 Forbidden: {var_intErrosForbidden}, 429 Too Many Requests: {var_intErrosTooManyRequests})")
            logger.info(f"* Timeout: {var_intErrosTimeout}")
            logger.info(f"* Ausentes: {var_intAusentes}")
            logger.info(f"* Outros: {var_intErrosOutros}")
            return var_listOut
        
        except AttributeError as e:
            var_strTraceback = traceback.format_exc()
            logger.critical(f"Falha crítica ao buscar detalhes em bulk: {e}\n{var_strTraceback}")
            raise RuntimeError(f"Falha ao buscar detalhes em bulk: {e}")
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar detalhes em bulk: {e}")
            raise RuntimeError(f"Falha ao buscar detalhes em bulk: {e}")
        
    # ------------------- Async reviews summary com batches -------------------
    @classmethod
    async def fetch_reviews_summary_batched(cls, arg_seqAppids: Sequence[int]) -> dict[int, dict]:
        """
        Busca o resumo de reviews de múltiplos jogos na Steam de forma assíncrona, processando em batches.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.
        
        Retorna:
        - var_dictAllResults (dict): Um dicionário mapeando appids para seus resumos de reviews.
        """
        var_dictConfigAPI = Settings.steam_api_reviews()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        var_intDelay = var_dictConfigAPI.get("Delay", 120)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        var_intTentativaMaxima = var_dictConfigAPI.get("max_tentativas", 3)

        logger.info(f"")
        logger.info(f"=== PROCESSAMENTO EM BATCHES (REVIEWS) ===")
        logger.info(f"Total de itens: {var_intTotalItems:,}")
        logger.info(f"Tamanho do batch: {var_intBatchSize:,}")
        logger.info(f"Total de batches: {var_intTotalBatches}")
        logger.info(f"Delay entre batches: {var_intDelay}s")
        logger.info(f"Concorrência por batch: {var_intAsyncConcurrency}")
        logger.info(f"Tempo Estimado para conclusão total do Batch: {(var_intTotalBatches * var_intDelay)/60:.1f} minutos")
        logger.info(f"==========================================\n")
        
        for var_intBatchNum in range(var_intTotalBatches):
            var_intStart = var_intBatchNum * var_intBatchSize
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]

            logger.info(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")

            # Processa o batch atual
            var_listBatchResults = await cls.fetch_reviews_summary(var_listBatch)
            
            var_listReviews = []
            for var_dictResult in var_listBatchResults:
                # Valida se o resultado não é None ou exceção
                if var_dictResult is None or isinstance(var_dictResult, Exception):
                    continue
                
                if not isinstance(var_dictResult, dict):
                    logger.warning(f"Resultado inválido (não é dict): {type(var_dictResult)}")
                    continue
                
                var_dictResult = {
                    "appid": var_dictResult.get("APPID"),
                    "reviews": var_dictResult.get("data"),
                    "ultima_atualizacao": datetime.utcnow().isoformat(sep=' ', timespec='microseconds')
                }
                var_listReviews.append(var_dictResult)

            # Insere no PostgreSQL (Docker) em vez de Supabase
            if var_listReviews:
                PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=var_listReviews)
                logger.info(f"Dados de reviews inseridos com sucesso no PostgreSQL ({len(var_listReviews)} registros).")
            else:
                logger.warning("Nenhum dado válido para inserir neste batch.")

            # Aguarda entre batches (exceto no último)
            if var_intBatchNum < var_intTotalBatches - 1:
                logger.info(f"Aguardando {var_intDelay}s antes do próximo batch...\n")
                await asyncio.sleep(var_intDelay)

        logger.info(f"===========PROCESSAMENTO COMPLETO! (Reviews)==========")
        logger.info(f"Total processado: {var_intTotalItems:,} itens.")
        return None
    
    # ------------------- Async reviews summary -------------------
    @classmethod
    async def fetch_reviews_summary(cls, arg_seqAppids: Sequence[int]) -> dict[int, dict]:
        """
        Busca o resumo de reviews de múltiplos jogos na Steam de forma assíncrona.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.
        
        Retorna:
        - var_dictResult (dict): Um dicionário mapeando appids para seus resumos de reviews.
        """
        try:
            var_dictConfigAPI = Settings.steam_api_reviews()
            var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)

            # Controle de concorrência
            var_semSemaphore = asyncio.Semaphore(var_intAsyncConcurrency)

            # Contadores de erro
            var_intErrosHTTP = 0
            var_intErrosForbidden = 0
            var_intErrosTooManyRequests = 0
            var_intErrosTimeout = 0
            var_intErrosOutros = 0
            var_intAusentes = 0

            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> dict | None:
                """
                Worker assíncrono para buscar o resumo de reviews de um único appid.

                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.

                Retorna:
                - var_dictSummary (dict | None): Um dicionário com o resumo das reviews ou None se não encontrado.
                """
                nonlocal var_intErrosHTTP, var_intErrosForbidden, var_intErrosTooManyRequests, var_intErrosTimeout, var_intErrosOutros, var_intAusentes
                
                async with var_semSemaphore:
                    # Pequena espera para evitar throttling
                    await asyncio.sleep(random.random() * 0.3)
                    var_strUrl = STEAM_REVIEWS_URL.format(appid=arg_intAppid)
                    var_dictParams = {"json": "1", "language": "all"}
                    try:
                        # Faz a requisição assíncrona
                        async with arg_clientSession.get(var_strUrl, params=var_dictParams, timeout=30) as var_respResponse:
                            var_respResponse.raise_for_status()
                            # Processa os dados recebidos
                            var_dictData = await var_respResponse.json()
                            
                            # Verifica se os dados são válidos
                            if var_dictData and var_dictData.get("success") == 1:
                                var_dictSummary = var_dictData.get("query_summary", {})
                                if isinstance(var_dictSummary, dict):
                                    var_dictSummary = dict(var_dictSummary)
                                    var_dictSummary["appid"] = arg_intAppid
                                    return var_dictSummary
                            
                            # Caso não retorne dados válidos (success != 1 ou dados ausentes)
                            var_intAusentes += 1
                            return None
                    except aiohttp.ClientError as e_http:
                        # Captura erros específicos de HTTP (conexão, timeout, status).
                        var_intErrosHTTP += 1
                        if hasattr(e_http, 'status'):
                            if e_http.status == 403:
                                var_intErrosForbidden += 1
                            elif e_http.status == 429:
                                var_intErrosTooManyRequests += 1
                        return None
                    except asyncio.TimeoutError:
                        # Captura erro de timeout.
                        var_intErrosTimeout += 1
                        return None
                    except Exception:
                        # Captura outros erros não classificados.
                        var_intErrosOutros += 1
                        return None

            # Executa os workers assíncronos
            async with aiohttp.ClientSession(headers=CON_DEFAULT_HEADERS) as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, var_intAppid)) for var_intAppid in arg_seqAppids]
                logger.info(f"Iniciando busca de 'REVIEWS' assíncrona para {len(var_listTasks)} AppIDs com concorrência {var_intAsyncConcurrency}...")
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.info("Busca assíncrona concluída.")
            
            # Filtra os resultados válidos e os retorna
            var_dictResult: dict[int, dict] = {}
            var_listReviews: list[dict] = []
            var_intSemReviews = 0
            for idx, var_dictOut in enumerate(var_listOut):
                if isinstance(var_dictOut, dict):
                    var_dictResult = {
                        "APPID": var_dictOut.get("appid"),
                        "data": var_dictOut
                    }
                    var_listReviews.append(var_dictResult)
                else:
                    var_intSemReviews += 1

            # Atualiza contador de ausentes (jogos válidos mas sem reviews)
            var_intAusentes += var_intSemReviews
            var_intFalha = len(arg_seqAppids) - len(var_listReviews)
            logger.info(f"--- Busca concluída: ---")
            logger.info(f"{len(var_listReviews)} sucesso(s) ({len(var_listReviews)/(len(arg_seqAppids)):.2%}),")
            logger.info(f"{var_intFalha} falha(s) ({var_intFalha/len(arg_seqAppids):.2%}).")
            logger.info(f"--- Detalhamento dos erros: ---")
            logger.info(f"* HTTP: {var_intErrosHTTP} (403 Forbidden: {var_intErrosForbidden}, 429 Too Many Requests: {var_intErrosTooManyRequests})")
            logger.info(f"* Timeout: {var_intErrosTimeout}")
            logger.info(f"* Ausentes: {var_intAusentes}")
            logger.info(f"* Outros: {var_intErrosOutros}")
            return var_listReviews
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar reviews em bulk: {e}")
            raise RuntimeError(f"Falha ao buscar resumos de reviews: {e}")
        
    # ------------------- ITAD lookups -------------------
    @classmethod
    async def lookup_itad_ids_batched(cls, arg_seqAppids: Sequence[int]) -> dict[int, dict]:
        """
        Realiza lookup de IDs na API do IsThereAnyDeal (ITAD) de forma assíncrona, processando em batches.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.
        
        Retorna:
        - var_dictAllResults (dict): Um dicionário mapeando appids para seus dados do ITAD.
        """
        var_dictConfigAPI = Settings.steam_api_itad()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        var_intDelay = var_dictConfigAPI.get("Delay", 120)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 3)

        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        
        logger.info(f"=== PROCESSAMENTO EM BATCHES (ITAD LOOKUP) ===")
        logger.info(f"Total de itens: {var_intTotalItems:,}")
        logger.info(f"Tamanho do batch: {var_intBatchSize:,}")
        logger.info(f"Total de batches: {var_intTotalBatches}")
        logger.info(f"Delay entre batches: {var_intDelay}s")
        logger.info(f"Concorrência por batch: {var_intAsyncConcurrency}")
        logger.info(f"===============================================\n")
        
        var_dictAllResults = {}
        
        for var_intBatchNum in range(var_intTotalBatches):
            var_intStart = var_intBatchNum * var_intBatchSize
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]
            
            logger.info(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")
            
            # Processa o batch atual
            var_dictBatchResults = await cls.lookup_itad_ids(var_listBatch)
            
            # Acumula os resultados
            if var_dictBatchResults:
                PostgreSQL.inserir_dados_itad_raw_batched(var_dictBatchResults)
                
            # Aguarda entre batches (exceto no último)
            if var_intBatchNum < var_intTotalBatches - 1:
                logger.info(f"Aguardando {var_intDelay}s antes do próximo batch...\n")
                await asyncio.sleep(var_intDelay)
        
        logger.info(f"===========PROCESSAMENTO COMPLETO!==========")
        logger.info(f"Total processado: {len(var_dictAllResults):,} sucessos de {var_intTotalItems:,} itens ({len(var_dictAllResults)/var_intTotalItems:.2%})")
    
    @classmethod
    async def lookup_itad_ids(cls, arg_seqAppids: Sequence[int]) -> dict[int, dict]:
        """
        Realiza lookup de IDs na API do IsThereAnyDeal (ITAD) de forma assíncrona.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.
        
        Retorna:
        - var_dictResults (dict): Um dicionário mapeando appids para seus dados do ITAD.
        """
        if not Settings._var_strItadApiKey:
            raise RuntimeError("ITAD_API_KEY não definido")
        
        try:
            var_dictConfigAPI = Settings.steam_api_itad()
            var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 3)

            # Controle de concorrência
            var_semSemaphore = asyncio.Semaphore(var_intAsyncConcurrency)
            
            # Contadores de erro
            var_intErrosHTTP = 0
            var_intErrosForbidden = 0
            var_intErrosTooManyRequests = 0
            var_intErrosTimeout = 0
            var_intErrosOutros = 0
            var_intNaoEncontrados = 0
            
            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> tuple[int, dict | None]:
                """
                Worker assíncrono para buscar dados ITAD de um único appid.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.
                
                Retorna:
                - tuple: (appid, dados do ITAD ou None se não encontrado)
                """
                nonlocal var_intErrosHTTP, var_intErrosForbidden, var_intErrosTooManyRequests, var_intErrosTimeout, var_intErrosOutros, var_intNaoEncontrados
                
                async with var_semSemaphore:
                    # Pequena espera para evitar throttling
                    await asyncio.sleep(random.random() * 0.2)
                    
                    if not isinstance(arg_intAppid, int) or arg_intAppid <= 0:
                        var_intErrosOutros += 1
                        return (arg_intAppid, None)
                    
                    var_dictParams = {
                        "key": Settings._var_strItadApiKey,
                        "appid": arg_intAppid,
                    }
                    
                    try:
                        # Faz a requisição assíncrona
                        async with arg_clientSession.get(ITAD_LOOKUP_IDS_URL, params=var_dictParams, timeout=30) as var_respResponse:
                            var_respResponse.raise_for_status()
                            # Processa os dados recebidos
                            var_dictData = await var_respResponse.json()
                            
                            # Verifica se o jogo foi encontrado
                            if var_dictData and var_dictData.get("found"):
                                var_dictGame = var_dictData.get("game", {})
                                if isinstance(var_dictGame, dict):
                                    return (arg_intAppid, var_dictGame)
                            
                            # Jogo não encontrado no ITAD
                            var_intNaoEncontrados += 1
                            return (arg_intAppid, None)
                            
                    except aiohttp.ClientError as e_http:
                        # Captura erros específicos de HTTP (conexão, timeout, status).
                        var_intErrosHTTP += 1
                        if hasattr(e_http, 'status'):
                            if e_http.status == 403:
                                var_intErrosForbidden += 1
                            elif e_http.status == 429:
                                var_intErrosTooManyRequests += 1
                        return (arg_intAppid, None)
                    except asyncio.TimeoutError:
                        # Captura erro de timeout.
                        var_intErrosTimeout += 1
                        return (arg_intAppid, None)
                    except Exception:
                        # Captura outros erros não classificados.
                        var_intErrosOutros += 1
                        return (arg_intAppid, None)
            
            # Executa os workers assíncronos
            async with aiohttp.ClientSession() as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, var_intAppid)) for var_intAppid in arg_seqAppids]
                logger.info(f"Iniciando busca de 'ITAD LOOKUP' assíncrona para {len(var_listTasks)} AppIDs com concorrência {var_intAsyncConcurrency}...")
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.info("Busca assíncrona concluída.")
            
            # Filtra os resultados válidos e os retorna
            var_dictResults: dict[int, dict] = {}
            for var_tupleResult in var_listOut:
                if isinstance(var_tupleResult, tuple) and len(var_tupleResult) == 2:
                    var_intAppid, var_dictData = var_tupleResult
                    if var_dictData is not None:
                        var_dictResults[var_intAppid] = var_dictData
            
            var_intFalha = len(arg_seqAppids) - len(var_dictResults)
            logger.info(f"--- Busca concluída: ---")
            logger.info(f"{len(var_dictResults)} sucesso(s) ({len(var_dictResults)/(len(arg_seqAppids)):.2%}),")
            logger.info(f"{var_intFalha} falha(s) ({var_intFalha/len(arg_seqAppids):.2%}).")
            logger.info(f"--- Detalhamento dos erros: ---")
            logger.info(f"* HTTP: {var_intErrosHTTP} (403 Forbidden: {var_intErrosForbidden}, 429 Too Many Requests: {var_intErrosTooManyRequests})")
            logger.info(f"* Timeout: {var_intErrosTimeout}")
            logger.info(f"* Não encontrados no ITAD: {var_intNaoEncontrados}")
            logger.info(f"* Outros: {var_intErrosOutros}")
            return var_dictResults
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar ITAD lookup em bulk: {e}")
            raise RuntimeError(f"ITAD lookup falhou: {e}")
    
    @classmethod
    def lookup_itad_title(cls, arg_seqTitles: Sequence[str]) -> dict:
        """
        Realiza lookup de títulos na API do IsThereAnyDeal (ITAD).
        
        Parâmetros:
        - arg_seqTitles (Sequence[str]): Uma sequência de títulos dos jogos.
        
        Retorna:
        - var_dictResults (dict): Um dicionário com os resultados do lookup.
        """
        if not Settings._var_strItadApiKey:
            raise RuntimeError("ITAD_API_KEY não definido")
        try:
            var_dictHeaders = {"Content-Type": "application/json"}
            var_respResponse = requests.post(
                f"{ITAD_LOOKUP_URL}?key={Settings._var_strItadApiKey}",
                data=json.dumps(list(arg_seqTitles)),
                headers=var_dictHeaders,
                timeout=30,
            )
            var_respResponse.raise_for_status()
            var_dictResults = var_respResponse.json()
            return var_dictResults
        except Exception as e:
            raise RuntimeError(f"ITAD lookup falhou: {e}")

    # ------------------- ITAD price history -------------------
    @classmethod
    def fetch_price_history(cls, arg_strItadPlain: str, arg_intAnos: int = 5) -> list:
        """
        Busca o histórico de preços de um jogo na API do IsThereAnyDeal (ITAD).
        
        Parâmetros:
        - arg_strItadPlain (str): O identificador "plain" do jogo no ITAD.
        - arg_intAnos (int): O número de anos para buscar o histórico.
        
        Retorna:
        - var_dictResults (list): Uma lista com o histórico de preços do jogo.
        """
        if not Settings._var_strItadApiKey:
            raise RuntimeError("ITAD_API_KEY não definido")
        
        # Calcula o tempo desde a data atual para o parâmetro 'since'
        var_strSince = (datetime.now(timezone.utc) - timedelta(days=arg_intAnos * 365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        var_dictParams = {
            "key": Settings._var_strItadApiKey,
            "id": arg_strItadPlain,
            "shops": "61", # ID da Steam no ITAD
            "country": "BR",
            "since": var_strSince,
        }
        try:
            var_respResponse = requests.get(ITAD_HISTORY_URL, params=var_dictParams, timeout=30)
            var_respResponse.raise_for_status()
            var_dictResults = var_respResponse.json()
            return var_dictResults
        except Exception as e:
            raise RuntimeError(f"Falha histórico ITAD: {e}")
        
    # ------------------- Async ITAD price history bulk com batches -------------------
    @classmethod
    async def fetch_price_history_bulk_batched(cls, arg_seqItadPlain: Sequence[str], arg_intAnos: int = 5) -> dict:
        """
        Busca o histórico de preços de múltiplos jogos na API do IsThereAnyDeal (ITAD) de forma assíncrona, processando em batches.

        Parâmetros:
        - arg_seqItadPlain (Sequence[str]): Uma sequência de identificadores "plain" dos jogos no ITAD.
        - arg_intAnos (int): O número de anos para buscar o histórico.

        Retorna:
        - var_dictAllResults (dict): Um dicionário mapeando cada plain para seu histórico de preços.
        """
        var_dictConfigAPI = Settings.steam_api_itad()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        var_intDelay = var_dictConfigAPI.get("Delay", 120)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTotalItems = len(arg_seqItadPlain)
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        
        logger.info(f"=== PROCESSAMENTO EM BATCHES (HISTÓRICO ITAD) ===")
        logger.info(f"Total de itens: {var_intTotalItems:,}")
        logger.info(f"Tamanho do batch: {var_intBatchSize:,}")
        logger.info(f"Total de batches: {var_intTotalBatches}")
        logger.info(f"Delay entre batches: {var_intDelay}s")
        logger.info(f"Concorrência por batch: {var_intAsyncConcurrency}")
        logger.info(f"Anos de histórico: {arg_intAnos}")
        logger.info(f"==================================================\n")
        
        var_dictAllResults = {}
        
        for var_intBatchNum in range(var_intTotalBatches):
            var_intStart = var_intBatchNum * var_intBatchSize
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqItadPlain[var_intStart:var_intEnd]
            
            logger.info(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")
            
            # Processa o batch atual
            var_dictBatchResults = await cls.fetch_price_history_bulk(var_listBatch, arg_intAnos)
            var_dictAllResults.update(var_dictBatchResults)
            
            # Aguarda entre batches (exceto no último)
            if var_intBatchNum < var_intTotalBatches - 1:
                logger.info(f"Aguardando {var_intDelay}s antes do próximo batch...\n")
                await asyncio.sleep(var_intDelay)
        
        logger.info(f"===========PROCESSAMENTO COMPLETO!==========")
        logger.info(f"Total processado: {len(var_dictAllResults):,} sucessos de {var_intTotalItems:,} itens ({len(var_dictAllResults)/var_intTotalItems:.2%})")
        
        return var_dictAllResults
    
    # ------------------- Async ITAD price history bulk -------------------
    @classmethod
    async def fetch_price_history_bulk(cls, arg_seqItadPlain: Sequence[str], arg_intAnos: int = 5) -> dict:
        """
        Busca o histórico de preços de múltiplos jogos na API do IsThereAnyDeal (ITAD) de forma assíncrona.

        Parâmetros:
        - arg_seqItadPlain (Sequence[str]): Uma sequência de identificadores "plain" dos jogos no ITAD.
        - arg_intAnos (int): O número de anos para buscar o histórico.

        Retorna:
        - var_dictResults (dict): Um dicionário mapeando cada plain para seu histórico de preços.
        """
        var_dictConfigAPI = Settings.steam_api_itad()
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 3)

        if not Settings._var_strItadApiKey:
            raise RuntimeError("ITAD_API_KEY não definido")
        
        try:
            var_strSince = (datetime.now(timezone.utc) - timedelta(days=arg_intAnos * 365)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Controle de concorrência
            var_semSemaphore = asyncio.Semaphore(var_intAsyncConcurrency)
            
            # Contadores de erro
            var_intErrosHTTP = 0
            var_intErrosForbidden = 0
            var_intErrosTooManyRequests = 0
            var_intErrosTimeout = 0
            var_intErrosOutros = 0
            var_intAusentes = 0
            
            async def worker(arg_clientSession: aiohttp.ClientSession, arg_strItadPlain: str) -> dict | None:
                """
                Worker assíncrono para buscar o histórico de preços de um único jogo.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_strItadPlain (str): O identificador "plain" do jogo no ITAD.
                
                Retorna:
                - var_dictData (dict | None): Um dicionário com o histórico de preços ou None se não encontrado.
                """
                nonlocal var_intErrosHTTP, var_intErrosForbidden, var_intErrosTooManyRequests, var_intErrosTimeout, var_intErrosOutros, var_intAusentes
                
                async with var_semSemaphore:
                    # Pequena espera para evitar throttling
                    await asyncio.sleep(random.random() * 0.2)
                    var_dictParams = {
                        "key": Settings._var_strItadApiKey,
                        "id": arg_strItadPlain,
                        "shops": "61",
                        "country": "BR",
                        "since": var_strSince,
                    }
                    try:
                        # Faz a requisição assíncrona
                        async with arg_clientSession.get(ITAD_HISTORY_URL, params=var_dictParams, timeout=30) as var_respResponse:
                            var_respResponse.raise_for_status()
                            # Processa os dados recebidos
                            var_dictData = await var_respResponse.json()
                            
                            # Verifica se os dados são válidos
                            if var_dictData and var_dictData is not None:
                                return var_dictData
                            
                            # Caso não retorne dados válidos
                            var_intAusentes += 1
                            return None
                    except aiohttp.ClientError as e_http:
                        # Captura erros específicos de HTTP (conexão, timeout, status).
                        var_intErrosHTTP += 1
                        if hasattr(e_http, 'status'):
                            if e_http.status == 403:
                                var_intErrosForbidden += 1
                            elif e_http.status == 429:
                                var_intErrosTooManyRequests += 1
                        return None
                    except asyncio.TimeoutError:
                        # Captura erro de timeout.
                        var_intErrosTimeout += 1
                        return None
                    except Exception:
                        # Captura outros erros não classificados.
                        var_intErrosOutros += 1
                        return None

            # Executa os workers assíncronos
            async with aiohttp.ClientSession() as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, plain)) for plain in arg_seqItadPlain]
                logger.info(f"Iniciando busca de 'HISTÓRICO DE PREÇOS' assíncrona para {len(var_listTasks)} jogos (ITAD) com concorrência {var_intAsyncConcurrency}...")
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.info("Busca assíncrona concluída.")
            
            # Filtra os resultados válidos e os retorna
            var_dictResults = {}
            for idx, var_dictOut in enumerate(var_listOut):
                if isinstance(var_dictOut, dict) and var_dictOut is not None:
                    var_dictResults[arg_seqItadPlain[idx]] = var_dictOut
            
            var_intFalha = len(arg_seqItadPlain) - len(var_dictResults)
            logger.info(f"--- Busca concluída: ---")
            logger.info(f"{len(var_dictResults)} sucesso(s) ({len(var_dictResults)/(len(arg_seqItadPlain)):.2%}),")
            logger.info(f"{var_intFalha} falha(s) ({var_intFalha/len(arg_seqItadPlain):.2%}).")
            logger.info(f"--- Detalhamento dos erros: ---")
            logger.info(f"* HTTP: {var_intErrosHTTP} (403 Forbidden: {var_intErrosForbidden}, 429 Too Many Requests: {var_intErrosTooManyRequests})")
            logger.info(f"* Timeout: {var_intErrosTimeout}")
            logger.info(f"* Ausentes: {var_intAusentes}")
            logger.info(f"* Outros: {var_intErrosOutros}")
            return var_dictResults
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar histórico ITAD em bulk: {e}")
            raise RuntimeError(f"Falha ao buscar histórico ITAD em bulk: {e}")