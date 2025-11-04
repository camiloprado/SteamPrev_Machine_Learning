from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.framework.Initialization import Initialization
from prj_TCC_PREVISOR_STEAM.classes.framework.Loop import Loop
from prj_TCC_PREVISOR_STEAM.classes.framework.End import End
import logging

logger = logging.getLogger(__name__)


class Bot:
    """
    Classe principal do projeto. Responsável por gerenciar o bot.
    """

    @classmethod
    def start(cls):
        """
        Inicia o bot, executando a inicialização, o loop principal e o encerramento.
        
        Retorna:
        - None
        """
        try:
            Initialization.execute()
            Loop.execute()
        except Exception as e:
            logger.error(f"Erro ao iniciar o bot: {e}")
        
        try:
            End.execute()
        except Exception as e:
            logger.error(f"Erro ao encerrar o bot: {e}")

if __name__ == "__main__":
    Bot.start()