from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorLimpeza import ProcessadorLimpeza
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.utils.GetTask import GetTask

import logging

logger = logging.getLogger(__name__)

class Process:
    """
    Classe para gerenciar o processamento das tarefas.
    """

    @classmethod
    def execute(cls):
        """
        Processa uma tarefa específica.

        Parâmetros:
        - arg_listTask: A lista de tarefas a ser processada.

        Retorna:
        - Resultado do processamento da tarefa.
        """
        logger.info("="*60)
        logger.info("PROCESSANDO TAREFA")
        logger.info("="*60)
        
        # Lógica para processar a tarefa
        
        logger.info("="*60)
        logger.info("TAREFA PROCESSADA")
        logger.info("="*60)
