from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.utils.GetTask import GetTask
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL

import logging

logger = logging.getLogger("framework.app")

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
        logger.info("="*60)
        logger.info("INICIANDO APLICAÇÃO")
        logger.info("="*60)
        
        if arg_boolFirstRun:
            var_boolDocker = Settings.start_docker_postgres()
            GetTask.abandona_fila(arg_boolAbandonar=True)
            if var_boolDocker:
                GetTask.criar_fila()
            else:
                raise Exception("Erro ao iniciar o Docker PostgreSQL.")
            
        for var_intTentativa in range(Settings._var_dictSettings["max_tentativas"]):
            try:
                # Lógica para inicializar a aplicação
                pass
            except Exception as e:
                if var_intTentativa == Settings._var_dictSettings["max_tentativas"] - 1:
                    raise e
                
            else:
                break
        
        logger.info("="*60)
        logger.info("APLICAÇÃO INICIALIZADA")
        logger.info("="*60)