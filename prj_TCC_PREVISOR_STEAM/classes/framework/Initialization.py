from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.InitApplication import InitApplication

import logging

logger = logging.getLogger("framework.init")

class Initialization:
    """
    Classe responsável pela inicialização do sistema.
    """

    @staticmethod
    def execute():
        """
        Método de classe para executar a inicialização do sistema.
        """
        try:
            logger.info("="*60)
            logger.info("INICIALIZANDO SISTEMA")
            logger.info("="*60)
            
            InitApplication.execute(arg_boolFirstRun=True)
            
            logger.info("="*60)
            logger.info("SISTEMA INICIALIZADO COM SUCESSO")
            logger.info("="*60)
        except Exception as e:
            var_strTraceback = e.__traceback__
            raise Exception(f"Erro na inicialização: {var_strTraceback}")