from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
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
            pass
            
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