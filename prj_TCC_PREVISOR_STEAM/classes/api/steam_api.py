from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from typing import Any, Sequence
from datetime import datetime, timedelta, timezone
import asyncio, random, json, logging, os, re, aiohttp, requests

logger = logging.getLogger(__name__)

CON_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

STEAM_APP_LIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
ITAD_LOOKUP_URL = "https://api.isthereanydeal.com/lookup/id/title/v1"
ITAD_HISTORY_URL = "https://api.isthereanydeal.com/games/history/v2"


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

        # Se não tiver cache ou for forçado, baixa da Steam
        try:
            # Faz a requisição para a Steam
            var_respResponse = requests.get(STEAM_APP_LIST_URL, headers=CON_DEFAULT_HEADERS, timeout=60)

            # Verifica se a resposta foi bem-sucedida
            var_respResponse.raise_for_status()

            # Processa os dados recebidos
            var_listData = var_respResponse.json().get("applist", {}).get("apps", [])
            Settings._var_listApp = var_listData

            # Salva no cache local
            os.makedirs(os.path.dirname(var_strPath), exist_ok=True)

            # Salva o arquivo
            with open(var_strPath, "w", encoding="utf-8") as f:
                json.dump(var_listData, f)
            Settings._var_boolAppListLoaded = True
        except Exception as e:
            Settings._var_listApp = []
        return Settings._var_listApp

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
            # Controle de concorrência
            var_semSemaphore = asyncio.Semaphore(Settings._var_intAsyncConcurrency)
            
            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int) -> dict | None:
                """
                Worker assíncrono para buscar detalhes de um único appid.
                
                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.
                
                Retorna:
                - var_dictDetails (dict | None): Um dicionário com os detalhes do jogo ou None se não encontrado.
                """
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

                            # Verifica se os dados são válidos
                            if var_dictData and str(arg_intAppid) in var_dictData and var_dictData[str(arg_intAppid)]["success"]:
                                var_dictDetails = var_dictData[str(arg_intAppid)]["data"]
                                return var_dictDetails
                    except Exception:
                        return None
                    return None

            # Executa os workers assíncronos
            async with aiohttp.ClientSession(headers=CON_DEFAULT_HEADERS) as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, var_intAppid)) for var_intAppid in arg_seqAppids]
                # Aguarda a conclusão de todas as tarefas
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)

            # Filtra os resultados válidos e os retorna
            var_listResults: list[dict] = []
            for var_dictOut in var_listOut:
                if isinstance(var_dictOut, dict):
                    var_listResults.append(var_dictOut)
            return var_listResults
        except Exception as e:
            raise RuntimeError(f"Falha ao buscar detalhes em bulk: {e}")
        
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
            # Controle de concorrência
            var_semSemaphore = asyncio.Semaphore(Settings._var_intAsyncConcurrency)

            async def worker(arg_clientSession: aiohttp.ClientSession, arg_intAppid: int):
                """
                Worker assíncrono para buscar o resumo de reviews de um único appid.

                Parâmetros:
                - arg_clientSession (aiohttp.ClientSession): A sessão HTTP assíncrona.
                - arg_intAppid (int): O appid do jogo.

                Retorna:
                - var_tupleResult (tuple): Uma tupla (arg_intAppid, var_dictSummary) contendo o Appid e o resumo das reviews ou None se não encontrado.
                """
                async with var_semSemaphore:
                    await asyncio.sleep(random.random() * 0.3)
                    var_strUrl = STEAM_REVIEWS_URL.format(appid=arg_intAppid)
                    var_dictParams = {"json": "1", "language": "all"}
                    try:
                        async with arg_clientSession.get(var_strUrl, params=var_dictParams, timeout=30) as var_respResponse:
                            var_respResponse.raise_for_status()
                            var_dictData = await var_respResponse.json()
                            if var_dictData and var_dictData.get("success") == 1:
                                var_dictSummary = var_dictData.get("query_summary", {})
                                if isinstance(var_dictSummary, dict):
                                    var_dictSummary = dict(var_dictSummary)
                                    var_dictSummary["appid"] = arg_intAppid
                                    var_tupleResult = (arg_intAppid, var_dictSummary)
                                    return var_tupleResult
                    except Exception:
                        return None
                    return None

            var_dictResult: dict[int, dict] = {}
            async with aiohttp.ClientSession(headers=CON_DEFAULT_HEADERS) as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, var_intAppid)) for var_intAppid in arg_seqAppids]
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
            for var_tupleItem in var_listOut:
                if (isinstance(var_tupleItem, tuple) and isinstance(var_tupleItem[0], int) and isinstance(var_tupleItem[1], dict)):
                    if var_tupleItem[1]['total_reviews'] > 0:
                        var_dictResult[var_tupleItem[0]] = var_tupleItem[1]
            return var_dictResult
        except Exception as e:
            raise RuntimeError(f"Falha ao buscar resumos de reviews: {e}")
        
    # ------------------- ITAD lookups -------------------
    @classmethod
    def lookup_itad_ids(cls, arg_seqTitles: Sequence[str]) -> dict:
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

        if not Settings._var_strItadApiKey:
            raise RuntimeError("ITAD_API_KEY não definido")
        try:
            var_strSince = (datetime.now(timezone.utc) - timedelta(days=arg_intAnos * 365)).strftime("%Y-%m-%dT%H:%M:%SZ")
            var_dictResults = {}
            var_semSemaphore = asyncio.Semaphore(getattr(Settings, '_var_intAsyncConcurrency', 5))
            
            async def worker(arg_clientSession: aiohttp.ClientSession, arg_strItadPlain: str):
                async with var_semSemaphore:
                    await asyncio.sleep(random.random() * 0.2)
                    var_dictParams = {
                        "key": Settings._var_strItadApiKey,
                        "id": arg_strItadPlain,
                        "shops": "61",
                        "country": "BR",
                        "since": var_strSince,
                    }
                    try:
                        async with arg_clientSession.get(ITAD_HISTORY_URL, params=var_dictParams, timeout=30) as var_respResponse:
                            var_respResponse.raise_for_status()
                            var_dictData = await var_respResponse.json()
                            return (arg_strItadPlain, var_dictData)
                    except Exception:
                        return (arg_strItadPlain, None)

            async with aiohttp.ClientSession() as var_respSession:
                var_listTasks = [asyncio.create_task(worker(var_respSession, plain)) for plain in arg_seqItadPlain]
                var_listOut = await asyncio.gather(*var_listTasks, return_exceptions=True)
            for plain, result in var_listOut:
                var_dictResults[plain] = result
            return var_dictResults
        
        except Exception as e:
            raise RuntimeError(f"Falha ao buscar histórico ITAD em bulk: {e}")