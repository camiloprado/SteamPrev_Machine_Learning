from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
from prj_TCC_PREVISOR_STEAM.classes.core.application import InitApplication
from prj_TCC_PREVISOR_STEAM.classes.utils.task_manager import GetTask
from prj_TCC_PREVISOR_STEAM.classes.core.Process import Process
import logging

logger = logging.getLogger(__name__)

class Loop:
    """
    Classe para gerenciar o loop principal da aplicação, executando as tarefas na fila.
    """

    @staticmethod
    def execute():
        """
        Executa uma tarefa específica.
        
        Parâmetros:
        
        Retorna:
        
        """
        var_listFila = GetTask.load_task_queue()
        var_intTotalTarefas = len(var_listFila)
        logger.info("="*60)
        logger.info(f"INICIANDO LOOP PRINCIPAL - {var_intTotalTarefas} tarefas na fila")
        logger.info("="*60)
        
        while len(var_listFila) > 0:
            for var_intTentativa in range(Settings._var_dictSettings["max_tentativas"]):
                try:
                    # Lógica para executar a tarefa
                    Process.execute()
                    var_listFila.pop(0)
                    logger.info(f"Tarefa concluída. Tarefas restantes: {len(var_listFila)}")
                    
                except Exception as e:
                    var_strTraceback = e.__traceback__
                    if var_intTentativa == Settings._var_dictSettings["max_tentativas"] - 1:
                        raise Exception(f"Erro ao processar a tarefa após {Settings._var_dictSettings['max_tentativas']} tentativas: {e}\nTraceback: {var_strTraceback}")
                    InitApplication.execute(arg_boolFirstRun=False)

                else:
                    break
        
        logger.info("="*60)
        logger.info(f"LOOP PRINCIPAL CONCLUÍDO - {var_intTotalTarefas} tarefas processadas")
        logger.info("="*60)