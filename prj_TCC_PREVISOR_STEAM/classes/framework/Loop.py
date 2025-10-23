from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.framework.InitApplication import InitApplication
from prj_TCC_PREVISOR_STEAM.classes.utils.GetTask import GetTask
from prj_TCC_PREVISOR_STEAM.classes.framework.Process import Process

class Loop:
    """
    Classe para gerenciar o loop principal da aplicação, executando as tarefas na fila.
    """

    @classmethod
    def __init__(cls):
        cls.var_clsGetTask = GetTask()
        cls.var_clsProcess = Process()

    @classmethod
    def run(cls):
        """
        Executa o loop principal para processar as tarefas na fila.
        
        Retorna:
        - None
        """
        while True:
            if cls.var_clsGetTask.var_listTaskQueue:
                var_listTask = cls.var_clsGetTask.var_listTaskQueue.pop(0)
                cls.execute(var_listTask)
            else:
                break

    @staticmethod
    def execute():
        """
        Executa uma tarefa específica.
        
        Parâmetros:
        
        Retorna:
        
        """
        while var_dictFila is not None:
            for var_intTentativa in range(Settings._var_dictSettings["max_tentativas"]):
                try:
                    # Lógica para executar a tarefa
                    Process.execute()
                    
                except Exception as e:
                    if var_intTentativa == Settings._var_dictSettings["max_tentativas"] - 1:
                        raise e
                    InitApplication.execute(arg_boolFirstRun=False)

                else:
                    break