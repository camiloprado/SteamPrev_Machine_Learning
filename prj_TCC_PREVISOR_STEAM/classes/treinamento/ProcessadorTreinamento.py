from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinamento import TreinarModelo
from prj_TCC_PREVISOR_STEAM.aprendizadodemaquina_livro.treinamento_avaliacao import TreinamentoAvaliacao
import logging

logger = logging.getLogger(__name__)

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
            # Carrega os dados de treinamento
            var_dfXTreino, var_serYtreino, var_dfXTeste, var_serYteste = TreinarModelo.carregar_dados_treinamento()

            # Treina o modelo
            TreinamentoAvaliacao.metodo_treinarModeloRegressaoLinear(var_dfXTreino, var_serYtreino)

            # Avalia o modelo
            var_r2 = TreinamentoAvaliacao.metodo_avaliarModeloRegressaoLinear(var_dfXTeste, var_serYteste)

            logger.info(f"Treinamento de regressão linear concluído com R²: {var_r2:.4f}")
            return var_r2

        except Exception as e:
            logger.error(f"Erro no treinamento de regressão linear: {e}", exc_info=True)
            raise