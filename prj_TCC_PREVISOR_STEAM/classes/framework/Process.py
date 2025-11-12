from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor

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
        # Lógica para processar a tarefa
        Previsor.alimentar_banco_dados_raw_docker()
        var_listAppids = PostgreSQL.buscar_appids_nao_processados()
        ProcessadorETL.processar_lote(var_listAppids)
        Previsor.alimentar_banco_dados_ITAD()
