from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor

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
            
            var_listAppIDAtual = Previsor.selecionar_dados_velhos(arg_listDados=var_listApp, arg_strNomeTabela="steam_raw")
            logger.info(f"Número de AppIDs a processar: {len(var_listAppIDAtual)}")
            # try:
            #     var_listAppIDAtual = var_listAppIDAtual[:5000]  # Limite para testes iniciais
            #     var_dictTeste = {
            #         0: {
            #             "BatchSize": int(os.getenv("STEAM_BATCH_SIZE", "200")), 
            #             "Delay": int(os.getenv("STEAM_DELAY_BETWEEN_BATCHES", "120")),
            #             "Concurrency": int(os.getenv("STEAM_ASYNC_CONCURRENCY", "1"))
            #         },
            #         1: {
            #             "BatchSize": int(os.getenv("STEAM_BATCH_SIZE", "300")), 
            #             "Delay": int(os.getenv("STEAM_DELAY_BETWEEN_BATCHES", "90")),
            #             "Concurrency": int(os.getenv("STEAM_ASYNC_CONCURRENCY", "2"))
            #         },
            #         2: {
            #             "BatchSize": int(os.getenv("STEAM_BATCH_SIZE", "500")), 
            #             "Delay": int(os.getenv("STEAM_DELAY_BETWEEN_BATCHES", "60")),
            #             "Concurrency": int(os.getenv("STEAM_ASYNC_CONCURRENCY", "3"))
            #         }
            #     }
            #     for var_intIndex, var_dictConfig in var_dictTeste.items():
            #         Settings._var_intBatchesSize = var_dictConfig["BatchSize"]
            #         Settings._var_intDelayBetweenBatches = var_dictConfig["Delay"]
            #         Settings._var_intAsyncConcurrency = var_dictConfig["Concurrency"]
            #         logger.info("="*80)
            #         logger.info(f"Teste {var_intIndex}: Batch Size={Settings._var_intBatchesSize}, Delay={Settings._var_intDelayBetweenBatches}, Concurrency={Settings._var_intAsyncConcurrency}")
            #         sleep(1800)  # Espera 30 minutos entre os testes para evitar bloqueios
            #         var_dictDetails = asyncio.run(SteamClient.fetch_details_bulk_batched(arg_seqAppids=var_listAppIDAtual))
            #         sleep(1800)  # Espera 30 minutos entre os testes para evitar bloqueios
            #         var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary_batched(arg_seqAppids=var_listAppIDAtual))
            #         logger.info("="*80)
        
            # except Exception as e:
            #     logger.error(f"Erro durante os testes de configuração: {e}")
            #     raise e
            
            sleep(1800)  # Espera 30 minutos entre os testes para evitar bloqueios
            var_dictDetails = asyncio.run(SteamClient.fetch_details_bulk_batched(arg_seqAppids=var_listAppIDAtual))
            sleep(1800)  # Espera 30 minutos entre os testes para evitar bloqueios
            var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary_batched(arg_seqAppids=var_listAppIDAtual))
            
            if not var_dictDetails:
                if not var_dictReview:
                    logger.warning("Nenhum dado retornado da API Steam.")
                    raise Exception("Nenhum dado retornado da API Steam.")
                
            # Combina details e reviews em um único dicionário usando appid como chave
            for var_intAppid in var_dictDetails.keys():
                var_dictRawData = {
                    "appid": var_intAppid,
                    "detalhes": var_dictDetails.get(var_intAppid),
                    "reviews": var_dictReview.get(var_intAppid)
                }
                PostgreSQL.inserir_dadosSteamRaw(arg_dictDados=var_dictRawData)

            var_listDadosSteamRaw = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="steam_raw")
            var_listGames = Previsor.seleciona_games(var_listDadosSteamRaw)
            if var_listGames:
                var_listDados = Previsor.selecionar_base_dadosSteamBD(var_listGames)
                var_listDadosVelhos = Previsor.selecionar_dados_velhos(arg_listDados=var_listDados, arg_strNomeTabela="steam_bd")
                for var_intAppID in var_listDadosVelhos:
                    PostgreSQL.inserir_dadosSteamBD(arg_dictDados=var_listDados[var_intAppID])

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