from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, mean_squared_error, f1_score
from sklearn.model_selection import train_test_split

class TreinarModelo:
    """
    Classe para treinar modelos de Machine Learning.
    """

    @classmethod
    def treinar(cls, arg_dfX, arg_arrY, arg_strTipo='classificacao', arg_floatTestSize=0.2, arg_intRandomState=42) -> tuple:
        """
        Método para iniciar o treinamento do modelo.

        Parâmetros:
        - arg_dfX (DataFrame ou array): Features
        - arg_arrY (array): Labels
        - arg_strTipo (str): 'classificacao' ou 'regressao'
        - arg_floatTestSize (float): Proporção para teste
        - arg_intRandomState (int): Semente para reprodução

        Retorna:
        - var_rfModelo: Modelo treinado
        - var_dictMetricas (dict): Métricas de avaliação
        """

        # Codifica labels se for classificação
        if arg_strTipo == 'classificacao':
            var_leLabel = LabelEncoder()
            arg_arrY = var_leLabel.fit_transform(arg_arrY)

        # Divide em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            arg_dfX, arg_arrY, test_size=arg_floatTestSize, random_state=arg_intRandomState
        )

        # Seleciona modelo
        if arg_strTipo == 'classificacao':
            var_rfModelo = RandomForestClassifier(random_state=arg_intRandomState)
        else:
            var_rfModelo = RandomForestRegressor(random_state=arg_intRandomState)

        # Treina
        var_rfModelo.fit(X_train, y_train)

        # Predição
        var_arrYPred = var_rfModelo.predict(X_test)

        # Métricas
        if arg_strTipo == 'classificacao':
            var_floatAccuracy = accuracy_score(y_test, var_arrYPred)
            var_floatF1 = f1_score(y_test, var_arrYPred, average='weighted')
            var_dictMetricas = {'accuracy': var_floatAccuracy, 'f1_score': var_floatF1}
        else:
            var_floatMSE = mean_squared_error(y_test, var_arrYPred)
            var_dictMetricas = {'mse': var_floatMSE}

        return var_rfModelo, var_dictMetricas