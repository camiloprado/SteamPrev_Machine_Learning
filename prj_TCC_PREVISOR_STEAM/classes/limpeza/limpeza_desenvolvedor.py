from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL

import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

class LimparDesenvolvedor:
    """
    Classe responsável por realizar a limpeza dos dados relacionados aos desenvolvedores dos jogos, preparando-os para análise e modelagem.
    """

    @classmethod
    def normalizar_texto(cls, arg_strTexto: str) -> str:
        """
        Normaliza o texto, removendo acentos, caracteres especiais e convertendo para minúsculas.

        Parâmetros:
        - arg_strTexto (str): Texto bruto a ser normalizado.

        Retorna:
        - str: Texto normalizado
        """
        if not isinstance(arg_strTexto, str):
            return ""
        
        # Remove acentos
        var_strTexto = unicodedata.normalize('NFKD', arg_strTexto).encode('ASCII', 'ignore').decode('utf-8')
        
        # Remove caracteres especiais e converte para minúsculas
        var_strTexto = re.sub(r'[^a-zA-Z0-9\s]', '', var_strTexto).strip()
        
        return var_strTexto
    
    @classmethod
    def limpar_desenvolvedor(cls, arg_listDesenvolvedores: list):
        """
        Padroniza a coluna 'developers' para garantir que os valores sejam consistentes e utilizáveis.

        Parâmetros:
        - arg_listDesenvolvedores (list): Lista bruta de desenvolvedores do campo 'developers' do steam_raw.

        Retorna:
        - List[str]: Conjunto de desenvolvedores normalizados
        """
        try:
            
            var_setDesenvolvedoresUnicos = set()
            for var_strDesenvolvedor in arg_listDesenvolvedores:
                var_strDesenvolvedor = cls.normalizar_texto(var_strDesenvolvedor)
                var_setDesenvolvedoresUnicos.add(var_strDesenvolvedor)
            return list(var_setDesenvolvedoresUnicos)
        
        except Exception as err:
            logger.error(f"Erro ao limpar a coluna 'developers': {err}")
            raise Exception(f"Erro ao limpar a coluna 'developers': {err}")