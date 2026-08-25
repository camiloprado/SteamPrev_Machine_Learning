from datetime import datetime
import asyncio
import random
import json
import logging
import os
import aiohttp

logger = logging.getLogger("steamspy")

# Adicionar fonte alternativa:
STEAMSPY_ALL_URL = "https://steamspy.com/api.php?request=all&page={var_intPage}"  # API ativa

class SteamSpyClient:
    """
    Cliente para interagir com a SteamSpy API.
    """

    # ------------------- Fallback SteamSpy (Wrapper Síncrono) -------------------
    @classmethod
    def _fetch_from_steamspy(cls) -> list:
        """
        Wrapper síncrono para chamar a versão async _fetch_from_steamspy_async().
        Mantém compatibilidade com código existente que espera uma função síncrona.
        
        Retorna:
        - list: Lista de dicionários com appid e nome dos jogos (apenas novos/modificados).
        """
        try:
            # Verifica se já existe um loop async em execução
            asyncio.get_running_loop()
            var_boolLoopEmExecucao = True
        except RuntimeError:
            # Não há loop rodando, pode usar asyncio.run() normalmente
            var_boolLoopEmExecucao = False

        if var_boolLoopEmExecucao:
            # Dentro de um loop async já ativo, asyncio.run() não pode ser usado.
            raise RuntimeError(
                "_fetch_from_steamspy() não pode ser chamado de dentro de um loop "
                "async já em execução. Use 'await SteamSpyClient._fetch_from_steamspy_async()' "
                "diretamente nesse caso."
            )

        return asyncio.run(cls._fetch_from_steamspy_async())

    # ------------------- Fallback SteamSpy (Versão Async) -------------------
    @classmethod
    async def _fetch_from_steamspy_async(cls) -> list:
        """
        Fallback usando SteamSpy que ainda funciona.
        Otimizado com asyncio.gather() para buscar múltiplas páginas em paralelo.
        Busca apenas jogos novos/modificados comparando com cache local.
        
        Retorna:
        - list: Lista de dicionários com appid e nome dos jogos (apenas novos/modificados).

        ## Endpoint: ##
            ### all ###

            Returns all games with owners data sorted by owners. Returns 1,000 entries per page.
            * page - page number for the list (starts at 0)


            ## Return format for an app: ##

            * appid - ID da aplicação da Steam. Se for 999999, então o dado da aplicação está oculta por conta da requisição, desculpa.
            * name - Nome do jogo
            * developer - Lista de Desenvolvedores do jogo separado por virgulas
            * publisher - Lista de Distribuidores do jogo separado por virgulas
            * score_rank - Ranke de Pontuação do jogo baseado em avaliações de usuários
            * owners - Estimativa de quantas pessoas possuem o jogo.
            * average_forever - Média de tempo jogado desde Março 2009. Em minutos.
            * average_2weeks - Média de tempo jogado dentro de 2 semanas. Em minutos.
            * median_forever - Mediana de tempo jogado desde Março 2009. Em minutos.
            * median_2weeks - Mediana de tempo jogado dentro de 2 semanas. Em minutos.
            * ccu - Pico global de usuários simultâneos de ontem.
            * price - Valor do preço em US e em centavos.
            * initialprice - Valor do preço original em US e em centavos.
            * discount - Valor atual do desconto em porcentagem.
            * tags - Tags do jogos como votos dentro de uma lista de JSON.
            * languages - Lista de linguagens suportadas.
            * genre - Lista de Generos.
        """
        var_intConcorrenciaPaginas = int(os.getenv("STEAMSPY_CONCURRENCY", "10"))  # 10 páginas paralelas
        var_intMaxRetries = int(os.getenv("STEAMSPY_MAX_RETRIES", "3"))  # Tentativas para erros temporários
        var_intMaxPaginas = int(os.getenv("STEAMSPY_MAX_PAGES", "300"))
        
        # ========== Carrega dados locais para comparação ==========
        var_dictJogosLocais = {}  # {appid: name}
        var_strJsonPath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "resources", "dados", "steam_applist.json"
        )
        
        # ========== VERIFICAÇÃO DE CACHE DE 24H ==========
        if os.path.exists(var_strJsonPath):
            try:
                # Verifica idade do cache
                var_dateMTime = datetime.fromtimestamp(os.path.getmtime(var_strJsonPath))
                var_timedelta = datetime.now() - var_dateMTime
                var_floatIdadeCacheHoras = var_timedelta.total_seconds() / 3600
                
                # Se cache tem menos de 24h, usa sem buscar na API
                if var_timedelta.total_seconds() < 86400:  # 24 horas = 86400 segundos
                    logger.info(f"Cache local tem {var_floatIdadeCacheHoras:.1f}h (< 24h). Usando cache existente.")
                    with open(var_strJsonPath, "r", encoding="utf-8") as f:
                        var_listJogosCache = json.load(f)
                    logger.info(f"Cache carregado: {len(var_listJogosCache):,} jogos")
                    return var_listJogosCache
                else:
                    logger.info(f"Cache local tem {var_floatIdadeCacheHoras:.1f}h (> 24h). Buscando atualização...")
                
                # Cache desatualizado, mas carrega para comparação
                with open(var_strJsonPath, "r", encoding="utf-8") as f:
                    var_listJogosLocais = json.load(f)
                    var_dictJogosLocais = {
                        jogo["appid"]: jogo.get("name", "") 
                        for jogo in var_listJogosLocais 
                        if isinstance(jogo, dict) and "appid" in jogo
                    }
                logger.info(f"Cache local carregado: {len(var_dictJogosLocais):,} jogos existentes")
            except Exception as e:
                logger.warning(f"Erro ao carregar/verificar cache local: {e}. Buscando todos os jogos...")
                var_dictJogosLocais = {}
        else:
            logger.info("Nenhum cache local encontrado. Buscando todos os jogos do SteamSpy...")
        
        # ========== WORKER ASYNC PARA CADA PÁGINA ==========
        async def fetch_page(arg_intPage: int, arg_semSemaphore: asyncio.Semaphore, arg_clientSession: aiohttp.ClientSession) -> dict:
            """
            Worker assíncrono para buscar uma única página do SteamSpy.
            
            Parâmetros:
            - arg_intPage (int): Número da página a ser buscada.
            - arg_semSemaphore (asyncio.Semaphore): Semáforo para limitar concorrência.
            - arg_clientSession (aiohttp.ClientSession): Session HTTP reutilizável para as requisições.

            Retorna:
            - dict: {
                "page": int,
                "data": dict | None,
                "novos": int,
                "modificados": int,
                "ignorados": int,
                "status": "success" | "empty" | "rate_limit" | "error_500" | "error"
            }
            """
            async with arg_semSemaphore:
                # Delay randômico para evitar throttling
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                for var_intTentativa in range(var_intMaxRetries):
                    try:
                        var_strUrl = STEAMSPY_ALL_URL.format(var_intPage=arg_intPage)
                        
                        async with arg_clientSession.get(var_strUrl, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                            # Verifica status HTTP
                            if resp.status != 200:
                                if resp.status == 500:
                                    logger.warning(f"Página {arg_intPage}: HTTP 500 (tentativa {var_intTentativa+1}/{var_intMaxRetries})")
                                    if var_intTentativa < var_intMaxRetries - 1:
                                        await asyncio.sleep((2 ** var_intTentativa) * 2)
                                        continue
                                    return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "error_500"}
                                else:
                                    logger.warning(f"Página {arg_intPage}: Status {resp.status}")
                                    return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "error"}
                            
                            # Lê response text
                            var_strText = await resp.text()
                            
                            # Verifica se está vazio
                            if not var_strText or var_strText.strip() == "":
                                return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "empty"}
                            
                            # Tenta parsear JSON
                            try:
                                var_jsonData = json.loads(var_strText)
                            except (ValueError, json.JSONDecodeError):
                                # Verifica se é erro de rate limit (status 200 com "too many connections")
                                if "too many connections" in var_strText.lower() or "connection failed" in var_strText.lower():
                                    logger.warning(f"Página {arg_intPage}: Rate limit detectado (tentativa {var_intTentativa+1}/{var_intMaxRetries})")
                                    if var_intTentativa < var_intMaxRetries - 1:
                                        await asyncio.sleep((2 ** var_intTentativa) * 3)
                                        continue
                                    return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "rate_limit"}
                                else:
                                    logger.warning(f"Página {arg_intPage}: Conteúdo não-JSON")
                                    return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "error"}
                            
                            # Verifica se retornou dados válidos
                            if not var_jsonData or not isinstance(var_jsonData, dict) or len(var_jsonData) == 0:
                                return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "empty"}
                            
                            # SUCESSO! Compara com cache local
                            var_listPaginaData = []
                            var_intNovos = 0
                            var_intModificados = 0
                            var_intIgnorados = 0
                            
                            for var_strKey, var_dictValue in var_jsonData.items():
                                var_intAppid = int(var_strKey)
                                var_strNomeNovo = var_dictValue.get("name", "")
                                
                                # Verifica se é novo (não existe no cache)
                                if var_intAppid not in var_dictJogosLocais:
                                    var_listPaginaData.append({"appid": var_intAppid, "name": var_strNomeNovo})
                                    var_intNovos += 1
                                # Verifica se foi modificado (nome diferente)
                                elif var_dictJogosLocais[var_intAppid] != var_strNomeNovo:
                                    var_listPaginaData.append({"appid": var_intAppid, "name": var_strNomeNovo})
                                    var_intModificados += 1
                                # Jogo já existe com mesmo nome (ignora)
                                else:
                                    var_intIgnorados += 1
                            
                            return {
                                "page": arg_intPage,
                                "data": var_listPaginaData,
                                "novos": var_intNovos,
                                "modificados": var_intModificados,
                                "ignorados": var_intIgnorados,
                                "status": "success"
                            }
                            
                    except asyncio.TimeoutError:
                        if var_intTentativa < var_intMaxRetries - 1:
                            logger.warning(f"Página {arg_intPage}: Timeout (tentativa {var_intTentativa+1}/{var_intMaxRetries})")
                            await asyncio.sleep(2 ** var_intTentativa)
                            continue
                        else:
                            logger.error(f"Página {arg_intPage}: Timeout persistente")
                            return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "error"}
                    
                    except Exception as e:
                        logger.error(f"Página {arg_intPage}: Erro inesperado - {e}")
                        return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "error"}
                
                return {"page": arg_intPage, "data": None, "novos": 0, "modificados": 0, "ignorados": 0, "status": "error"}
        
        # ========== PROCESSAMENTO PARALELO COM asyncio.gather() ==========
        logger.info("=== COLETA STEAMSPY COM PARALELIZAÇÃO ===")
        logger.info(f"Páginas máximas: {var_intMaxPaginas}")
        logger.info(f"Concorrência: {var_intConcorrenciaPaginas} páginas simultâneas")
        logger.info(f"Tempo estimado: {(var_intMaxPaginas / var_intConcorrenciaPaginas) * 1.5:.1f}s")
        logger.info("========================================\n")
        
        var_semSemaphore = asyncio.Semaphore(var_intConcorrenciaPaginas)
        var_listAllData = []
        var_intJogosNovos = 0
        var_intJogosModificados = 0
        var_intJogosIgnorados = 0
        var_intPaginasErro500 = 0
        var_intPaginasRateLimit = 0
        var_intPaginasVazias = 0
        
        # Cria session HTTP reutilizável com connector configurado para Windows
        var_connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=20,
            force_close=True,
            enable_cleanup_closed=True
        )
        var_timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
        
        async with aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0"},
            connector=var_connector,
            timeout=var_timeout
        ) as var_clientSession:
            # Cria tasks para todas as páginas
            var_listTasks = [
                fetch_page(var_intPage, var_semSemaphore, var_clientSession) 
                for var_intPage in range(var_intMaxPaginas)
            ]
            
            # Executa todas em paralelo com gather
            logger.info("Iniciando coleta paralela de páginas...")
            var_listResults = await asyncio.gather(*var_listTasks, return_exceptions=True)
            
            # Processa resultados
            for var_dictResult in var_listResults:
                if isinstance(var_dictResult, Exception):
                    logger.error(f"Exceção durante gather: {var_dictResult}")
                    continue
                
                if var_dictResult["status"] == "success":
                    if var_dictResult["data"]:
                        var_listAllData.extend(var_dictResult["data"])
                        var_intJogosNovos += var_dictResult["novos"]
                        var_intJogosModificados += var_dictResult["modificados"]
                        var_intJogosIgnorados += var_dictResult["ignorados"]
                elif var_dictResult["status"] == "error_500":
                    var_intPaginasErro500 += 1
                elif var_dictResult["status"] == "rate_limit":
                    var_intPaginasRateLimit += 1
                elif var_dictResult["status"] == "empty":
                    var_intPaginasVazias += 1
                else:
                    # Conta ignored
                    var_intJogosIgnorados += var_dictResult["ignorados"]
        
        # ========== RELATÓRIO FINAL ==========
        var_intPaginasSucesso = len([r for r in var_listResults if isinstance(r, dict) and r["status"] == "success"])
        
        logger.info(f"{'='*70}")
        logger.info("COLETA STEAMSPY CONCLUÍDA")
        logger.info(f"{'='*70}")
        logger.info(f"Páginas processadas: {var_intPaginasSucesso:,} sucessos de {var_intMaxPaginas:,}")
        logger.info(f"Páginas vazias: {var_intPaginasVazias:,}")
        logger.info(f"Páginas com erro 500: {var_intPaginasErro500:,}")
        logger.info(f"Páginas com rate limit: {var_intPaginasRateLimit:,}")
        logger.info("")
        logger.info(f"Jogos NOVOS: {var_intJogosNovos:,}")
        logger.info(f"Jogos MODIFICADOS: {var_intJogosModificados:,}")
        logger.info(f"Jogos IGNORADOS (cache): {var_intJogosIgnorados:,}")
        logger.info(f"TOTAL coletado: {len(var_listAllData):,} (novos + modificados)")
        logger.info(f"{'='*70}\n")
        
        # Circuit Breaker: Se muitos erros 500, alerta
        if var_intPaginasErro500 > 50:
            logger.warning(
                f"AVISO: {var_intPaginasErro500} páginas com HTTP 500. "
                f"SteamSpy API pode estar instável."
            )
        
        return var_listAllData
