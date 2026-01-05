from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL

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
        logger.info("Criando a fila de tarefas.")
        try:
            try:
                var_listDados = SteamClient.find_app_list()
                PostgreSQL.inserir_dadosSteamGenerico(arg_listDadosGerais=var_listDados)
            except:
                var_listDados = SteamClient.load_app_list()

            # Alimentação do banco de dados raw para o docker
            if PostgreSQL.buscar_appids_desatualizados_otimizado():
                Previsor.alimentar_banco_dados_raw_docker()

            ProcessadorETL.processar_lote_unificado()
            
            # Alimentação do banco de dados ITAD para o docker
            if PostgreSQL.buscar_appids_desatualizados_otimizado(arg_strNomeTabela="itad_raw"):
                Previsor.alimentar_banco_dados_ITAD_docker()

            #Alimentação do banco de dados processado via ETL para o Supabase
            if PostgreSQL.buscar_appids_desatualizados_otimizado(arg_strNomeTabela="steam_bd"):
                ProcessadorETL.processar_lote()
            
            cls._var_listTaskQueue = [1]
            
        except Exception as e:
            logger.error(f"Erro ao criar a fila de tarefas: {e}")
            raise Exception(f"Erro ao criar a fila de tarefas: {e}")
        logger.info("Fila de tarefas criada com sucesso.")
        
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