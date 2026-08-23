
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
        
        # Divide a string no primeiro grande bloco de espaços e mantém apenas a primeira parte real do nome
        var_strNome = re.split(r'\s{3,}', arg_strNome)[0]
        
        # Remove acentos
        var_strNome = unicodedata.normalize('NFKD', var_strNome).encode('ASCII', 'ignore').decode('utf-8')
        
        # Remove caracteres especiais e converte para minúsculas
        var_strNome = re.sub(r'[^a-zA-Z0-9\s]', '', var_strNome).strip()

        # Remove múltiplos espaços internos, substituindo por um único espaço
        var_strNome = re.sub(r'\s+', ' ', var_strNome)
        
        if len(var_strNome) > 255:
            var_strNome = var_strNome[:255]
        elif var_strNome == "":
            var_strNome = "Desconhecido"
        return var_strNome