from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from datetime import datetime
from sklearn.impute import SimpleImputer      
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
from sklearn.base import BaseEstimator, TransformerMixin
import json, locale, logging, pandas as pd

logger = logging.getLogger(__name__)

class LimpezaDados:
    """
    Classe para limpeza de dados.
    """
    _var_sklImputer = SimpleImputer(strategy="median")

    @classmethod
    def tratar_data(cls, arg_strData: str) -> str:
        """
        Trata a data para um formato padrão.

        Parametros:
        - arg_strData (str): Data em formato string.

        Retorna:
        - var_strDataFormatada (str): Data em formato "YYYY-MM-DD".
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
            logger.error(f"Erro ao tratar data '{arg_strData}': {e}")
            return "Indisponível"

    @classmethod
    def tratar_preco(cls, arg_strPreco: str) -> float:
        """
        Trata o preço para um formato numérico padrão.

        Parametros:
        - arg_strPreco (str): Preço em formato string.

        Retorna:
        - var_floatPreco (float): Preço em formato float.
        """
        try:
            var_strPrecoLimpo = arg_strPreco.replace("R$", "").replace("$", "").replace("€", "").replace("£", "").strip()
            var_strPrecoLimpo = var_strPrecoLimpo.replace(",", ".")
            var_floatPreco = float(var_strPrecoLimpo)
            return var_floatPreco
        except Exception as e:
            logger.error(f"Erro ao tratar preço '{arg_strPreco}': {e}")
            return 0.0
    
    @classmethod
    def carregar_dataframe(cls, arg_strNomeTabela: str) -> pd.DataFrame:
        """
        Carrega os dados de uma tabela PostgreSQL em um DataFrame do pandas.

        Parametros:
        - arg_strNomeTabela (str): Nome da tabela no banco de dados.

        Retorna:
        - var_dfData (pd.DataFrame): DataFrame contendo os dados da tabela.
        """
        var_listData = PostgreSQL.buscar_todos_dados(arg_strNomeTabela=arg_strNomeTabela)
        var_dfData = pd.DataFrame(var_listData)
        return var_dfData
    

    @classmethod
    def ordinal_encoder(cls, arg_dfData: pd.DataFrame, arg_listColunas: list) -> pd.DataFrame:
        """
        Aplica Ordinal Encoding nas colunas especificadas.

        Parametros:
        - arg_dfData (pd.DataFrame): DataFrame do pandas a ser transformado.
        - arg_listColunas (list): Lista de colunas a serem transformadas.

        Retorna:
        - arg_dfData (pd.DataFrame): DataFrame transformado.
        """
        var_sklEncoder = OrdinalEncoder()
        arg_dfData[arg_listColunas] = var_sklEncoder.fit_transform(arg_dfData[arg_listColunas])
        return arg_dfData
    
    @classmethod
    def onehot_encoder(cls, arg_dfData: pd.DataFrame, arg_listColunas: list) -> pd.DataFrame:
        """
        Aplica One-Hot Encoding nas colunas especificadas.

        Parametros:
        - arg_dfData (pd.DataFrame): DataFrame do pandas a ser transformado.
        - arg_listColunas (list): Lista de colunas a serem transformadas.

        Retorna:
        - arg_dfData (pd.DataFrame): DataFrame transformado.
        """
        var_sklEncoder = OneHotEncoder()
        var_ndarrayEncoded = var_sklEncoder.fit_transform(arg_dfData[arg_listColunas])
        var_arrayEncoded = var_ndarrayEncoded.toarray()
        var_dfEncoded = pd.DataFrame(var_arrayEncoded, columns=var_sklEncoder.get_feature_names_out(arg_listColunas))
        arg_dfData = arg_dfData.drop(columns=arg_listColunas).reset_index(drop=True)
        arg_dfData = pd.concat([arg_dfData, var_dfEncoded], axis=1)
        return arg_dfData
    
    @classmethod
    def fit_imputer(cls, arg_dfData: pd.DataFrame, arg_listColunas: list) -> pd.DataFrame:
        """
        Aplica Simple Imputer nas colunas especificadas.

        Parametros:
        - arg_dfData (pd.DataFrame): DataFrame do pandas a ser transformado.
        - arg_listColunas (list): Lista de colunas a serem transformadas.

        Retorna:
        - arg_dfData (pd.DataFrame): DataFrame transformado.
        """
        arg_dfData[arg_listColunas] = cls._var_sklImputer.fit_transform(arg_dfData[arg_listColunas])
        return arg_dfData