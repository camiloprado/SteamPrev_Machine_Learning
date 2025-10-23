from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.InitApplication import InitApplication

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
            var_listApp = SteamClient.load_app_list()
            InitApplication.execute(arg_boolFirstRun=True)

        except Exception as e:
            raise Exception(f"Erro na inicialização: {e}")