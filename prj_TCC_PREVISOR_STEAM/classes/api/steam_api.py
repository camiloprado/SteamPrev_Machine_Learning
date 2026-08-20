from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from typing import Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import asyncio
import random
import logging
import aiohttp
import traceback
from dotenv import load_dotenv

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
    _var_intDelayBetweenBatches = 0
    _var_intRetryBackoffBase = 0
    _var_intProcessados = 0

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
        logger = logging.getLogger("steam.details")
        var_dictConfigAPI = Settings.steam_api_details()
        var_intBatchSizeInicial = var_dictConfigAPI.get("BatchSize", 50)
        var_intBatchSizeMin = var_dictConfigAPI.get("BatchSizeMin", 10)
        var_intBatchSizeMax = var_dictConfigAPI.get("BatchSizeMax", 200)
        var_intBatchSize = var_intBatchSizeInicial
        cls._var_intDelayBetweenBatches = var_dictConfigAPI.get("DelayBetweenBatches", var_dictConfigAPI.get("Delay", 180))
        cls._var_intRetryBackoffBase = var_dictConfigAPI.get("RetryBackoffBase", cls._var_intDelayBetweenBatches)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTentativaMaxima = var_dictConfigAPI.get("max_tentativas", 3)
        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatchesEstimado = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        logger.info(
            "STEAM DETALHES (batches): "
            f"Total itens={var_intTotalItems:,} Tamanho batch={var_intBatchSize:,} Total batches={var_intTotalBatchesEstimado} (estimado) "
            f"Concorrência={var_intAsyncConcurrency} delayBatch={cls._var_intDelayBetweenBatches}s "
            f"Tempo estimado={(var_intTotalBatchesEstimado * cls._var_intDelayBetweenBatches)/60:.1f}m"
        )
        
        var_intCurrentIndex = 0
        var_intBatchNum = 0
        
        while var_intCurrentIndex < var_intTotalItems:
            var_intStart = var_intCurrentIndex
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]
            var_intBatchNum += 1
            
            logger.info(
                "DETALHES batch "
                f"{var_intBatchNum}/{var_intTotalBatchesEstimado}: itens {var_intStart + 1}-{var_intEnd} "
                f"(n={len(var_listBatch)})"
            )
            
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
            logger.info(
                "DETALHES batch "
                f"{var_intBatchNum}/{var_intTotalBatchesEstimado} resultado: "
                f"sucesso={len(var_listDetails)} ausente={var_intAusentes} erros={var_intErrosReais} "
                f"taxa={var_floatTaxaSucesso:.1%}"
            )

            # Ajusta batch size dinamicamente
            if var_floatTaxaSucesso > 0.95:  # >95% sucesso - aumenta batch
                var_intNovoSize = min(int(var_intBatchSize * 1.2), var_intBatchSizeMax)
                if var_intNovoSize != var_intBatchSize:
                    logger.debug(
                        "DETALHES ajuste batchSize: "
                        f"{var_intBatchSize} → {var_intNovoSize} (taxa={var_floatTaxaSucesso:.1%})"
                    )
                    var_intBatchSize = var_intNovoSize
            elif var_floatTaxaSucesso < 0.70:  # <70% sucesso - reduz batch
                var_intNovoSize = max(int(var_intBatchSize * 0.5), var_intBatchSizeMin)
                if var_intNovoSize != var_intBatchSize:
                    logger.warning(
                        "DETALHES ajuste batchSize: "
                        f"{var_intBatchSize} → {var_intNovoSize} (taxa={var_floatTaxaSucesso:.1%})"
                    )
                    var_intBatchSize = var_intNovoSize
            
            # Insere os dados no PostgreSQL
            if var_listDetails:
                PostgreSQLSteam.inserir_dadosSteamRaw_Bulk(arg_listDados=var_listDetails)
                logger.debug(
                    "DETALHES inseridos no PostgreSQL: "
                    f"registros={len(var_listDetails)}"
                )
            else:
                logger.warning("Nenhum dado válido para inserir neste batch.")

            # Avança o índice para o próximo batch
            var_intCurrentIndex = var_intEnd
            
            # Aguarda entre batches (exceto no último)
            if var_intCurrentIndex < var_intTotalItems:
                logger.debug(
                    "DETALHES progresso: "
                    f"{var_intCurrentIndex:,}/{var_intTotalItems:,} ({var_intCurrentIndex/var_intTotalItems:.1%})"
                )
                
        logger.info(
            "STEAM DETALHES concluído: "
            f"batches={var_intBatchNum} itens={var_intCurrentIndex:,}/{var_intTotalItems:,}"
        )

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
        logger = logging.getLogger(f"steam.{arg_strTipo}")
        if arg_strTipo == 'detalhes':
            url = f"{STEAM_DETAILS_URL}?appids={arg_intAppid}"
        elif arg_strTipo == 'reviews':
            url = STEAM_REVIEWS_URL.format(appid=arg_intAppid)

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
                async with arg_clientSession.get(url) as resp:
                    if resp.status == 429:
                        var_intWaitTime = _parse_retry_after_seconds(resp)
                        if var_intWaitTime is None:
                            var_intWaitTime = (2 ** var_intAttempt) * cls._var_intRetryBackoffBase
                        logger.warning(
                            f"STEAM retry ({arg_strTipo}) id={arg_intAppid} status=429 "
                            f"tentativa={var_intAttempt+1}/{arg_intMaxRetries} espera={var_intWaitTime}s"
                        )
                        await asyncio.sleep(var_intWaitTime)
                        continue
                    if resp.status == 502:
                        var_intWaitTime = (2 ** var_intAttempt) * cls._var_intRetryBackoffBase
                        logger.warning(
                            f"STEAM retry ({arg_strTipo}) id={arg_intAppid} status=502 "
                            f"tentativa={var_intAttempt+1}/{arg_intMaxRetries} espera={var_intWaitTime}s"
                        )
                        await asyncio.sleep(var_intWaitTime)
                        continue
                    elif resp.status == 200:
                        return await resp.json()
                    else:
                        logger.debug(
                            f"STEAM resposta id={arg_intAppid} status={resp.status} "
                            f"tentativa={var_intAttempt+1}"
                        )
                        return None
            except Exception as e:
                if var_intAttempt == arg_intMaxRetries - 1:
                    logger.error(f"STEAM retry id={arg_intAppid}: Falha após {arg_intMaxRetries} tentativas - {e}")
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
        logger = logging.getLogger("steam.details")
        try:
            load_dotenv()
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
            cls._var_intProcessados = 0

            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> dict | str | None:
                """
                Worker assíncrono para buscar detalhes de um único appid.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.
                
                Retorna:
                - var_dictDetails (dict | None): Um dicionário com os detalhes do jogo ou None se não encontrado.
                """
                """Retorno JSON:
                {
                    appid: {
                        "success": True|False,
                        "data": { 
                            "type": "game"|"advertising"|"dlc"|"demo"|"episode"|"hardware"|"mod"|"music"|"series"|"video",
                            "name": "Nome do Jogo",
                            "steam_appid": 12345,
                            "required_age": 0,
                            "is_free": True|False,
                            "detailed_description": "Descrição detalhada",
                            "about_the_game": "Sobre o jogo",
                            "short_description": "Descrição curta",
                            "supported_languages": String contendo as linguagens (Vem com elementos HTML). ""Inglês<strong>*</strong>, Francês<strong>*</strong>, Alemão<strong>*</strong>, ...",
                            "header_image": "URL da imagem",
                            "capsule_image": "URL da imagem",
                            "capsule_imagev5": "URL da imagem",
                            "website": "URL do site"|null,
                            "pc_requirements": { 
                                "minimum": String contendo as recomendações (Vem com elementos HTML), 
                                "recommended": String contendo as recomendações (Vem com elementos HTML)
                            },
                            "mac_requirements": { 
                                "minimum": String contendo as recomendações (Vem com elementos HTML), 
                                "recommended": String contendo as recomendações (Vem com elementos HTML) 
                            },
                            "linux_requirements": { 
                                "minimum": String contendo as recomendações (Vem com elementos HTML), 
                                "recommended": String contendo as recomendações (Vem com elementos HTML) 
                            },
                            "developers": Lista com nomes dos desenvolvedores. ["Dev1", "Dev2"],
                            "publishers": Lista com nomes das distribuidoras. ["Publisher1", "Publisher2"],
                            "price_overview": { 
                                "currency": "USD"|"BRL"|..., 
                                "initial": Valor inteiro (Necessario dividir por 100) - 2069, 
                                "final": 2069, 
                                "discount_percent": 0,
                                "initial_formatted": "",
                                "final_formatted": "R$20,69"
                            },
                            "packages": Lista de IDs interligadas ao jogos (DLCs). [12345, 67890],
                            "package_groups": [
                                {
                                    "name": "Nome do pacote",
                                    "title": "Título do pacote",
                                    "description": "Descrição do pacote",
                                    "selection_text": "Texto de seleção do pacote",
                                    "save_text": "Texto de economia do pacote",
                                    "display_type": 0,
                                    "is_recurring_subscription": "false",
                                    "subs": [
                                        {
                                            "packageid": 12345,
                                            "percent_savings_text": "0%",
                                            "percent_savings": 0,
                                            "option_text": "Jogo base",
                                            "option_description": "",
                                            "can_get_free_license": "0",
                                            "is_free_license": False,
                                            "price_in_cents_with_discount": 2069
                                        }
                                    ]
                            ],
                            "platforms": { 
                                "windows": True|False, 
                                "mac": True|False, 
                                "linux": True|False 
                            },
                            "metacritic": { 
                                "score": 85, 
                                "url": "URL do Metacritic" 
                            },
                            "categories": Lista com ID e descrição das categorias. 
                            [ 
                                { 
                                    "id": 1, 
                                    "description": "Categoria 1" 
                                }, 
                                {
                                    "id": 2,
                                    "description": "Categoria 2"
                                }
                            ],
                            "genres": Lista com ID e descrição dos gêneros.
                            [
                                { 
                                    "id": 1, 
                                    "description": "Gênero 1" 
                                }, 
                                {
                                    "id": 2,
                                    "description": "Gênero 2"
                                }
                            ],
                            "screenshots": Lista com ID e URLs das screenshots.
                            [ 
                                { 
                                    "id": 1, 
                                    "path_thumbnail": "URL da thumbnail", 
                                    "path_full": "URL da imagem completa" 
                                }, 
                                ... 
                            ],
                            "movies": Lista com ID e URLs dos trailers.
                            [
                                { 
                                    "id": 1, 
                                    "name": "Trailer 1", 
                                    "thumbnail": "URL da thumbnail", 
                                    "dash_av1": "URL do vídeo em AV1",
                                    "dash_h264": "URL do vídeo em H264",
                                    "hls_h264": "URL do vídeo em HLS H264",
                                    "highlight": True|False
                                }, 
                                ...
                            ],
                            "achievements": {
                                "total": 50,
                            },
                            "recommendations": { "total": 1234 },
                            "release_date": { 
                                "coming_soon": True|False, 
                                "date": "1/jan./2020" 
                            },
                            "support_info": { 
                                "url": "URL de suporte", 
                                "email": "Email de suporte" 
                            },
                            "background": "URL da imagem de fundo"
                            "background_raw": "URL da imagem de fundo sem redimensionamento",
                            "content_descriptors": {
                                "ids": Lista de IDs dos content descriptors. [1, 2, 3],
                                "notes": String com notas sobre os content descriptors. "Violência, Linguagem Forte, ...",
                            }
                            "ratings": {
                                "dejus": {
                                    "rating_generated": "1",
                                    "rating"; "l",
                                    "required_age": "0",
                                    "banned": "0",
                                    "use_age_gate": "0",
                                    "descriptors": ""
                                },
                                "steam_germany": {...}
                            }
                            
                        } ou {} se success=False
                    }
                }
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
                                cls._var_intProcessados += 1
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
                                        cls._var_intProcessados += 1
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
                                logger.error(f"Erro:\n{e_http.status} - {e_http.message if hasattr(e_http, 'message') else str(e_http)}")
                        return None
                    except asyncio.TimeoutError:
                        # Captura erro de timeout
                        var_intErrosTimeout += 1
                        return None
                    except Exception as e:
                        # Captura outros erros não classificados.
                        logger.error(f"Erro não classificado para AppID {arg_intAppid}: {e}")
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
                logger.debug(
                    "DETALHES async start: "
                    f"tasks={len(var_listTasks)} conc={var_intAsyncConcurrency}"
                )
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.debug("DETALHES async done")

            # Filtra a lista de forma segura
            var_listOut = [item for item in var_listOut if item is not None]
            
            var_intTotal = len(arg_seqAppids)
            var_intTotal = 1 if var_intTotal == 0 else var_intTotal  # Evita divisão por zero
            var_intAusentes = sum(1 for item in var_listOut if item.get("data") == "AUSENTE")
            var_intSucesso = len(var_listOut) - var_intAusentes
            var_intErrosReais = var_intTotal - var_intSucesso - var_intAusentes
            var_intTotalProcessavel = var_intTotal - var_intAusentes
            var_floatTaxaSucesso = var_intSucesso / var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1

            logger.info(
                "DETALHES async resumo: "
                f"sucesso={var_intSucesso} ausente={var_intAusentes} erros={var_intErrosReais} "
                f"taxa={var_floatTaxaSucesso:.1%} http429={var_intErrosTooManyRequests} "
                f"timeout={var_intErrosTimeout}"
            )
            logger.debug(
                "DETALHES async detalhes: "
                f"http={var_intErrosHTTP} (403={var_intErrosForbidden}, 429={var_intErrosTooManyRequests}) "
                f"timeout={var_intErrosTimeout} outros={var_intErrosOutros}"
            )
            
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
        logger = logging.getLogger("steam.reviews")
        var_dictConfigAPI = Settings.steam_api_reviews()
        var_intBatchSize = var_dictConfigAPI.get("BatchSize", 200)
        cls._var_intDelayBetweenBatches = var_dictConfigAPI.get("DelayBetweenBatches", var_dictConfigAPI.get("Delay", 120))
        cls._var_intRetryBackoffBase = var_dictConfigAPI.get("RetryBackoffBase", cls._var_intDelayBetweenBatches)
        var_intAsyncConcurrency = var_dictConfigAPI.get("Concurrency", 1)
        var_intTotalItems = len(arg_seqAppids)
        var_intTotalBatches = (var_intTotalItems + var_intBatchSize - 1) // var_intBatchSize
        var_intTentativaMaxima = var_dictConfigAPI.get("max_tentativas", 3)

        logger.info(
            "STEAM REVIEWS (batches): "
            f"Total itens={var_intTotalItems:,} Tamanho batch={var_intBatchSize:,} Total batches={var_intTotalBatches} (estimado)"
            f"Concorrência={var_intAsyncConcurrency} delayBatch={cls._var_intDelayBetweenBatches}s "
            f"Tempo estimado={(var_intTotalBatches * cls._var_intDelayBetweenBatches)/60:.1f}m"
        )
        
        for var_intBatchNum in range(var_intTotalBatches):
            var_intStart = var_intBatchNum * var_intBatchSize
            var_intEnd = min(var_intStart + var_intBatchSize, var_intTotalItems)
            var_listBatch = arg_seqAppids[var_intStart:var_intEnd]

            logger.info(
                "REVIEWS batch "
                f"{var_intBatchNum + 1}/{var_intTotalBatches}: itens {var_intStart + 1}-{var_intEnd} "
                f"(n={len(var_listBatch)})"
            )

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
            logger.info(
                "REVIEWS batch "
                f"{var_intBatchNum + 1}/{var_intTotalBatches} resultado: "
                f"sucesso={len(var_listReviews)} ausente={var_intAusentesReviews} erros={var_intErrosReais}"
            )

            # Insere os dados no PostgreSQL
            if var_listReviews:
                PostgreSQLSteam.inserir_dadosSteamRaw_Bulk(arg_listDados=var_listReviews)
                logger.debug(
                    "REVIEWS inseridos no PostgreSQL: "
                    f"registros={len(var_listReviews)}"
                )
            else:
                logger.warning("Nenhum dado válido para inserir neste batch.")

        logger.info(f"STEAM REVIEWS concluído: itens={var_intTotalItems:,}")
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
        logger = logging.getLogger("steam.reviews")
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
            cls._var_intProcessados = 0

            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> dict | None:
                """
                Worker assíncrono para buscar o resumo de reviews de um único appid.

                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.

                Retorna:
                - var_dictSummary (dict | None): Um dicionário com o resumo das reviews ou None se não encontrado.
                """
                """Retorno JSON:
                {
                    "success": 1|2,
                    "query_summary": {
                        "num_reviews": 1234,
                        "review_score": 8,
                        "review_score_desc": "Muito Positivas",
                        "total_positive": 1000,
                        "total_negative": 234,
                        "total_reviews": 1234
                    },
                    "reviews": [
                        {
                            recommendationid: "1234567890",
                            "author": {
                                "steamid": "76561198000000000",
                                "personaname": "Nome do Usuário",
                                "persona_status": "offline",
                                "profileurl": "URL do perfil",
                                "num_games_owned": 10,
                                "num_reviews": 5,
                                "playtime_forever": 50,
                                "playtime_last_two_weeks": 5,
                                "playtime_at_review": 45,
                                "last_played": 1609459200,
                                "avatar": "URL do avatar",
                            },
                            "language": "brazilian",
                            "appid": 12345,
                            "review": "Texto da review",
                            "timestamp_created": 1609459200,
                            "timestamp_updated": 1609459200,
                            "voted_up": True|False,
                            "votes_up": 100,
                            "votes_funny": 10,
                            "weighted_vote_score": "0.95",
                            "comment_count": 5,
                            "steam_purchase": True|False,
                            "received_for_free": True|False,
                            "refounded": True|False,
                            "written_during_early_access": True|False,
                            "primarily_steam_deck": True|False,
                            "app_release_date": "973065600",
                            "reactions": [],
                            "csgo_disclaimer": True|False
                        }

                }
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
                                    cls._var_intProcessados += 1
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
                                logger.debug(
                                    f"REVIEWS 429 detectado id={arg_intAppid}, iniciando retry"
                                )
                                var_dictRetryData = await cls._retry_with_backoff(arg_clientSession, arg_intAppid, arg_intMaxRetries=3, arg_strTipo='reviews')
                                if var_dictRetryData:
                                    # Sucesso no retry - processa os dados
                                    if var_dictRetryData.get("success") == 1:
                                        var_dictSummary = var_dictRetryData.get("query_summary", {})
                                        if isinstance(var_dictSummary, dict):
                                            var_dictSummary = dict(var_dictSummary)
                                            var_dictSummary["appid"] = arg_intAppid
                                            cls._var_intProcessados += 1
                                            logger.debug(f"REVIEWS retry sucesso id={arg_intAppid}")

                                            return var_dictSummary
                                # Falha no retry
                                logger.warning(f"REVIEWS retry falhou id={arg_intAppid}")
                                logger.debug(
                                    f"REVIEWS erro http id={arg_intAppid}: {e_http.status} - "
                                    f"{e_http.message if hasattr(e_http, 'message') else str(e_http)}"
                                )
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
                logger.debug(
                    "REVIEWS async start: "
                    f"tasks={len(var_listTasks)} conc={var_intAsyncConcurrency}"
                )
                
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
                logger.debug("REVIEWS async done")
            
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
            
            var_intTotalProcessavel = var_intTotal - var_intAusentes
            var_floatTaxaEfetiva = var_intSucesso / var_intTotalProcessavel if var_intTotalProcessavel != 0 else 1
            logger.info(
                "REVIEWS async resumo: "
                f"sucesso={var_intSucesso} ausente={var_intAusentes} erros={var_intErrosReais} "
                f"taxa={var_floatTaxaEfetiva:.1%} http429={var_intErrosTooManyRequests} "
                f"timeout={var_intErrosTimeout}"
            )
            logger.debug(
                "REVIEWS async detalhes: "
                f"http={var_intErrosHTTP} (403={var_intErrosForbidden}, 429={var_intErrosTooManyRequests}) "
                f"timeout={var_intErrosTimeout} outros={var_intErrosOutros}"
            )
            return var_listReviews
        
        except Exception as e:
            logger.critical(f"Falha crítica ao buscar reviews em bulk: {e}")
            raise RuntimeError(f"Falha ao buscar resumos de reviews: {e}")