from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from datetime import datetime       
import json, locale

class LimpezaDados:
    """
    Classe para limpeza de dados.
    """
    
    @classmethod
    def seleciona_games(cls, arg_listDados: list) -> list:
        """
        Seleciona apenas os jogos dos dados fornecidos.
        
        Parâmetros:
        - arg_listDados (list): Lista de dados a serem filtrados.

        Retorna:
        - var_listGames (list): Lista contendo apenas os jogos.
        """
        var_listGames = []
        for var_dictDado in arg_listDados:
            if var_dictDado.get("type") == "game" and not var_dictDado.get("is_free"):
                var_listGames.append(var_dictDado)
        print(f"Número de jogos selecionados: {len(var_listGames)}")
        return var_listGames
    
    @classmethod
    def tratar_data(cls, arg_strData: str) -> str:
        """
        Trata a data para um formato padrão.
        
        Parâmetros:
        - arg_strData (str): Data em formato string.

        Retorna:
        - var_strDataFormatada (str): Data formatada.
        """
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')  # se disponível no sistema
            var_dateData = datetime.strptime(arg_strData.replace(".", ""), "%d %m, %Y")
            var_strDataFormatada = var_dateData.strftime("%Y-%m-%d")
            return var_strDataFormatada
        except Exception as e:
            print(f"Erro ao tratar data '{arg_strData}': {e}")
            return "Indisponível"
