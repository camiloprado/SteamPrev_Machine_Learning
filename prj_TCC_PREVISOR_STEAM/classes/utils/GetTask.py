from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

from datetime import datetime
from time import sleep
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
        try:

            var_listApp = SteamClient.load_app_list()
            print(f"Número total de aplicativos carregados: {len(var_listApp)}")
            
            var_intParte = Settings._var_dictSettings["partes_porte"]
            
            for var_intInicio in range(0, len(var_listApp), var_intParte):
                print(f"Processando aplicativos de {var_intInicio} a {var_intInicio + var_intParte} de {len(var_listApp)}.")
                var_listAppIDAtual = []
                var_listAppAtual = var_listApp[var_intInicio:var_intInicio + var_intParte]

                for var_dictApp in var_listAppAtual:
                    if var_dictApp.get("appid"):
                        var_dateUltimaAtualizacao = PostgreSQL.verificar_ultima_atualizacao(arg_intAppid=var_dictApp.get("appid"))
                        if var_dateUltimaAtualizacao:
                            var_intDiasDesdeAtualizacao = (datetime.now().replace(tzinfo=None) - var_dateUltimaAtualizacao.replace(tzinfo=None)).days
                        else:
                            var_intDiasDesdeAtualizacao = Settings._var_dictSettings["dias_para_atualizacao"] + 1

                        if var_intDiasDesdeAtualizacao < Settings._var_dictSettings["dias_para_atualizacao"]:
                            continue
                        var_listAppIDAtual.append(var_dictApp.get("appid"))
                print(f"Número de aplicativos para processar: {len(var_listAppIDAtual)}")

                var_listDetails = asyncio.run(SteamClient.fetch_details_bulk(arg_seqAppids=var_listAppIDAtual))
                if not var_listDetails:
                    # sleep(120)
                    continue

                var_listGames = LimpezaDados.seleciona_games(var_listDetails)
                if not var_listGames:
                    continue

                var_setCategorias = set()
                var_setGenero = set()
                var_strdataLancamento = ""
                var_listAppIDAtual = []
                for var_dictApp in var_listGames:
                    if not var_dictApp:
                        print("Aplicativo inválido ou vazio encontrado, pulando.")
                        print(f"Dados do aplicativo: {var_dictApp}")
                        continue
                    var_intAppid = int(var_dictApp.get("steam_appid"))
                    var_listAppIDAtual.append(var_intAppid)
                    var_strName = var_dictApp.get("name")            
                    var_intIdadeClassificada = var_dictApp.get("required_age")
                    if var_dictApp.get("ratings") and var_dictApp.get("ratings").get("dejus"):
                        var_strClassificacaoEtaria = var_dictApp.get("ratings").get("dejus").get("rating")
                    else:
                        var_strClassificacaoEtaria = None
                    var_listLinguagens = var_dictApp.get("supported_languages").replace("<strong>*</strong>", "").replace("<br>", ", ").split(", ")
                    var_listDesenvolvedores = var_dictApp.get("developers")
                    var_listDistribuidores = var_dictApp.get("publishers")
                    var_strPreco = var_dictApp.get("price_overview").get("final_formatted") if var_dictApp.get("price_overview") else None
                    var_intMetacriticScore = var_dictApp.get("metacritic").get("score") if var_dictApp.get("metacritic") else None
                    for var_dictCategoria in var_dictApp.get("categories"):
                        var_setCategorias.add(var_dictCategoria.get("description"))
                    for var_dictGenero in var_dictApp.get("genres"):
                        var_setGenero.add(var_dictGenero.get("description"))
                    if var_dictApp.get("release_date").get("date"):
                        var_strdataLancamento = LimpezaDados.tratar_data(arg_strData=var_dictApp.get("release_date").get("date"))
                    elif var_dictApp.get("release_date").get("coming_soon"):
                        var_strdataLancamento = "Em breve"
                    else:
                        var_strdataLancamento = None
                    
                    var_listCategorias = list(var_setCategorias)
                    var_listGenero = list(var_setGenero)
                    
                    PostgreSQL.inserir_dadosSteamBD(
                        arg_dictDados={
                            "appid": var_intAppid,
                            "nome": var_strName,
                            "idade_classificada": str(var_intIdadeClassificada),
                            "classificacao_etaria": var_strClassificacaoEtaria,
                            "linguagens": var_listLinguagens,
                            "desenvolvedores": var_listDesenvolvedores,
                            "distribuidores": var_listDistribuidores,
                            "preco": var_strPreco,
                            "metacritic_score": str(var_intMetacriticScore),
                            "categorias": var_listCategorias,
                            "genero": var_listGenero,
                            "data_lancamento": var_strdataLancamento
                        }
                    )  
                
                var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary(arg_seqAppids=var_listAppIDAtual))
                if not var_dictReview:
                    # sleep(120)
                    continue
                print(f"Número de resenhas coletadas: {len(var_dictReview)}")
                for var_intAppid, var_dictReview in var_dictReview.items():
                    PostgreSQL.atualizar_reviews(arg_jsonReviews=var_dictReview, arg_intAppid=var_intAppid)
        except Exception as e:
            print(f"Erro ao criar a fila de tarefas: {e}")
            raise Exception(f"Erro ao criar a fila de tarefas: {e}")

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