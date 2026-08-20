
import logging

logger = logging.getLogger(__name__)

class LimparMetacritic:
    """
    Classe responsável por limpar e padronizar o campo "metacritic_score" dos jogos.
    """

    @classmethod
    def processar_metacritic(cls, arg_anyMetacritic: any) -> str:
        """
        Processa o campo de metacritic_score, extraindo o valor numérico e convertendo para um formato padronizado.

        Parâmetros:
        - arg_anyMetacritic (any): Valor bruto do campo 'metacritic' do steam_raw.

        Retorna:
        - str: Metacritic score padronizado (ex: "85", "Desconhecido")
        """
        try:
            if isinstance(arg_anyMetacritic, dict):
                var_intScore = arg_anyMetacritic.get("score", None)
                if isinstance(var_intScore, int) and 0 <= var_intScore <= 100:
                    return str(var_intScore)
            return "Desconhecido"
            
        except Exception as e:
            logging.error(f"Erro ao processar o metacritic score: {e}")
            raise Exception(f"Erro ao processar o metacritic score: {e}")
