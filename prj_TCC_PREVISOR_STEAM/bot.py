from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
from prj_TCC_PREVISOR_STEAM.classes.core.initialization import Initialization
from prj_TCC_PREVISOR_STEAM.classes.core.loopstation import Loop
from prj_TCC_PREVISOR_STEAM.classes.core.endprocess import End
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