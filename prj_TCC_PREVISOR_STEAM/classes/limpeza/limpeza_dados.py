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
        try:
            var_listGames = []
            for var_dictDado in arg_listDados:
                if var_dictDado.get("type") == "game" and not var_dictDado.get("is_free"):
                    var_listGames.append(var_dictDado)
            print(f"Número de jogos selecionados: {len(var_listGames)}")
            return var_listGames
        except Exception as e:
            print(f"Erro ao selecionar jogos: {e}")
            return []
        
    @classmethod
    def tratar_data(cls, arg_strData: str) -> str:
        """
        Trata a data para um formato padrão.
        """
        var_listMeses = {
            "jan": "Jan", "fev": "Feb", "mar": "Mar", "abr": "Apr", "mai": "May", "jun": "Jun",
            "jul": "Jul", "ago": "Aug", "set": "Sep", "out": "Oct", "nov": "Nov", "dez": "Dec"
        }
        try:
            var_strDataRaw = arg_strData.replace(".", "")
            var_listPartes = var_strDataRaw.split("/")
            if len(var_listPartes) == 3:
                var_strDia, var_strMes, var_strAno = var_listPartes
                var_strMesIngles = var_listMeses.get(var_strMes.lower(), var_strMes)
                var_strDataIngles = f"{var_strDia} {var_strMesIngles}, {var_strAno}"
                var_dateData = datetime.strptime(var_strDataIngles, "%d %b, %Y")
                var_strDataFormatada = var_dateData.strftime("%Y-%m-%d")
                return var_strDataFormatada
            else:
                # Tenta outros formatos se necessário
                var_dateData = datetime.strptime(var_strDataRaw, "%d %b, %Y")
                var_strDataFormatada = var_dateData.strftime("%Y-%m-%d")
                return var_strDataFormatada
        except Exception as e:
            print(f"Erro ao tratar data '{arg_strData}': {e}")
            return "Indisponível"

    @classmethod
    def tratar_preco(cls, arg_strPreco: str) -> float:
        """
        Trata o preço para um formato numérico padrão.
        """
        try:
            var_strPrecoLimpo = arg_strPreco.replace("R$", "").replace("$", "").replace("€", "").replace("£", "").strip()
            var_strPrecoLimpo = var_strPrecoLimpo.replace(",", ".")
            var_floatPreco = float(var_strPrecoLimpo)
            return var_floatPreco
        except Exception as e:
            print(f"Erro ao tratar preço '{arg_strPreco}': {e}")
            return 0.0