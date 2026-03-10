from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

class LimparDistribuidores:
    """
    Classe responsável por realizar a limpeza dos dados relacionados aos distribuidores dos jogos.
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
        try:
            if not isinstance(arg_strTexto, str):
                return ""
            
            # Remove acentos
            var_strTexto = unicodedata.normalize('NFKD', arg_strTexto).encode('ASCII', 'ignore').decode('utf-8')
            
            # Remove caracteres especiais e converte para minúsculas
            var_strTexto = re.sub(r'[^a-zA-Z0-9\s]', '', var_strTexto).strip()
            
            return var_strTexto
            
        except Exception as e:
            logger.error(f"Erro ao normalizar texto: {e}")
            raise Exception(f"Erro ao normalizar texto: {e}")
        
    @classmethod
    def limpar_distribuidores(cls, arg_listDistribuidores: list):
        """
        Padroniza a coluna 'distribuidores' para garantir que os valores sejam consistentes e utilizáveis.

        Parâmetros:
        - arg_listDistribuidores (list): Lista bruta de distribuidores do campo 'publishers' do steam_raw.

        Retorna:
        - List[str]: Conjunto de distribuidores normalizados
        """
        try:
            var_setDistribuidoresUnicos = set()
            for var_strDistribuidor in arg_listDistribuidores:
                var_strDistribuidor = cls.normalizar_texto(var_strDistribuidor)
                var_setDistribuidoresUnicos.add(var_strDistribuidor)
            return list(var_setDistribuidoresUnicos)
        
        except Exception as err:
            logger.error(f"Erro ao limpar a coluna 'distribuidores': {err}")
            raise Exception(f"Erro ao limpar a coluna 'distribuidores': {err}")