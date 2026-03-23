from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorLimpeza import ProcessadorLimpeza, MultiLabelBinarizerTransformer as MLBTransformer
from sklearn.linear_model import LinearRegression
from pandas import DataFrame, Series

class TreinamentoAvaliacao:
    """
    Classe responsável pelo treinamento e avaliação de modelos preditivos.
    """

    var_molLinReg = LinearRegression()

    def __init__(cls):
        cls.var_molLinReg = LinearRegression()
        
    @classmethod
    def metodo_treinarModeloRegressaoLinear(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> LinearRegression:
        """
        Treina um modelo de regressão linear.

        Parâmetros:
        arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        LinearRegression: Modelo treinado.
        """
        cls.var_molLinReg.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molLinReg
    
    @classmethod
    def metodo_avaliarModeloRegressaoLinear(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> float:
        """
        Avalia o modelo de regressão linear.

        Parâmetros:
        arg_dfXTeste (DataFrame): Dados de entrada para teste.
        arg_serYteste (Series): Valores alvo para teste.

        Retorna:
        float: R² do modelo no conjunto de teste.
        """
        r2_score = cls.var_molLinReg.score(arg_dfXTeste, arg_serYteste)
        return r2_score
        