from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
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

STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"

class SteamClient:
    """
    Cliente para interagir com a Steam API.
    """
    _var_intDelay = 180
    
    # ------------------- Async bulk details com batches -------------------
    @classmethod
    async def fetch_details_bulk_batched(cls, arg_seqAppids: Sequence[int]) -> None:
        """
        Busca os detalhes de múltiplos jogos na Steam de forma assíncrona, processando em batches.
        Com adaptive batch sizing baseado na taxa de sucesso.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.

        Retorna:
        - var_dictAllResults (dict): Um dicionário com todos os detalhes dos jogos.
        """
        var_dictConfigAPI = Settings.steam_api_details()
        var_intBatchSizeInicial = var_dictConfigAPI.get("BatchSize", 50)
        var_intBatchSizeMin = var_dictConfigAPI.get("BatchSizeMin", 10)
        var_intBatchSizeMax = var_dictConfigAPI.get("BatchSizeMax", 200)
        var_intBatchSize = var_intBatchSizeInicial
        cls._var_intDelay = var_dictConfigAPI.get("Delay", 180)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTentativaMaxima = var_dictConfigAPI.get("max_tentativas", 3)
        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatchesEstimado = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        logger.info(f"")
        logger.info(f"=== PROCESSAMENTO EM BATCHES ===")
        logger.info(f"Total de itens: {var_intTotalItems:,}")
        logger.info(f"Tamanho do batch inicial: {var_intBatchSize:,}")
        logger.info(f"Batches estimados: {var_intTotalBatchesEstimado} (pode variar com adaptive sizing)")
        logger.info(f"Delay entre batches: {cls._var_intDelay}s")
        logger.info(f"Concorrência por batch: {var_intAsyncConcurrency}")
        logger.info(f"Tempo Estimado para conclusão total do Batch: {(var_intTotalBatchesEstimado * cls._var_intDelay)/60:.1f} minutos")
        logger.info(f"================================\n")
        
        var_dictAllResults = {}
        var_intCurrentIndex = 0
        var_intBatchNum = 0
        
        while var_intCurrentIndex < var_intTotalItems:
            var_intStart = var_intCurrentIndex
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]
            var_intBatchNum += 1
            
            logger.info(f"Batch {var_intBatchNum} (size={var_intBatchSize}) - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")
            
            # Processa o batch atual e recebe estatísticas
            var_listBatchResults, var_dictBatchStats = await cls.fetch_details_bulk(var_listBatch)
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

            # Usa estatísticas retornadas por fetch_details_bulk (já calculadas corretamente)
            var_intAusentes = var_dictBatchStats["ausentes"]
            var_intErrosReais = var_dictBatchStats["erros"]
            var_floatTaxaSucesso = var_dictBatchStats["taxa_efetiva"]

            # Log detalhado com valores corretos
            logger.info(f"Batch {var_intBatchNum}: {len(var_listDetails)} sucessos, {var_intAusentes} ausentes, {var_intErrosReais} erros")

            # Ajusta batch size dinamicamente
            if var_floatTaxaSucesso > 0.95:  # >95% sucesso - aumenta batch
                var_intNovoSize = min(int(var_intBatchSize * 1.2), var_intBatchSizeMax)
                if var_intNovoSize != var_intBatchSize:
                    logger.info(f"Taxa {var_floatTaxaSucesso:.1%} (excluiu {var_intAusentes} ausentes) - "
                        f"Aumentando: {var_intBatchSize} → {var_intNovoSize}")
                    var_intBatchSize = var_intNovoSize
            elif var_floatTaxaSucesso < 0.70:  # <70% sucesso - reduz batch
                var_intNovoSize = max(int(var_intBatchSize * 0.5), var_intBatchSizeMin)
                if var_intNovoSize != var_intBatchSize:
                    logger.warning(f"Taxa {var_floatTaxaSucesso:.1%} (excluiu {var_intAusentes} ausentes) - "
                        f"Reduzindo: {var_intBatchSize} → {var_intNovoSize}")
                    var_intBatchSize = var_intNovoSize
            
            # Insere no PostgreSQL (Docker) em vez de Supabase
            if var_listDetails:
                PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=var_listDetails)
                logger.info(f"Dados de detalhes inseridos com sucesso no PostgreSQL ({len(var_listDetails)} registros).")
            else:
                logger.warning("Nenhum dado válido para inserir neste batch.")

            # Avança o índice para o próximo batch
            var_intCurrentIndex = var_intEnd
            
            # Aguarda entre batches (exceto no último)
            if var_intCurrentIndex < var_intTotalItems:
                logger.info(f"Progresso: {var_intCurrentIndex:,}/{var_intTotalItems:,} ({var_intCurrentIndex/var_intTotalItems:.1%}).\n")
                
        logger.info(f"===========PROCESSAMENTO COMPLETO! (Detalhes)==========")
        logger.info(f"Total de batches executados: {var_intBatchNum}")
        logger.info(f"Total de itens processados: {var_intCurrentIndex:,} de {var_intTotalItems:,}")
        logger.info(f"================================\n")

    # ------------------- Método auxiliar para retry -------------------
    @classmethod
    async def _retry_with_backoff(cls, arg_clientSession: aiohttp.ClientSession, arg_intAppid: int, arg_strTipo: str = 'detalhes', arg_intMaxRetries: int = 3) -> dict | None:
        """
        Retry com backoff exponencial para erros 429 (Too Many Requests).
        
        Parâmetros:
        - arg_clientSession (aiohttp.ClientSession): Sessão HTTP reutilizável.
        - arg_intAppid (int): AppID do jogo.
        - arg_strTipo (str): Tipo de dados sendo buscado (detalhes ou reviews) para logs mais claros.
        - arg_intMaxRetries (int): Número máximo de tentativas.

        Retorna:
        - dict | None: Dados do jogo ou None se falhar.
        """
        if arg_strTipo == 'detalhes':
            url = f"{STEAM_DETAILS_URL}?appids={arg_intAppid}"
        elif arg_strTipo == 'reviews':
            url = STEAM_REVIEWS_URL.format(appid=arg_intAppid)
            
        for var_intAttempt in range(arg_intMaxRetries):
            try:
                async with arg_clientSession.get(url) as resp:
                    if resp.status == 429:
                        var_intWaitTime = (2 ** var_intAttempt) * cls._var_intDelay  # 120s, 240s, 480s
                        logger.warning(f"AppID {arg_intAppid}: 429 na tentativa {var_intAttempt+1}/{arg_intMaxRetries}. Aguardando {var_intWaitTime}s...")
                        await asyncio.sleep(var_intWaitTime)
                        continue
                    if resp.status == 502:
                        var_intWaitTime = (2 ** var_intAttempt) * cls._var_intDelay  # 120s, 240s, 480s
                        logger.warning(f"AppID {arg_intAppid}: 502 na tentativa {var_intAttempt+1}/{arg_intMaxRetries}. Aguardando {var_intWaitTime}s...")
                        await asyncio.sleep(var_intWaitTime)
                        continue
                    elif resp.status == 200:
                        return await resp.json()
                    else:
                        logger.warning(f"AppID {arg_intAppid}: Status {resp.status} na tentativa {var_intAttempt+1}")
                        return None
            except Exception as e:
                if var_intAttempt == arg_intMaxRetries - 1:
                    logger.error(f"AppID {arg_intAppid}: Falha após {arg_intMaxRetries} tentativas - {e}")
                    return None
                await asyncio.sleep(5)  # Espera 5s entre tentativas com erro
        return None

    # ------------------- Async bulk details -------------------
    @classmethod
    async def fetch_details_bulk(cls, arg_seqAppids: Sequence[int]) -> tuple[list[dict], dict]:
        """
        Busca os detalhes de múltiplos jogos na Steam de forma assíncrona.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.

        Retorna:
        - tuple[list[dict], dict]: Uma tupla contendo:
            - var_listResults (list[dict]): Lista de dicionários com os detalhes dos jogos (sem ausentes).
            - var_dictStats (dict): Estatísticas do processamento (sucessos, ausentes, erros, taxa_efetiva).
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
                                # Erro 429: Tenta retry com backoff exponencial
                                logger.debug(f"AppID {arg_intAppid}: 429 detectado, iniciando retry com backoff...")
                                var_dictRetryData = await cls._retry_with_backoff(arg_clientSession, arg_intAppid, arg_strTipo='detalhes', arg_intMaxRetries=3)
                                if var_dictRetryData:
                                    # Sucesso no retry - processa os dados
                                    if var_dictRetryData.get(str(arg_intAppid), {}).get("success"):
                                        var_dictDetails = var_dictRetryData[str(arg_intAppid)]
                                        var_dictDetails["APPID"] = arg_intAppid
                                        return var_dictDetails
                                    elif var_dictRetryData.get(str(arg_intAppid), {}).get("success") is False:
                                        var_intAusentes += 1
                                        var_dictDetails = var_dictRetryData[str(arg_intAppid)]
                                        var_dictDetails["data"] = "AUSENTE"
                                        var_dictDetails["APPID"] = arg_intAppid
                                        return var_dictDetails
                                # Falhou mesmo com retry
                                var_intErrosTooManyRequests += 1
                            elif e_http.status == 502:
                                # Erro 502: Tenta retry com backoff exponencial
                                logger.debug(f"AppID {arg_intAppid}: 502 detectado, iniciando retry com backoff...")
                                var_dictRetryData = await cls._retry_with_backoff(arg_clientSession, arg_intAppid, arg_strTipo='detalhes', arg_intMaxRetries=3)
                                if var_dictRetryData:
                                    # Sucesso no retry - processa os dados
                                    if var_dictRetryData.get(str(arg_intAppid), {}).get("success"):
                                        var_dictDetails = var_dictRetryData[str(arg_intAppid)]
                                        var_dictDetails["APPID"] = arg_intAppid
                                        return var_dictDetails
                                    elif var_dictRetryData.get(str(arg_intAppid), {}).get("success") is False:
                                        var_intAusentes += 1
                                        var_dictDetails = var_dictRetryData[str(arg_intAppid)]
                                        var_dictDetails["data"] = "AUSENTE"
                                        var_dictDetails["APPID"] = arg_intAppid
                                        return var_dictDetails
                                # Falhou mesmo com retry
                                var_intErrosOutros += 1
                            else:
                                logger.warning(f"AppID {arg_intAppid}: Erro HTTP status {e_http.status}")
                        return None
                    except asyncio.TimeoutError:
                        # Captura erro de timeout
                        var_intErrosTimeout += 1
                        return None
                    except Exception:
                        # Captura outros erros não classificados.
                        var_intErrosOutros += 1
                        return None

            # Executa os workers assíncronos
            # Configuração do connector para evitar ConnectionResetError no Windows
            var_connector = aiohttp.TCPConnector(
                limit=100,  # Limite de conexões simultâneas
                limit_per_host=20,  # Limite por host
                force_close=True,  # Fecha conexões adequadamente no Windows
                enable_cleanup_closed=True  # Limpa sockets fechados
            )
            var_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            
            async with aiohttp.ClientSession(
                headers=CON_DEFAULT_HEADERS,
                connector=var_connector,
                timeout=var_timeout
            ) as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, var_intAppid)) for var_intAppid in arg_seqAppids]
                logger.info(f"Iniciando busca de 'DETALHES' assíncrona para {len(var_listTasks)} AppIDs com concorrência {var_intAsyncConcurrency}...")
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.info("Busca assíncrona concluída.")

            # Conta None's e filtra a lista de forma segura
            var_intContNones = sum(1 for item in var_listOut if item is None)
            var_listOut = [item for item in var_listOut if item is not None]
            
            var_intTotal = len(arg_seqAppids)
            var_intTotal = 1 if var_intTotal == 0 else var_intTotal  # Evita divisão por zero
            var_intAusentes = sum(1 for item in var_listOut if item.get("data") == "AUSENTE")
            var_intSucesso = len(var_listOut) - var_intAusentes
            var_intFalha = var_intTotal - var_intSucesso
            var_intErrosReais = var_intTotal - var_intSucesso - var_intAusentes
            var_intTotalProcessavel = var_intTotal - var_intAusentes
            var_floatTaxaSucesso = var_intSucesso / var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1

            logger.info(f"{'='*50}")
            logger.info(f" Sucessos: {var_intSucesso} ({var_intSucesso/var_intTotal:.1%})")
            logger.info(f" AUSENTES: {var_intAusentes} ({var_intAusentes/var_intTotal:.1%}) ← Jogos não existem na store")
            logger.info(f" Erros: {var_intErrosReais} ({var_intErrosReais/var_intTotal:.1%}) ← Verdadeiros erros")
            if var_intErrosReais > 0:
                logger.info(f"   - 429 Too Many: {var_intErrosTooManyRequests} ({var_intErrosTooManyRequests/var_intErrosReais:.1%} dos erros)")
                logger.info(f"   - Timeout: {var_intErrosTimeout} ({var_intErrosTimeout/var_intErrosReais:.1%} dos erros)")
            logger.info(f" Taxa Efetiva: {var_intSucesso}/{var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1} = "
                f"{var_floatTaxaSucesso:.1%} ← Base para ajuste de batch")
            logger.info(f"{'='*50}")
            
            # Filtra apenas dados válidos antes de retornar
            var_listValidData = []
            for item in var_listOut:
                if item and isinstance(item, dict) and item.get("data") != "AUSENTE" and item.get("APPID"):
                    var_listValidData.append(item)
            
            if not var_listValidData:
                logger.warning("Nenhum dado válido encontrado após filtragem.")
            
            # Prepara estatísticas para retornar
            var_dictStats = {
                "sucessos": var_intSucesso,
                "ausentes": var_intAusentes,
                "erros": var_intErrosReais,
                "taxa_efetiva": var_floatTaxaSucesso,
                "total_processavel": var_intTotalProcessavel
            }
            
            return var_listValidData, var_dictStats
        
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
        cls._var_intDelay = var_dictConfigAPI.get("Delay", 120)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        var_intTentativaMaxima = var_dictConfigAPI.get("max_tentativas", 3)

        logger.info(f"")
        logger.info(f"=== PROCESSAMENTO EM BATCHES (REVIEWS) ===")
        logger.info(f"Total de itens: {var_intTotalItems:,}")
        logger.info(f"Tamanho do batch: {var_intBatchSize:,}")
        logger.info(f"Total de batches: {var_intTotalBatches}")
        logger.info(f"Delay entre batches: {cls._var_intDelay}s")
        logger.info(f"Concorrência por batch: {var_intAsyncConcurrency}")
        logger.info(f"Tempo Estimado para conclusão total do Batch: {(var_intTotalBatches * cls._var_intDelay)/60:.1f} minutos")
        logger.info(f"==========================================\n")
        
        for var_intBatchNum in range(var_intTotalBatches):
            var_intStart = var_intBatchNum * var_intBatchSize
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]

            logger.debug(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")

            # Processa o batch atual
            var_listBatchResults = await cls.fetch_reviews_summary(var_listBatch)
            
            var_listReviews = []
            var_intAusentesReviews = 0
            for var_dictResult in var_listBatchResults:
                # Valida se o resultado não é None ou exceção
                if var_dictResult is None or isinstance(var_dictResult, Exception):
                    var_intAusentesReviews += 1
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

            # Log detalhado do batch
            var_intErrosReais = len(var_listBatch) - len(var_listReviews) - var_intAusentesReviews
            logger.info(f"Batch {var_intBatchNum + 1}: {len(var_listReviews)} sucessos, {var_intAusentesReviews} ausentes, {var_intErrosReais} erros")

            # Insere no PostgreSQL (Docker) em vez de Supabase
            if var_listReviews:
                PostgreSQL.inserir_dadosSteamRaw_Bulk(arg_listDados=var_listReviews)
                logger.info(f"Dados de reviews inseridos com sucesso no PostgreSQL ({len(var_listReviews)} registros).")
            else:
                logger.warning("Nenhum dado válido para inserir neste batch.")

            # Aguarda entre batches (exceto no último)
            if var_intBatchNum < var_intTotalBatches - 1:
                logger.info(f"Aguardando {cls._var_intDelay}s antes do próximo batch...\n")
                await asyncio.sleep(cls._var_intDelay)

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
                                # Erro 429: Tenta retry com backoff exponencial
                                logger.debug(f"AppID {arg_intAppid}: 429 detectado em reviews, iniciando retry com backoff...")
                                var_dictRetryData = await cls._retry_with_backoff(arg_clientSession, arg_intAppid, arg_intMaxRetries=3, arg_strTipo='reviews')
                                if var_dictRetryData:
                                    # Sucesso no retry - processa os dados
                                    if var_dictRetryData.get("success") == 1:
                                        var_dictSummary = var_dictRetryData.get("query_summary", {})
                                        if isinstance(var_dictSummary, dict):
                                            var_dictSummary = dict(var_dictSummary)
                                            var_dictSummary["appid"] = arg_intAppid
                                            logger.info(f"AppID {arg_intAppid}: SUCESSO após retry em reviews")
                                            return var_dictSummary
                                # Falha no retry
                                logger.warning(f"AppID {arg_intAppid}: Falha após retries em reviews")
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
            # Configuração do connector para evitar ConnectionResetError no Windows
            var_connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                force_close=True,
                enable_cleanup_closed=True
            )
            var_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            
            async with aiohttp.ClientSession(
                headers=CON_DEFAULT_HEADERS,
                connector=var_connector,
                timeout=var_timeout
            ) as var_respSession:
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
            var_intTotal = len(arg_seqAppids)
            var_intSucesso = len(var_listReviews)
            var_intErrosReais = var_intTotal - var_intSucesso - var_intAusentes
            
            logger.info(f"{'='*50}")
            logger.info(f" Sucessos: {var_intSucesso} ({var_intSucesso/var_intTotal:.1%})")
            logger.info(f"  AUSENTES: {var_intAusentes} ({var_intAusentes/var_intTotal:.1%}) ← Jogos sem reviews")
            logger.info(f" Erros: {var_intErrosReais} ({var_intErrosReais/var_intTotal:.1%}) ← Verdadeiros erros")
            if var_intErrosReais > 0:
                logger.info(f"   - 429 Too Many: {var_intErrosTooManyRequests} ({var_intErrosTooManyRequests/var_intErrosReais:.1%} dos erros)")
                logger.info(f"   - Timeout: {var_intErrosTimeout} ({var_intErrosTimeout/var_intErrosReais:.1%} dos erros)")
            var_intTotalProcessavel = var_intTotal - var_intAusentes
            var_floatTaxaEfetiva = var_intSucesso / var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1
            logger.info(f" Taxa Efetiva: {var_intSucesso}/{var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1} = {var_floatTaxaEfetiva:.1%}")
            logger.info(f"{'='*50}")
            return var_listReviews
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar reviews em bulk: {e}")
            raise RuntimeError(f"Falha ao buscar resumos de reviews: {e}")