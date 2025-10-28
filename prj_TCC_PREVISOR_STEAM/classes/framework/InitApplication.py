from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.utils.GetTask import GetTask
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

class InitApplication:
    """
    Classe para inicializar as aplicações.
    """

    @classmethod
    def execute(cls, arg_boolFirstRun: bool = False):
        """
        Executa a inicialização da aplicação.
        
        Parâmetros:
        - arg_boolFirstRun (bool): Indica se é a primeira execução.

        Retorna:
        - None
        """
        if arg_boolFirstRun:
            PostgreSQL.conectar()
            PostgreSQL.criar_tabela_dadosSteam()
            PostgreSQL.criar_tabela_SteamRaw()
            GetTask.abandona_fila(arg_boolAbandonar=True)
            GetTask.criar_fila()

        for var_intTentativa in range(Settings._var_dictSettings["max_tentativas"]):
            try:
                # Lógica para inicializar a aplicação
                pass
            except Exception as e:
                if var_intTentativa == Settings._var_dictSettings["max_tentativas"] - 1:
                    raise e
                
            else:
                break