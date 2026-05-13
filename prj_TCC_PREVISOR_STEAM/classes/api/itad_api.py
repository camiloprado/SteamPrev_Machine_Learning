from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_itad import PostgreSQLITAD

from typing import Sequence
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import asyncio, random, logging, aiohttp, os

logger = logging.getLogger("itad")

ITAD_LOOKUP_URL = "https://api.isthereanydeal.com/lookup/id/title/v1"
ITAD_HISTORY_URL = "https://api.isthereanydeal.com/games/history/v2"
ITAD_LOOKUP_IDS_URL = "https://api.isthereanydeal.com/games/lookup/v1"

class ITADClient:
    """
    Cliente para interagir com a Is There Any Deal API.
    """
    _var_intDelayBetweenBatches = 0
    _var_intRetryBackoffBase = 0
    _var_intProcessados = 0

    @classmethod
    async def lookup_itad_ids_batched(cls, arg_seqAppids: Sequence[int]) -> dict[int, dict]:
        """
        Realiza lookup de IDs na API do IsThereAnyDeal (ITAD) de forma assíncrona, processando em batches.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.
        
        Retorna:
        - var_dictAllResults (dict): Um dicionário mapeando appids para seus dados do ITAD.
        """
        logger = logging.getLogger("itad.lookup")
        var_dictConfigAPI = Settings.steam_api_itad()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        cls._var_intDelayBetweenBatches = var_dictConfigAPI.get("DelayBetweenBatches", var_dictConfigAPI.get("Delay", 120))
        cls._var_intRetryBackoffBase = var_dictConfigAPI.get("RetryBackoffBase", cls._var_intDelayBetweenBatches)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 3)

        var_intBatchSizeMax = int(os.getenv("STEAM_BATCH_SIZE_ITAD_MAX", 1000))
        var_intBatchSizeMin = int(os.getenv("STEAM_BATCH_SIZE_ITAD_MIN", 100))

        var_intTotalItems = len(arg_seqAppids)
        if var_intTotalItems == 0:
            logger.info("Nenhum AppID recebido para processamento ITAD.")
            return {}
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize

        logger.info(
            "ITAD LOOKUP (batches): "
            f"Total itens={var_intTotalItems:,} Tamanho batch={var_intBatchSize:,} Total batches={var_intTotalBatches} (estimado) "
            f"concorrência={var_intAsyncConcurrency} delayBatch={cls._var_intDelayBetweenBatches}s "
            f"retryBase={cls._var_intRetryBackoffBase}s"
        )
        
        var_dictAllResults = {}
        var_intTotalSucessos = 0
        var_intTotalAusentes = 0
        var_intTotalErros = 0
        var_intCurrentIndex = 0
        var_intBatchNum = 0

        while var_intCurrentIndex < var_intTotalItems:
            var_intStart = var_intCurrentIndex
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]
            var_intBatchNum += 1

            logger.info(
                "ITAD LOOKUP batch "
                f"{var_intBatchNum}/{var_intTotalBatches}: itens {var_intStart + 1}-{var_intEnd} "
                f"(n={len(var_listBatch)})"
            )
            
            # Processa o batch atual
            var_dictResults, var_dictBatchStats = await cls.lookup_itad_ids(var_listBatch)
            
            # Usa estatísticas retornadas para ajuste dinâmico do batch size
            var_intAusentes = var_dictBatchStats["ausentes"]
            var_intSucesso = var_dictBatchStats["sucessos"]
            var_intErrosReais = var_dictBatchStats["erros_http"] + var_dictBatchStats["erros_timeout"] + var_dictBatchStats["erros_outros"]
            var_intTotal = var_dictBatchStats["total"]
            var_intTotalProcessavel = var_intTotal - var_intAusentes
            var_floatTaxaSucesso = var_intSucesso / var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1

            var_intTotalSucessos += var_intSucesso
            var_intTotalAusentes += var_intAusentes
            var_intTotalErros += var_intErrosReais

            # Log detalhado com valores corretos
            logger.info(
                "ITAD LOOKUP batch "
                f"{var_intBatchNum}/{var_intTotalBatches} resultado: "
                f"sucesso={var_intSucesso} ausente={var_intAusentes} erros={var_intErrosReais} "
                f"taxa={var_floatTaxaSucesso:.1%}"
            )

            # Ajusta batch size dinamicamente
            if var_floatTaxaSucesso > 0.95:  # >95% sucesso - aumenta batch
                var_intNovoSize = min(int(var_intBatchSize * 1.2), var_intBatchSizeMax)
                if var_intNovoSize != var_intBatchSize:
                    logger.debug(
                        "ITAD LOOKUP ajuste batchSize: "
                        f"{var_intBatchSize} → {var_intNovoSize} (taxa={var_floatTaxaSucesso:.1%})"
                    )
                    var_intBatchSize = var_intNovoSize
            elif var_floatTaxaSucesso < 0.70:  # <70% sucesso - reduz batch
                var_intNovoSize = max(int(var_intBatchSize * 0.5), var_intBatchSizeMin)
                if var_intNovoSize != var_intBatchSize:
                    logger.warning(
                        "ITAD LOOKUP ajuste batchSize: "
                        f"{var_intBatchSize} → {var_intNovoSize} (taxa={var_floatTaxaSucesso:.1%})"
                    )
                    var_intBatchSize = var_intNovoSize

            # Acumula os resultados
            if var_dictResults:
                var_dictAllResults.update(var_dictResults)
                PostgreSQLITAD.inserir_dados_itad_raw_batched(var_dictResults)

            var_intCurrentIndex = var_intEnd
                
        logger.info(
            "ITAD LOOKUP concluído: "
            f"sucesso={var_intTotalSucessos:,}/{var_intTotalItems:,} ({var_intTotalSucessos/var_intTotalItems:.2%}) "
            f"ausente={var_intTotalAusentes:,} erros={var_intTotalErros:,}"
        )
        return var_dictAllResults
    
    @classmethod
    async def lookup_itad_ids(cls, arg_seqAppids: Sequence[int]) -> tuple[dict[int, dict], dict]:
        """
        Realiza lookup de IDs na API do IsThereAnyDeal (ITAD) de forma assíncrona.
        
        Parâmetros:
        - arg_seqAppids (Sequence[int]): Uma sequência de appids dos jogos.
        
        Retorna:
        - tuple: Uma tupla contendo:
            - var_dictResults (dict): Um dicionário mapeando appids para seus dados do ITAD.
            - var_dictStats (dict): Um dicionário com estatísticas do processamento.
        """
        logger = logging.getLogger("itad.lookup")
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
            cls._var_intProcessados = 0

            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> tuple[int, dict | None]:
                """
                Worker assíncrono para buscar dados ITAD de um único appid.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.
                
                Retorna:
                - tuple: (appid, dados do ITAD ou None se não encontrado)
                """
                """Retorno JSON
                {
                    "found": true|false,
                    "game": {
                        "id": String contendo o ID dentro de ITAD. "018d937f-1ad7-728a-9596-0d9ab5464ef5",
                        "slug": String contendo o nome do jogo com espaço transformados em "-". "enemy-territory-quake-wars",
                        "title": String contendo o nome do jogo. "Enemy Territory: Quake Wars",
                        "type": String contendo o tipo do jogo (normalmente "game"). "game"|null,
                        "mature": Boolean indicando se o jogo é adulto. true|false,
                        "assets": {
                            "boxart": URL da imagem boxart do jogo (normalmente 600x900). "https://assets.isthereanydeal.com/018d937e-ffaf-736e-9842-0215cb593b35/boxart.jpg?t=1761616309",
                            "banner145": URL da imagem banner do jogo (normalmente 145x50). "https://assets.isthereanydeal.com/018d937e-ffaf-736e-9842-0215cb593b35/banner145.jpg?t=1761616309",
                            "banner300": URL da imagem banner do jogo (normalmente 300x100). "https://assets.isthereanydeal.com/018d937e-ffaf-736e-9842-0215cb593b35/banner300.jpg?t=1761616309",
                            "banner400": URL da imagem banner do jogo (normalmente 400x150). "https://assets.isthereanydeal.com/018d937e-ffaf-736e-9842-0215cb593b35/banner400.jpg?t=1761616309",
                            "banner600": URL da imagem banner do jogo (normalmente 600x225). "https://assets.isthereanydeal.com/018d937e-ffaf-736e-9842-0215cb593b35/banner600.jpg?t=1761616309"
                        }
                }
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
                                    cls._var_intProcessados += 1
                                    return (arg_intAppid, var_dictGame)
                            elif var_dictData and var_dictData.get("found") is False:
                                # Jogo não encontrado no ITAD
                                var_intNaoEncontrados += 1
                                return (arg_intAppid, "AUSENTE")
                            else:
                                # Resposta inesperada
                                var_intErrosOutros += 1
                                return (arg_intAppid, None)
                            
                    except aiohttp.ClientError as e_http:
                        if hasattr(e_http, 'status'):
                            if e_http.status == 403:
                                var_intErrosForbidden += 1
                            elif e_http.status == 429:
                                var_dictRetryData = await cls._retry_with_backoff(arg_clientSession, arg_intAppid, arg_strTipo='lookup_ids')  # Retry para 429
                                if var_dictRetryData:
                                    # Sucesso no retry - processa os dados
                                    if var_dictRetryData and var_dictRetryData.get("found"):
                                        var_dictGame = var_dictRetryData.get("game", {})
                                        if isinstance(var_dictGame, dict):
                                            cls._var_intProcessados += 1
                                            return (arg_intAppid, var_dictGame)
                                    elif var_dictRetryData and var_dictRetryData.get("found") is False:
                                        var_intNaoEncontrados += 1
                                        return (arg_intAppid, "AUSENTE")
                                # Falhou mesmo com retry
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
                logger.debug(
                    "ITAD LOOKUP async start: "
                    f"tasks={len(var_listTasks)} conc={var_intAsyncConcurrency}"
                )
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.debug("ITAD LOOKUP async done")
            
            # Filtra os resultados válidos e os retorna
            var_dictResults: dict[int, dict] = {}
            for var_tupleResult in var_listOut:
                if isinstance(var_tupleResult, tuple) and len(var_tupleResult) == 2:
                    var_intAppid, var_dictData = var_tupleResult
                    if var_dictData is not None and var_dictData != "AUSENTE":
                        var_dictResults[var_intAppid] = var_dictData
                    elif var_dictData == "AUSENTE":
                        var_dictResults[var_intAppid] = "AUSENTE"
            
            var_intFalha = len(arg_seqAppids) - len(var_dictResults)
            logger.info(
                "ITAD LOOKUP async resumo: "
                f"sucesso={len(var_dictResults)-var_intNaoEncontrados} ausente={var_intNaoEncontrados} "
                f"falha={var_intFalha} http429={var_intErrosTooManyRequests} timeout={var_intErrosTimeout}"
            )
            logger.debug(
                "ITAD LOOKUP async detalhes: "
                f"http={var_intErrosHTTP} (403={var_intErrosForbidden}, 429={var_intErrosTooManyRequests}) "
                f"timeout={var_intErrosTimeout} outros={var_intErrosOutros}"
            )
            var_dictEstatisticas = {
                "total": len(arg_seqAppids),
                "sucessos": len(var_dictResults)-var_intNaoEncontrados,
                "erros": var_intFalha,
                "erros_http": var_intErrosHTTP,
                "erros_timeout": var_intErrosTimeout,
                "ausentes": var_intNaoEncontrados,
                "erros_outros": var_intErrosOutros
            }
            return [var_dictResults, var_dictEstatisticas]  # Retorna também as estatísticas para ajuste de batch
        
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
        logger = logging.getLogger("itad.history")
        var_listBatchTotal = []
        for var_seqItadPlain in arg_seqItadPlain:
            if var_seqItadPlain is not None and var_seqItadPlain != "" and var_seqItadPlain != "AUSENTE":
                var_listBatchTotal.append(var_seqItadPlain)

        var_dictConfigAPI = Settings.steam_api_itad()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        cls._var_intDelayBetweenBatches = var_dictConfigAPI.get("DelayBetweenBatches", var_dictConfigAPI.get("Delay", 120))
        cls._var_intRetryBackoffBase = var_dictConfigAPI.get("RetryBackoffBase", cls._var_intDelayBetweenBatches)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTotalItems = len(var_listBatchTotal)
        if var_intTotalItems == 0:
            logger.info("Nenhum ID ITAD válido para buscar histórico de preços.")
            return {}
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        var_intBatchSizeMax = int(os.getenv("STEAM_BATCH_SIZE_ITAD_MAX", 1000))
        var_intBatchSizeMin = int(os.getenv("STEAM_BATCH_SIZE_ITAD_MIN", 100))

        logger.info(
            "ITAD HISTÓRICO (batches): "
            f"Total itens={var_intTotalItems:,} Tamanho batch={var_intBatchSize:,} Total batches={var_intTotalBatches} (estimado) "
            f"concorrência={var_intAsyncConcurrency} anos={arg_intAnos} delayBatch={cls._var_intDelayBetweenBatches}s "
            f"retryBase={cls._var_intRetryBackoffBase}s"
        )
        
        var_dictAllResults = {}
        var_intTotalSucessos = 0
        var_intTotalAusentes = 0
        var_intTotalErros = 0
        var_intCurrentIndex = 0
        var_intBatchNum = 0

        while var_intCurrentIndex < var_intTotalItems:
            var_intStart = var_intCurrentIndex
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = var_listBatchTotal[var_intStart:var_intEnd]
            var_intBatchNum += 1

            logger.info(
                "ITAD HISTÓRICO batch "
                f"{var_intBatchNum}/{var_intTotalBatches}: itens {var_intStart + 1}-{var_intEnd} "
                f"(n={len(var_listBatch)})"
            )
            
            # Processa o batch atual
            var_dictBatchResults, var_dictBatchStats = await cls.fetch_price_history_bulk(var_listBatch, arg_intAnos)
            var_dictAllResults.update(var_dictBatchResults)
            
            # Usa estatísticas retornadas para ajuste dinâmico do batch size
            var_intAusentes = var_dictBatchStats["ausentes"]
            var_intSucesso = var_dictBatchStats["sucessos"]
            var_intErrosReais = var_dictBatchStats["erros_http"] + var_dictBatchStats["erros_timeout"] + var_dictBatchStats["erros_outros"]
            var_intTotal = var_dictBatchStats["total"]
            var_intTotalProcessavel = var_intTotal - var_intAusentes
            var_floatTaxaSucesso = var_intSucesso / var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1

            var_intTotalSucessos += var_intSucesso
            var_intTotalAusentes += var_intAusentes
            var_intTotalErros += var_intErrosReais

            logger.info(
                "ITAD HISTÓRICO batch "
                f"{var_intBatchNum}/{var_intTotalBatches} resultado: "
                f"sucesso={var_intSucesso} ausente={var_intAusentes} erros={var_intErrosReais} "
                f"taxa={var_floatTaxaSucesso:.1%}"
            )
            PostgreSQLITAD.inserir_dados_itad_raw_historico_preco_bulk(var_dictBatchResults)
            
            # Ajusta batch size dinamicamente
            if var_floatTaxaSucesso > 0.95:  # >95% sucesso - aumenta batch
                var_intNovoSize = min(int(var_intBatchSize * 1.2), var_intBatchSizeMax)
                if var_intNovoSize != var_intBatchSize:
                    logger.debug(
                        "ITAD HISTÓRICO ajuste batchSize: "
                        f"{var_intBatchSize} → {var_intNovoSize} (taxa={var_floatTaxaSucesso:.1%})"
                    )
                    var_intBatchSize = var_intNovoSize
            elif var_floatTaxaSucesso < 0.70:  # <70% sucesso - reduz batch
                var_intNovoSize = max(int(var_intBatchSize * 0.5), var_intBatchSizeMin)
                if var_intNovoSize != var_intBatchSize:
                    logger.warning(
                        "ITAD HISTÓRICO ajuste batchSize: "
                        f"{var_intBatchSize} → {var_intNovoSize} (taxa={var_floatTaxaSucesso:.1%})"
                    )
                    var_intBatchSize = var_intNovoSize

            var_intCurrentIndex = var_intEnd

        logger.info(
            "ITAD HISTÓRICO concluído: "
            f"sucesso={var_intTotalSucessos:,}/{var_intTotalItems:,} ({var_intTotalSucessos/var_intTotalItems:.2%}) "
            f"ausente={var_intTotalAusentes:,} erros={var_intTotalErros:,}"
        )
        
        return var_dictAllResults
    
    # ------------------- Async ITAD price history bulk -------------------
    @classmethod
    async def fetch_price_history_bulk(cls, arg_seqItadPlain: Sequence[str], arg_intAnos: int = 5) -> tuple[dict, dict]:
        """
        Busca o histórico de preços de múltiplos jogos na API do IsThereAnyDeal (ITAD) de forma assíncrona.

        Parâmetros:
        - arg_seqItadPlain (Sequence[str]): Uma sequência de identificadores "plain" dos jogos no ITAD.
        - arg_intAnos (int): O número de anos para buscar o histórico.

        Retorna:
        - tuple: Uma tupla contendo:
            - var_dictResults (dict): Um dicionário mapeando cada plain para seu histórico de preços.
            - var_dictEstatisticas (dict): Um dicionário com estatísticas do processamento.
        """
        logger = logging.getLogger("itad.history")
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
            cls._var_intProcessados = 0

            async def worker(arg_clientSession: aiohttp.ClientSession, arg_strItadPlain: str) -> dict | None:
                """
                Worker assíncrono para buscar o histórico de preços de um único jogo.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_strItadPlain (str): O identificador "plain" do jogo no ITAD.
                
                Retorna:
                - var_dictData (dict | None): Um dicionário com o histórico de preços ou None se não encontrado.
                """
                """Retorno JSON
                [
                    {
                        "timestamp": String contendo a data e hora do registro de preço. "2026-02-21T19:16:20+01:00",
                        "shop": {
                            "id": String contendo o ID da loja. "61",
                            "name": String contendo o nome da loja. "Steam",
                        },
                        "deal": {
                            "price": {
                                "amount": Float contendo o preço atual do jogo. 65.96,
                                "amountInt": Inteiro contendo o preço atual do jogo em centavos. 6596,
                                "currency": String contendo a moeda do preço. "USD"|"BRL",
                            },
                            "regular": {
                                "amount": Float contendo o preço regular do jogo. 199.9,
                                "amountInt": Inteiro contendo o preço regular do jogo em centavos. 19990,
                                "currency": String contendo a moeda do preço regular. "USD"|"BRL",
                            },
                            "cut": Inteiro contendo a porcentagem de desconto. 67,
                        }
                    }, {...}
                ]
                """

                nonlocal var_intErrosHTTP, var_intErrosForbidden, var_intErrosTooManyRequests, var_intErrosTimeout, var_intErrosOutros, var_intAusentes
                
                async with var_semSemaphore:
                    # Pequena espera para evitar throttling
                    await asyncio.sleep(random.random() * 0.2)
                    if not arg_strItadPlain:
                        var_intAusentes += 1
                        return None
                    
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
                                cls._var_intProcessados += 1
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
                                var_listDataRetry = await cls._retry_with_backoff(arg_clientSession, arg_strItadPlain, arg_strTipo='preco', arg_strSince=var_strSince)  # Retry para 429
                                if var_listDataRetry:
                                    cls._var_intProcessados += 1
                                    return var_listDataRetry
                                var_intErrosTooManyRequests += 1
                        return None
                    except asyncio.TimeoutError:
                        # Captura erro de timeout.
                        var_intErrosTimeout += 1
                        return None
                    except Exception as err:
                        # Captura outros erros não classificados.
                        var_intErrosOutros += 1
                        logger.error(f"Erro não classificado: {err}")
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
                logger.debug(
                    "ITAD HISTÓRICO async start: "
                    f"tasks={len(var_listTasks)} conc={var_intAsyncConcurrency}"
                )
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.debug("ITAD HISTÓRICO async done")
            
            # Filtra os resultados válidos e os retorna
            var_dictResults = {}
            for idx, var_listOutData in enumerate(var_listOut):
                if isinstance(var_listOutData, list) and var_listOutData is not None: 
                    var_dictResults[arg_seqItadPlain[idx]] = var_listOutData
            
            var_intFalha = len(arg_seqItadPlain) - len(var_dictResults)
            logger.info(
                "ITAD HISTÓRICO async resumo: "
                f"sucesso={len(var_dictResults)} ausente={var_intAusentes} falha={var_intFalha} "
                f"http429={var_intErrosTooManyRequests} timeout={var_intErrosTimeout}"
            )
            logger.debug(
                "ITAD HISTÓRICO async detalhes: "
                f"http={var_intErrosHTTP} (403={var_intErrosForbidden}, 429={var_intErrosTooManyRequests}) "
                f"timeout={var_intErrosTimeout} outros={var_intErrosOutros}"
            )

            var_dictEstatisticas = {
                "total": len(arg_seqItadPlain),
                "sucessos": len(var_dictResults),
                "erros": var_intFalha,
                "erros_http": var_intErrosHTTP,
                "erros_timeout": var_intErrosTimeout,
                "ausentes": var_intAusentes,
                "erros_outros": var_intErrosOutros
            }

            return var_dictResults, var_dictEstatisticas
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar histórico ITAD em bulk: {e}")
            raise RuntimeError(f"Falha ao buscar histórico ITAD em bulk: {e}")

    # ------------------- Método auxiliar para retry -------------------
    @classmethod
    async def _retry_with_backoff(cls, arg_clientSession: aiohttp.ClientSession, arg_anyId: int | str, arg_strTipo: str = 'lookup_ids', arg_intMaxRetries: int = 3, arg_strSince: str = None) -> dict | None:
        """
        Retry com backoff exponencial para erros 429 (Too Many Requests).
        
        Parâmetros:
        - arg_clientSession (aiohttp.ClientSession): Sessão HTTP reutilizável.
        - arg_anyId (int or str): ID do jogo (pode ser AppID ou ITAD Plain).
        - arg_strTipo (str): Tipo de dados sendo buscado (preço ou lookup_ids) para logs mais claros.
        - arg_intMaxRetries (int): Número máximo de tentativas.
        - arg_strSince (str): Data mínima para histórico de preços.
        Retorna:
        - dict | None: Dados do jogo ou None se falhar.
        """
        if arg_strTipo == "preco":
            logger = logging.getLogger("itad.history")
        else:
            logger = logging.getLogger("itad.lookup")
        if arg_strTipo == 'preco':
            url = ITAD_HISTORY_URL
            var_dictParams = {
                        "key": Settings._var_strItadApiKey,
                        "id": arg_anyId,
                        "shops": "61",
                        "country": "BR",
                        "since": arg_strSince,
                    }
            
        elif arg_strTipo == 'lookup_ids':
            url = ITAD_LOOKUP_IDS_URL
            var_dictParams = {
                "key": Settings._var_strItadApiKey,
                "appid": arg_anyId,
            }

        def _parse_retry_after_seconds(arg_resp: aiohttp.ClientResponse) -> int | None:
            var_strRetryAfter = arg_resp.headers.get("Retry-After")
            if not var_strRetryAfter:
                return None

            var_strRetryAfter = var_strRetryAfter.strip()

            try:
                var_floatSeconds = float(var_strRetryAfter)
                if var_floatSeconds < 0:
                    return None
                return max(1, int(var_floatSeconds))
            except ValueError:
                pass

            try:
                var_dateRetryAt = parsedate_to_datetime(var_strRetryAfter)
                if var_dateRetryAt.tzinfo is None:
                    var_dateRetryAt = var_dateRetryAt.replace(tzinfo=timezone.utc)
                var_dateNow = datetime.now(timezone.utc)
                var_intSeconds = int((var_dateRetryAt - var_dateNow).total_seconds())
                return max(1, var_intSeconds)
            except Exception:
                return None

        for var_intAttempt in range(arg_intMaxRetries):
            try:
                async with arg_clientSession.get(url, params=var_dictParams) as resp:
                    if resp.status == 429:
                        var_intWaitTime = _parse_retry_after_seconds(resp)
                        if var_intWaitTime is None:
                            var_intWaitTime = (2 ** var_intAttempt) * cls._var_intRetryBackoffBase

                        logger.warning(
                            f"ITAD retry ({arg_strTipo}) id={arg_anyId} status=429 "
                            f"tentativa={var_intAttempt+1}/{arg_intMaxRetries} espera={var_intWaitTime}s"
                        )
                        await asyncio.sleep(var_intWaitTime)
                        continue
                    if resp.status == 502:
                        var_intWaitTime = (2 ** var_intAttempt) * cls._var_intRetryBackoffBase
                        logger.warning(
                            f"ITAD retry ({arg_strTipo}) id={arg_anyId} status=502 "
                            f"tentativa={var_intAttempt+1}/{arg_intMaxRetries} espera={var_intWaitTime}s"
                        )
                        await asyncio.sleep(var_intWaitTime)
                        continue
                    elif resp.status == 200:
                        return await resp.json()
                    else:
                        logger.debug(f"ITAD resposta id={arg_anyId} status={resp.status} tentativa={var_intAttempt+1}")
                        return None
            except Exception as e:
                if var_intAttempt == arg_intMaxRetries - 1:
                    logger.error(f"ID {arg_anyId}: Falha após {arg_intMaxRetries} tentativas - {e}")
                    return None
                await asyncio.sleep(5)  # Espera 5s entre tentativas com erro
        return None