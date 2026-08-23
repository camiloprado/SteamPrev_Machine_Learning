
import logging

logger = logging.getLogger(__name__)

class LimparPreco:
    """
    Classe responsável por limpar e padronizar o campo "preço" dos jogos.
    """

    @classmethod
    def processar_preco(cls, arg_dictPreco: dict) -> float:
        """
        Processa o campo de preço, extraindo o valor numérico e convertendo para um formato padronizado.

        Parâmetros:
        - arg_dictPreco (dict): Dicionário bruto do campo 'price_overview' do steam_raw.

        Retorna:
        - float: Preço padronizado (ex: 19.99)
        """
        try:
            if not isinstance(arg_dictPreco, dict):
                return "Gratuito"
            
            var_strPreco = arg_dictPreco.get("final_formatted", "Desconhecido").strip().replace(",", ".")
            if var_strPreco.lower() in ["free", "grátis", "gratuito"]:
                return "Gratuito"
            
            return var_strPreco
            
        except Exception as e:
            logging.error(f"Erro ao processar o preço: {e}")
            raise Exception(f"Erro ao processar o preço: {e}")