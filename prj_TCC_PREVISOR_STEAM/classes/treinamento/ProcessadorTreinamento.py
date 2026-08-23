from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinar_modelos import Treinar_Modelos
import logging

logger = logging.getLogger("treino.orq")

class ProcessadorTreinamento:
    """
    Classe responsável pelo processamento do treinamento do modelo de machine learning.
    """

    @classmethod
    def executar_treinamento(cls):
        """
        Executa o processo de treinamento do modelo de machine learning.
        
        Retorna:
        - None
        """
        try:
            logger.info("Iniciando orquestração de treinamento unificado...")
            Treinar_Modelos.executar_treinamento()
            logger.info("Treinamento unificado concluído com sucesso.")
            return True

        except Exception as e:
            logger.error(f"Erro no treinamento unificado: {e}", exc_info=True)
            raise