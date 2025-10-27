from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from datetime import datetime
import asyncio, json, os


class GetTask:
    """
    Classe utilitária para gerenciar as tarefas.
    """
    _var_listTaskQueue = []
    
    @classmethod
    def criar_fila(cls):
        """
        Cria a fila de tarefas.
        
        Retorna:
        """
        var_listApp = SteamClient.load_app_list()
        print(f"Número total de aplicativos carregados: {len(var_listApp)}")
        
        var_intParte = 500
        
        for var_intInicio in range(0, len(var_listApp), var_intParte):
            print(f"Processando aplicativos de {var_intInicio} a {var_intInicio + var_intParte} de {len(var_listApp)}.")
            var_listAppID = []
            var_listAppIDAtual = []
            var_listAppAtual = var_listApp[var_intInicio:var_intInicio + var_intParte]

            for var_dictApp in var_listAppAtual:
                if var_dictApp.get("appid") not in var_listAppID:
                    var_listAppIDAtual.append(var_dictApp.get("appid"))

            var_listDetails = asyncio.run(SteamClient.fetch_details_bulk(arg_seqAppids=var_listAppIDAtual))
            # for var_dictDetail in var_listDetails:
            #     print(f"--- Dados: {var_dictDetail.get('steam_appid')} ---")
            #     for i, v in var_dictDetail.items():
            #         print(f"- Coluna {i}: {v}")
            if not var_listDetails:
                continue
            var_listGames = LimpezaDados.seleciona_games(var_listDetails)
            var_tupleCategorias = ()
            var_tupleGenero = ()
            var_strdataLancamento = ""
            for var_dictApp in var_listGames:
                var_intAppid = int(var_dictApp.get("steam_appid"))
                var_strName = var_dictApp.get("name")            
                var_intIdadeClassificada = var_dictApp.get("required_age")
                var_listLinguagens = var_dictApp.get("supported_languages").replace("<strong>*</strong>", "").replace("<br>", ", ").split(", ")
                var_listDesenvolvedores = var_dictApp.get("developers")
                var_listDistribuidores = var_dictApp.get("publishers")
                var_strPreco = var_dictApp.get("price_overview").get("final_formatted") if var_dictApp.get("price_overview") else "Gratuito"
                var_intMetacriticScore = var_dictApp.get("metacritic").get("score") if var_dictApp.get("metacritic") else None
                for var_dictCategoria in var_dictApp.get("categories"):
                    var_tupleCategorias += (var_dictCategoria.get("description"), )
                for var_dictGenero in var_dictApp.get("genres"):
                    var_tupleGenero += (var_dictGenero.get("description"), )
                if var_dictApp.get("release_date").get("date"):
                    var_strdataLancamento = LimpezaDados.tratar_data(arg_strData=var_dictApp.get("release_date").get("date"))
                elif var_dictApp.get("release_date").get("coming_soon"):
                    var_strdataLancamento = "Em breve"
                else:
                    var_strdataLancamento = "Indisponível"
                print(f"--- Dados: {var_intAppid} ---")
                print(f"- Nome: {var_strName}")
                print(f"- Idade Classificada: {var_intIdadeClassificada}")
                print(f"- Linguagens: {var_listLinguagens}")
                print(f"- Desenvolvedores: {var_listDesenvolvedores}")
                print(f"- Distribuidores: {var_listDistribuidores}")
                print(f"- Preço: {var_strPreco}")
                print(f"- Metacritic Score: {var_intMetacriticScore}")
                print(f"- Categorias: {var_tupleCategorias}")
                print(f"- Gêneros: {var_tupleGenero}")
                print(f"- Data de Lançamento: {var_strdataLancamento}")

            var_listAppID.extend([var_dictApp.get("steam_appid") for var_dictApp in var_listGames])
            var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary(arg_seqAppids=var_listAppID))
            print(f"Número de resenhas coletadas: {len(var_dictReview)}")

        var_listConsolidado = []
        for var_intIndex, var_dictDetail in enumerate(var_listDetails):
            print(f"Progresso: {var_intIndex + 1} de {len(var_listDetails)}")
            var_intAppid = var_dictDetail.get("steam_appid")
            var_strName = var_dictDetail.get("name")
            var_dictReview = var_dictReview.get(var_intAppid) if var_intAppid in var_dictReview else None
            var_listConsolidado.append({
                "appid": var_intAppid,
                "name": var_strName,
                "details": var_dictDetail,
                "reviews": var_dictReview
            })
            print(f"Adicionada à fila: {var_strName} (AppID: {var_intAppid})")
        cls._var_listTaskQueue = var_listConsolidado

    @classmethod
    def abandona_fila(cls, arg_boolAbandonar: bool = True):
        """
        Abandona a fila de tarefas.

        Retorna:
        - None
        """
        if arg_boolAbandonar:
            if len(cls._var_listTaskQueue) > 0:
                for var_intIndex in range(len(cls._var_listTaskQueue)):
                    cls._var_listTaskQueue.pop(var_intIndex)

    @classmethod
    def load_task_queue(cls) -> dict:
        """
        Carrega a fila de tarefas.

        Retorna:
        - None
        """
        return cls._var_listTaskQueue