
import re
import logging

logger = logging.getLogger(__name__)

class LimparIdade:

    @classmethod
    def processar_classificacao_etaria(cls, arg_intClassificacaoEtaria: int) -> str:
        """
        Processa a classificação etária, extraindo apenas os dígitos e convertendo para um formato padronizado.

        Parâmetros:
        - arg_intClassificacaoEtaria (int): Classificação etária bruta do campo 'required_age' do steam_raw.

        Retorna:
        - str: Classificação etária padronizada (ex: "18", "16", "12", "3", "Livre")
        """
        try:
            if not isinstance(arg_intClassificacaoEtaria, int) or arg_intClassificacaoEtaria < 0:
                return "Desconhecido"
            
            # Extrai apenas os dígitos
            var_intApenasDigitos = int(re.sub(r'\D', '', str(arg_intClassificacaoEtaria)))
            if var_intApenasDigitos < 10:
                return "L (Livre)"
            
            elif var_intApenasDigitos < 12:
                return "10 anos"
            
            elif var_intApenasDigitos < 14:
                return "12 anos"
            
            elif var_intApenasDigitos < 16:
                return "14 anos"
            
            elif var_intApenasDigitos < 18:
                return "16 anos"
            
            elif var_intApenasDigitos < 100:
                return "18+ anos"
             
            else:
                return "Desconhecido"
        
        except Exception as e:
            logger.error(f"Erro ao processar classificação etária: {e}")
            raise Exception(f"Erro ao processar classificação etária: {e}")