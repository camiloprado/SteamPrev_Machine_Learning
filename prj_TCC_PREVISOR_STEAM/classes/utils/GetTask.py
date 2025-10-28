from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

from datetime import datetime
from time import sleep
import asyncio, json, os, logging

logger = logging.getLogger(__name__)


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
            logger.info(f"Número total de aplicativos carregados: {len(var_listApp)}")
            
            var_intParte = Settings._var_dictSettings["partes_por_serie"]
            
            for var_intInicio in range(0, len(var_listApp), var_intParte):
                logger.info(f"--- Processando aplicativos de {var_intInicio} a {var_intInicio + var_intParte} de {len(var_listApp)}. ---")
                var_listAppIDAtual = []
                var_listAppAtual = var_listApp[var_intInicio:var_intInicio + var_intParte]

                for var_dictApp in var_listAppAtual:
                    if var_dictApp.get("appid"):
                        var_dateUltimaAtualizacao = PostgreSQL.verificar_ultima_atualizacao(arg_intAppid=var_dictApp.get("appid"), arg_strNomeTabela="steam_raw")
                        if var_dateUltimaAtualizacao:
                            var_intDiasDesdeAtualizacao = (datetime.now().replace(tzinfo=None) - var_dateUltimaAtualizacao.replace(tzinfo=None)).days
                        else:
                            var_intDiasDesdeAtualizacao = Settings._var_dictSettings["dias_para_atualizacao"] + 1

                        if var_intDiasDesdeAtualizacao < Settings._var_dictSettings["dias_para_atualizacao"]:
                            continue
                        var_listAppIDAtual.append(var_dictApp.get("appid"))
        
                var_dictDetails = asyncio.run(SteamClient.fetch_details_bulk(arg_seqAppids=var_listAppIDAtual))
                var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary(arg_seqAppids=var_listAppIDAtual))
                
                if var_dictDetails is None:
                    if var_dictReview is None:
                        continue

                # Combina details e reviews em um único dicionário usando appid como chave
                for var_intAppid in var_dictDetails.keys():
                    var_dictRawData = {
                        "appid": var_intAppid,
                        "detalhes": var_dictDetails.get(var_intAppid),
                        "reviews": var_dictReview.get(var_intAppid)
                    }
                    PostgreSQL.inserir_dadosSteamRaw(arg_dictDados=var_dictRawData)

            var_listDadosSteamRaw = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="steam_raw")
            var_listGames = LimpezaDados.seleciona_games(var_listDadosSteamRaw)
            if var_listGames:
                var_listDados = LimpezaDados.selecionar_base_dadosSteamBD(var_listGames)
                for var_dictDado in var_listDados:
                    if var_dictDado.get("appid"):
                        var_dateUltimaAtualizacao = PostgreSQL.verificar_ultima_atualizacao(arg_intAppid=var_dictDado.get("appid"), arg_strNomeTabela="steam_bd")
                        if var_dateUltimaAtualizacao:
                            var_intDiasDesdeAtualizacao = (datetime.now().replace(tzinfo=None) - var_dateUltimaAtualizacao.replace(tzinfo=None)).days
                        else:
                            var_intDiasDesdeAtualizacao = Settings._var_dictSettings["dias_para_atualizacao"] + 1

                        if var_intDiasDesdeAtualizacao < Settings._var_dictSettings["dias_para_atualizacao"]:
                            continue
                        PostgreSQL.inserir_dadosSteamBD(arg_dictDados=var_dictDado)
            else:
                raise Exception("Nenhum jogo válido encontrado para processar.")            
            
        except Exception as e:
            logger.error(f"Erro ao criar a fila de tarefas: {e}")
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