from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

import unicodedata
import re
import logging

logger = logging.getLogger(__name__)

class LimparNome:
    """
    Classe responsável por limpar e normalizar o campo "nome" dos jogos.
    """

    @classmethod
    def normalizar_nome(cls, arg_strNome: str) -> str:
        """
        Normaliza o nome do jogo, removendo acentos, caracteres especiais e convertendo para minúsculas.

        Parâmetros:
        - arg_strNome (str): Nome bruto do jogo a ser normalizado.

        Retorna:
        - str: Nome normalizado
        """
        if not isinstance(arg_strNome, str):
            return "Desconhecido"
        
        # Remove acentos
        var_strNome = unicodedata.normalize('NFKD', arg_strNome).encode('ASCII', 'ignore').decode('utf-8')
        
        # Remove caracteres especiais e converte para minúsculas
        var_strNome = re.sub(r'[^a-zA-Z0-9\s]', '', var_strNome).strip().replace('  ', ' ')
        if len(var_strNome) > 255:
            var_strNome = var_strNome[:255]
        return var_strNome