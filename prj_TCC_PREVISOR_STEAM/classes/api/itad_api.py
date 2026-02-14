from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

from typing import Any, Sequence
from datetime import datetime, timedelta, timezone
from time import sleep
import asyncio, random, json, logging, os, re, aiohttp, requests, traceback

logger = logging.getLogger(__name__)

ITAD_LOOKUP_URL = "https://api.isthereanydeal.com/lookup/id/title/v1"
ITAD_HISTORY_URL = "https://api.isthereanydeal.com/games/history/v2"
ITAD_LOOKUP_IDS_URL = "https://api.isthereanydeal.com/games/lookup/v1"

class ITADClient:
    """
    Cliente para interagir com a Is There Any Deal API.
    """

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
            
            logger.debug(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")
            
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
            # Configuração do connector para evitar ConnectionResetError no Windows
            var_connector = aiohttp.TCPConnector(
                limit=50,
                limit_per_host=10,
                force_close=True,
                enable_cleanup_closed=True
            )
            var_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            
            async with aiohttp.ClientSession(
                connector=var_connector,
                timeout=var_timeout
            ) as var_respSession:
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
            
            logger.debug(f"Batch {var_intBatchNum + 1}/{var_intTotalBatches} - Processando itens {var_intStart + 1} a {var_intEnd} ({len(var_listBatch)} itens)...")
            
            # Processa o batch atual
            var_dictBatchResults = await cls.fetch_price_history_bulk(var_listBatch, arg_intAnos)
            var_dictAllResults.update(var_dictBatchResults)
            
            # Aguarda entre batches (exceto no último)
            if var_intBatchNum < var_intTotalBatches - 1:
                logger.info(f"Aguardando {var_intDelay}s antes do próximo batch...\n")
                await asyncio.sleep(var_intDelay)
            PostgreSQL.inserir_dados_itad_raw_historico_preco_bulk(var_dictBatchResults)
            
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
                            var_listData = await var_respResponse.json()
                            
                            # Verifica se os dados são válidos
                            if var_listData and var_listData is not None:
                                return var_listData
                            
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
            # Configuração do connector para evitar ConnectionResetError no Windows
            var_connector = aiohttp.TCPConnector(
                limit=50,
                limit_per_host=10,
                force_close=True,
                enable_cleanup_closed=True
            )
            var_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            
            async with aiohttp.ClientSession(
                connector=var_connector,
                timeout=var_timeout
            ) as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, plain)) for plain in arg_seqItadPlain]
                logger.info(f"Iniciando busca de 'HISTÓRICO DE PREÇOS' assíncrona para {len(var_listTasks)} jogos (ITAD) com concorrência {var_intAsyncConcurrency}...")
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.info("Busca assíncrona concluída.")
            
            # Filtra os resultados válidos e os retorna
            var_dictResults = {}
            for idx, var_listOutData in enumerate(var_listOut):
                if isinstance(var_listOutData, list) and var_listOutData is not None: 
                    var_dictResults[arg_seqItadPlain[idx]] = var_listOutData
            
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