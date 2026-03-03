import logging

logger = logging.getLogger(__name__)

class Limpar_Dados:
    """
    Classe responsável por realizar a limpeza dos dados brutos obtidos do banco de dados, preparando-os para análise e modelagem.
    """

    @classmethod
    def limpar_score(cls):
        """
        Padroniza a coluna 'review_score' para garantir que os valores sejam numéricos.
        """
        var_dictReviewsValidos = {
                0: 'Outros',
                1: 'Nenhuma analise de usuario', 
                2: 'Extremamente negativas', 
                3: 'Muito negativas', 
                4: 'Bem negativas', 
                5: 'Negativas', 
                6: 'Mistas', 
                7: 'Positivas', 
                8: 'Bem positivas',
                9: 'Muito positivas', 
                10: 'Extremamente positivas', 
            }
        try:
            pass
        except Exception as err:
            logger.error(f"Erro ao limpar a coluna 'review_score': {err}")
            raise Exception(f"Erro ao limpar a coluna 'review_score': {err}")