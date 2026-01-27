from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    median_absolute_error, max_error, explained_variance_score
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from pandas import DataFrame, Series
import numpy as np, pandas as pd
import logging
import joblib
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class TreinamentoAvaliacao:
    """
    Classe responsável pelo treinamento e avaliação de modelos preditivos.
    Suporta múltiplos algoritmos, tuning de hiperparâmetros e persistência de modelos.
    """
    
    # Diretório padrão para salvar modelos
    MODELS_DIR = "prj_TCC_PREVISOR_STEAM/resources/models"

    def __init__(cls):
        cls.var_molLinReg = LinearRegression()
        cls.var_molDecTree = DecisionTreeRegressor()
        cls.var_molRandForest = RandomForestRegressor()
        cls.var_molGradBoost = GradientBoostingRegressor()
        cls.var_molSVR = SVR()
        cls.var_molRidge = Ridge()
        cls.var_molLasso = Lasso()
        cls.var_molXGBoost = None  # Será inicializado se XGBoost estiver disponível 
    
    # ================= Regressão Linear =================
    @classmethod
    def metodo_treinarModeloRegressaoLinear(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> LinearRegression:
        """
        Treina um modelo de regressão linear.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - LinearRegression: Modelo treinado.
        """
        cls.var_molLinReg.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molLinReg
    
    @classmethod
    def metodo_avaliarModeloRegressaoLinear(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo de regressão linear.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.

        """
        var_dfPredictions = cls.var_molLinReg.predict(arg_dfXTeste)
        var_floatLinMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatLinRMSE = np.sqrt(var_floatLinMSE)
        logger.info(f"Regressão Linear - RMSE: {var_floatLinRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molLinReg, arg_dfXTeste, arg_serYteste)
    
    # ================= Árvore de Decisão =================
    @classmethod
    def metodo_treinarModeloDecisionTree(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> DecisionTreeRegressor:
        """
        Treina um modelo de árvore de decisão.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - DecisionTreeRegressor: Modelo treinado.
        """
        cls.var_molDecTree.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molDecTree
    
    @classmethod
    def metodo_avaliarModeloDecisionTree(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo de árvore de decisão.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        """
        var_dfPredictions = cls.var_molDecTree.predict(arg_dfXTeste)
        var_floatTreeMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatTreeRMSE = np.sqrt(var_floatTreeMSE)
        logger.info(f"Árvore de Decisão - RMSE: {var_floatTreeRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molDecTree, arg_dfXTeste, arg_serYteste)

    # ================= Random Forest =================
    @classmethod
    def metodo_treinarModeloRandomForest(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> RandomForestRegressor:
        """
        Treina um modelo de Random Forest.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - RandomForestRegressor: Modelo treinado.
        """
        cls.var_molRandForest.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molRandForest
    
    @classmethod
    def metodo_avaliarModeloRandomForest(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo de Random Forest.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        """
        var_dfPredictions = cls.var_molRandForest.predict(arg_dfXTeste)
        var_floatRandMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatRandRMSE = np.sqrt(var_floatRandMSE)
        logger.info(f"Random Forest - RMSE: {var_floatRandRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molRandForest, arg_dfXTeste, arg_serYteste)

    # ================= Avaliação Cruzada =================
    @classmethod
    def avaliar_avaliacao_cruzada(cls, arg_objModelo, arg_dfX:DataFrame, arg_serY:Series, arg_intFolds:int=10) -> None:
        """
        Avalia o modelo usando validação cruzada.

        Parâmetros:
        - arg_objModelo: Modelo a ser avaliado.
        - arg_dfX (DataFrame): Dados de entrada.
        - arg_serY (Series): Valores alvo.
        - arg_intFolds (int): Número de folds para validação cruzada.
        """
        from sklearn.model_selection import cross_val_score
        var_listScores = cross_val_score(arg_objModelo, arg_dfX, arg_serY, scoring='neg_mean_squared_error', cv=arg_intFolds)
        cls.display_score(var_listScores, arg_objModelo.__class__.__name__)
        
    @classmethod
    def display_score(cls, arg_listScore:list, arg_strNomeModelo:str) -> None:
        """
        Exibe a pontuação do modelo.

        Parâmetros:
        - arg_listScore (list): Pontuação a ser exibida.
        - arg_strNomeModelo (str): Nome do modelo.
        """
        logger.info(f"{5*'-'}Pontuação do Modelo {arg_strNomeModelo}: {5*'-'}")
        logger.info(f"SCORE: {arg_listScore}")
        logger.info(f"Média: {np.mean(arg_listScore)}")
        logger.info(f"Desvio Padrão: {np.std(arg_listScore)}")

    # ================= Gradient Boosting =================
    @classmethod
    def metodo_treinarModeloGradientBoosting(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> GradientBoostingRegressor:
        """
        Treina um modelo de Gradient Boosting.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - GradientBoostingRegressor: Modelo treinado.
        """
        cls.var_molGradBoost.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molGradBoost
    
    @classmethod
    def metodo_avaliarModeloGradientBoosting(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo de Gradient Boosting.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        """
        var_dfPredictions = cls.var_molGradBoost.predict(arg_dfXTeste)
        var_floatGradMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatGradRMSE = np.sqrt(var_floatGradMSE)
        logger.info(f"Gradient Boosting - RMSE: {var_floatGradRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molGradBoost, arg_dfXTeste, arg_serYteste)

    # ================= SVR =================
    @classmethod
    def metodo_treinarModeloSVR(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> SVR:
        """
        Treina um modelo SVR (Support Vector Regression).

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - SVR: Modelo treinado.
        """
        cls.var_molSVR.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molSVR
    
    @classmethod
    def metodo_avaliarModeloSVR(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo SVR.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        """
        var_dfPredictions = cls.var_molSVR.predict(arg_dfXTeste)
        var_floatSVRMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatSVRRMSE = np.sqrt(var_floatSVRMSE)
        logger.info(f"SVR - RMSE: {var_floatSVRRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molSVR, arg_dfXTeste, arg_serYteste)

    # ================= Ridge =================
    @classmethod
    def metodo_treinarModeloRidge(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> Ridge:
        """
        Treina um modelo Ridge Regression.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - Ridge: Modelo treinado.
        """
        cls.var_molRidge.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molRidge
    
    @classmethod
    def metodo_avaliarModeloRidge(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo Ridge.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        """
        var_dfPredictions = cls.var_molRidge.predict(arg_dfXTeste)
        var_floatRidgeMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatRidgeRMSE = np.sqrt(var_floatRidgeMSE)
        logger.info(f"Ridge - RMSE: {var_floatRidgeRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molRidge, arg_dfXTeste, arg_serYteste)

    # ================= Lasso =================
    @classmethod
    def metodo_treinarModeloLasso(cls, arg_dfXTreino:DataFrame, arg_serYtreino:Series) -> Lasso:
        """
        Treina um modelo Lasso Regression.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.

        Retorna:
        - Lasso: Modelo treinado.
        """
        cls.var_molLasso.fit(arg_dfXTreino, arg_serYtreino)
        return cls.var_molLasso
    
    @classmethod
    def metodo_avaliarModeloLasso(cls, arg_dfXTeste:DataFrame, arg_serYteste:Series) -> None:
        """
        Avalia o modelo Lasso.

        Parâmetros:
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        """
        var_dfPredictions = cls.var_molLasso.predict(arg_dfXTeste)
        var_floatLassoMSE = mean_squared_error(arg_serYteste, var_dfPredictions)
        var_floatLassoRMSE = np.sqrt(var_floatLassoMSE)
        logger.info(f"Lasso - RMSE: {var_floatLassoRMSE}")
        cls.avaliar_avaliacao_cruzada(cls.var_molLasso, arg_dfXTeste, arg_serYteste)

    # ================= Salvar e Carregar Modelos =================
    @classmethod
    def salvar_modelo(cls, arg_objModelo: Any, arg_strNomeModelo: str, 
                      arg_dictMetricas: Optional[Dict] = None) -> str:
        """
        Salva um modelo treinado usando joblib.

        Parâmetros:
        - arg_objModelo: Modelo a ser salvo.
        - arg_strNomeModelo (str): Nome do modelo para o arquivo.
        - arg_dictMetricas (Dict, optional): Métricas do modelo para salvar junto.

        Retorna:
        - var_strCaminhoCompleto (str): Caminho completo do arquivo salvo.
        """
        try:
            # Criar diretório se não existir
            var_pathDiretorio = Path(cls.MODELS_DIR)
            var_pathDiretorio.mkdir(parents=True, exist_ok=True)
            
            # Criar nome do arquivo com timestamp
            var_strTimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            var_strNomeArquivo = f"{arg_strNomeModelo}_{var_strTimestamp}.joblib"
            var_strCaminhoCompleto = os.path.join(var_pathDiretorio, var_strNomeArquivo)
            
            # Salvar modelo e metadados
            var_dictDados = {
                'modelo': arg_objModelo,
                'nome': arg_strNomeModelo,
                'timestamp': var_strTimestamp,
                'metricas': arg_dictMetricas or {}
            }
            
            joblib.dump(var_dictDados, var_strCaminhoCompleto)
            logger.info(f"Modelo salvo em: {var_strCaminhoCompleto}")
            
            # Salvar também uma versão 'latest'
            var_strCaminhoLatest = os.path.join(var_pathDiretorio, f"{arg_strNomeModelo}_latest.joblib")
            joblib.dump(var_dictDados, var_strCaminhoLatest)
            logger.info(f"Versão 'latest' salva em: {var_strCaminhoLatest}")
            
            return str(var_strCaminhoCompleto)
            
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {str(e)}")
            raise
    
    @classmethod
    def carregar_modelo(cls, arg_strNomeModelo: str, arg_boolLatest: bool = True) -> Tuple[Any, Dict]:
        """
        Carrega um modelo salvo.

        Parâmetros:
        - arg_strNomeModelo (str): Nome do modelo a carregar.
        - arg_boolLatest (bool): Se True, carrega a versão 'latest'.

        Retorna:
        - Tuple[modelo, Dict]: Modelo carregado e suas métricas.
        """
        try:
            if arg_boolLatest:
                var_strCaminhoCompleto = os.path.join(cls.MODELS_DIR, f"{arg_strNomeModelo}_latest.joblib")
            else:
                # Buscar o arquivo mais recente
                var_pathDiretorio = Path(cls.MODELS_DIR)
                var_listArquivos = list(var_pathDiretorio.glob(f"{arg_strNomeModelo}_*.joblib"))
                if not var_listArquivos:
                    raise FileNotFoundError(f"Nenhum modelo encontrado com nome: {arg_strNomeModelo}")
                var_strCaminhoCompleto = str(max(var_listArquivos, key=os.path.getctime))
            
            if not os.path.exists(var_strCaminhoCompleto):
                raise FileNotFoundError(f"Modelo não encontrado: {var_strCaminhoCompleto}")
            
            var_dictDados = joblib.load(var_strCaminhoCompleto)
            logger.info(f"Modelo carregado de: {var_strCaminhoCompleto}")
            
            return var_dictDados['modelo'], var_dictDados.get('metricas', {})
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {str(e)}")
            raise

    # ================= Comparação de Modelos =================
    @classmethod
    def comparar_modelos(cls, arg_dfXTreino: DataFrame, arg_serYtreino: Series,
                        arg_dfXTeste: DataFrame, arg_serYteste: Series,
                        arg_listModelos: Optional[list] = None) -> DataFrame:
        """
        Treina e compara múltiplos modelos, retornando DataFrame com resultados.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        - arg_listModelos (list, optional): Lista de nomes de modelos para testar.

        Retorna:
        - DataFrame: Comparação dos modelos com métricas.
        """
        logger.info("="*60)
        logger.info("COMPARAÇÃO DE MODELOS")
        logger.info("="*60)
        
        # Modelos disponíveis
        var_dictModelosDisponiveis = {
            'LinearRegression': cls.var_molLinReg,
            'DecisionTree': cls.var_molDecTree,
            'RandomForest': cls.var_molRandForest,
            'GradientBoosting': cls.var_molGradBoost,
            'SVR': cls.var_molSVR,
            'Ridge': cls.var_molRidge,
            'Lasso': cls.var_molLasso
        }
        
        # Selecionar modelos a testar
        if arg_listModelos is None:
            arg_listModelos = list(var_dictModelosDisponiveis.keys())
        
        var_listResultados = []
        
        for var_strNomeModelo in arg_listModelos:
            if var_strNomeModelo not in var_dictModelosDisponiveis:
                logger.warning(f"Modelo {var_strNomeModelo} não disponível")
                continue
            
            logger.info(f"\nTreinando {var_strNomeModelo}...")
            var_objModelo = var_dictModelosDisponiveis[var_strNomeModelo]
            
            try:
                # Treinar modelo
                var_objModelo.fit(arg_dfXTreino, arg_serYtreino)
                
                # Fazer previsões
                var_arrayPredTreino = var_objModelo.predict(arg_dfXTreino)
                var_arrayPredTeste = var_objModelo.predict(arg_dfXTeste)
                
                # Calcular métricas
                var_dictMetricas = {
                    'Modelo': var_strNomeModelo,
                    'RMSE_Treino': np.sqrt(mean_squared_error(arg_serYtreino, var_arrayPredTreino)),
                    'RMSE_Teste': np.sqrt(mean_squared_error(arg_serYteste, var_arrayPredTeste)),
                    'MAE_Teste': mean_absolute_error(arg_serYteste, var_arrayPredTeste),
                    'R2_Teste': r2_score(arg_serYteste, var_arrayPredTeste)
                }
                
                var_listResultados.append(var_dictMetricas)
                
                logger.info(f"  RMSE Teste: {var_dictMetricas['RMSE_Teste']:.4f}")
                logger.info(f"  R² Teste: {var_dictMetricas['R2_Teste']:.4f}")
                
            except Exception as e:
                logger.error(f"Erro ao treinar {var_strNomeModelo}: {str(e)}")
                continue
        
        # Criar DataFrame com resultados
        var_dfResultados = pd.DataFrame(var_listResultados)
        var_dfResultados = var_dfResultados.sort_values('RMSE_Teste')
        
        logger.info("\n" + "="*60)
        logger.info("RESULTADOS DA COMPARAÇÃO")
        logger.info("="*60)
        logger.info(f"\n{var_dfResultados.to_string(index=False)}")
        logger.info("="*60)
        
        return var_dfResultados

    # ================= Tuning de Hiperparâmetros =================
    @classmethod
    def tunning_hiperparametros_grid(cls, arg_objModelo: Any, arg_dictParametros: Dict,
                                     arg_dfXTreino: DataFrame, arg_serYtreino: Series,
                                     arg_intCV: int = 5) -> Tuple[Any, Dict]:
        """
        Realiza tuning de hiperparâmetros usando GridSearchCV.

        Parâmetros:
        - arg_objModelo: Modelo base para tuning.
        - arg_dictParametros (Dict): Grid de parâmetros para testar.
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.
        - arg_intCV (int): Número de folds para validação cruzada.

        Retorna:
        - Tuple[modelo, Dict]: Melhor modelo encontrado e seus parâmetros.
        """
        logger.info(f"Iniciando GridSearchCV para {arg_objModelo.__class__.__name__}...")
        logger.info(f"Grid de parâmetros: {arg_dictParametros}")
        
        var_objGridSearch = GridSearchCV(
            estimator=arg_objModelo,
            param_grid=arg_dictParametros,
            cv=arg_intCV,
            scoring='neg_mean_squared_error',
            n_jobs=-1,
            verbose=1
        )
        
        var_objGridSearch.fit(arg_dfXTreino, arg_serYtreino)
        
        logger.info(f"Melhores parâmetros: {var_objGridSearch.best_params_}")
        logger.info(f"Melhor score: {-var_objGridSearch.best_score_:.4f}")
        
        return var_objGridSearch.best_estimator_, var_objGridSearch.best_params_
    
    @classmethod
    def tunning_hiperparametros_random(cls, arg_objModelo: Any, arg_dictParametros: Dict,
                                       arg_dfXTreino: DataFrame, arg_serYtreino: Series,
                                       arg_intIteracoes: int = 100, arg_intCV: int = 5) -> Tuple[Any, Dict]:
        """
        Realiza tuning de hiperparâmetros usando RandomizedSearchCV.

        Parâmetros:
        - arg_objModelo: Modelo base para tuning.
        - arg_dictParametros (Dict): Distribuição de parâmetros para testar.
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.
        - arg_intIteracoes (int): Número de iterações.
        - arg_intCV (int): Número de folds para validação cruzada.

        Retorna:
        - Tuple[modelo, Dict]: Melhor modelo encontrado e seus parâmetros.
        """
        logger.info(f"Iniciando RandomizedSearchCV para {arg_objModelo.__class__.__name__}...")
        logger.info(f"Distribuição de parâmetros: {arg_dictParametros}")
        logger.info(f"Iterações: {arg_intIteracoes}")
        
        var_objRandomSearch = RandomizedSearchCV(
            estimator=arg_objModelo,
            param_distributions=arg_dictParametros,
            n_iter=arg_intIteracoes,
            cv=arg_intCV,
            scoring='neg_mean_squared_error',
            n_jobs=-1,
            verbose=1,
            random_state=42
        )
        
        var_objRandomSearch.fit(arg_dfXTreino, arg_serYtreino)
        
        logger.info(f"Melhores parâmetros: {var_objRandomSearch.best_params_}")
        logger.info(f"Melhor score: {-var_objRandomSearch.best_score_:.4f}")
        
        return var_objRandomSearch.best_estimator_, var_objRandomSearch.best_params_
    
    @classmethod
    def obter_grids_parametros_padrao(cls, arg_strModelo: str) -> Dict:
        """
        Retorna grids de parâmetros padrão para modelos comuns.

        Parâmetros:
        - arg_strModelo (str): Nome do modelo.

        Retorna:
        - Dict: Grid de parâmetros para o modelo.
        """
        var_dictGrids = {
            'RandomForest': {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'GradientBoosting': {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.1, 0.2],
                'max_depth': [3, 5, 7],
                'min_samples_split': [2, 5, 10]
            },
            'SVR': {
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.001, 0.01],
                'kernel': ['rbf', 'linear']
            },
            'Ridge': {
                'alpha': [0.1, 1, 10, 100, 1000]
            },
            'Lasso': {
                'alpha': [0.1, 1, 10, 100, 1000]
            },
            'DecisionTree': {
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        }
        
        return var_dictGrids.get(arg_strModelo, {})
    
    # ================= Avaliação Detalhada de Modelos =================
    @classmethod
    def calcular_metricas_completas(cls, arg_serYreal: Series, arg_arrayYpred: np.ndarray,
                                    arg_strNomeModelo: str = "") -> Dict[str, float]:
        """
        Calcula um conjunto completo de métricas para avaliação de modelos.

        Parâmetros:
        - arg_serYreal (Series): Valores reais.
        - arg_arrayYpred (np.ndarray): Valores preditos.
        - arg_strNomeModelo (str): Nome do modelo para logging.

        Retorna:
        - Dict[str, float]: Dicionário com todas as métricas calculadas.
        """   
        var_dictMetricas = {
            'modelo': arg_strNomeModelo,
            'mse': mean_squared_error(arg_serYreal, arg_arrayYpred),
            'rmse': np.sqrt(mean_squared_error(arg_serYreal, arg_arrayYpred)),
            'mae': mean_absolute_error(arg_serYreal, arg_arrayYpred),
            'r2': r2_score(arg_serYreal, arg_arrayYpred),
            'median_ae': median_absolute_error(arg_serYreal, arg_arrayYpred),
            'max_error': max_error(arg_serYreal, arg_arrayYpred),
            'explained_variance': explained_variance_score(arg_serYreal, arg_arrayYpred)
        }
        
        # Métricas percentuais
        var_arrayErros = arg_serYreal - arg_arrayYpred
        var_dictMetricas['mape'] = np.mean(np.abs(var_arrayErros / (arg_serYreal + 1e-10))) * 100
        var_dictMetricas['std_erro'] = np.std(var_arrayErros)
        var_dictMetricas['mean_erro'] = np.mean(var_arrayErros)
        
        return var_dictMetricas
    
    @classmethod
    def avaliar_modelo_detalhado(cls, arg_objModelo: Any, arg_strNomeModelo: str,
                                 arg_dfXTreino: DataFrame, arg_serYtreino: Series,
                                 arg_dfXTeste: DataFrame, arg_serYteste: Series,
                                 arg_boolSalvar: bool = False) -> Dict[str, Any]:
        """
        Realiza avaliação detalhada de um modelo com métricas completas.

        Parâmetros:
        - arg_objModelo: Modelo treinado a avaliar.
        - arg_strNomeModelo (str): Nome do modelo.
        - arg_dfXTreino (DataFrame): Dados de treino.
        - arg_serYtreino (Series): Target de treino.
        - arg_dfXTeste (DataFrame): Dados de teste.
        - arg_serYteste (Series): Target de teste.
        - arg_boolSalvar (bool): Se True, salva o modelo.

        Retorna:
        - Dict: Dicionário com avaliação completa do modelo.
        """
        logger.info(f"{'='*60}")
        logger.info(f"AVALIAÇÃO DETALHADA: {arg_strNomeModelo}")
        logger.info(f"{'='*60}")
        
        # Previsões
        var_arrayPredTreino = arg_objModelo.predict(arg_dfXTreino)
        var_arrayPredTeste = arg_objModelo.predict(arg_dfXTeste)
        
        # Métricas de treino
        var_dictMetricasTreino = cls.calcular_metricas_completas(
            arg_serYtreino, var_arrayPredTreino, f"{arg_strNomeModelo}_treino"
        )
        
        # Métricas de teste
        var_dictMetricasTeste = cls.calcular_metricas_completas(
            arg_serYteste, var_arrayPredTeste, f"{arg_strNomeModelo}_teste"
        )
        
        # Detectar overfitting
        var_floatDiferencaR2 = var_dictMetricasTreino['r2'] - var_dictMetricasTeste['r2']
        var_floatDiferencaRMSE = var_dictMetricasTeste['rmse'] - var_dictMetricasTreino['rmse']
        
        var_boolOverfitting = (var_floatDiferencaR2 > 0.1) or (var_floatDiferencaRMSE > var_dictMetricasTreino['rmse'] * 0.2)
        
        # Compilar resultado
        var_dictResultado = {
            'modelo': arg_strNomeModelo,
            'metricas_treino': var_dictMetricasTreino,
            'metricas_teste': var_dictMetricasTeste,
            'overfitting_detectado': var_boolOverfitting,
            'diferenca_r2': var_floatDiferencaR2,
            'diferenca_rmse': var_floatDiferencaRMSE,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Logging detalhado
        logger.info(f"\nMÉTRICAS DE TREINO:")
        logger.info(f"  RMSE: {var_dictMetricasTreino['rmse']:.4f}")
        logger.info(f"  MAE: {var_dictMetricasTreino['mae']:.4f}")
        logger.info(f"  R²: {var_dictMetricasTreino['r2']:.4f}")
        
        logger.info(f"\nMÉTRICAS DE TESTE:")
        logger.info(f"  RMSE: {var_dictMetricasTeste['rmse']:.4f}")
        logger.info(f"  MAE: {var_dictMetricasTeste['mae']:.4f}")
        logger.info(f"  R²: {var_dictMetricasTeste['r2']:.4f}")
        logger.info(f"  MAPE: {var_dictMetricasTeste['mape']:.2f}%")
        logger.info(f"  Median AE: {var_dictMetricasTeste['median_ae']:.4f}")
        
        logger.info(f"\nANÁLISE DE OVERFITTING:")
        logger.info(f"  Diferença R²: {var_floatDiferencaR2:.4f}")
        logger.info(f"  Diferença RMSE: {var_floatDiferencaRMSE:.4f}")
        logger.info(f"  Overfitting: {'SIM' if var_boolOverfitting else 'NÃO'}")
        
        # Salvar modelo se solicitado
        if arg_boolSalvar:
            cls.salvar_modelo(arg_objModelo, arg_strNomeModelo, var_dictMetricasTeste)
            logger.info(f"\nModelo salvo com sucesso")
        
        logger.info(f"{'='*60}\n")
        
        return var_dictResultado
    
    @classmethod
    def avaliar_melhores_modelos(cls, arg_dfXTreino: DataFrame, arg_serYtreino: Series,
                                arg_dfXTeste: DataFrame, arg_serYteste: Series,
                                arg_intTopN: int = 3,
                                arg_boolSalvarMelhores: bool = True) -> Tuple[DataFrame, list[Dict]]:
        """
        Avalia todos os modelos, identifica os melhores e analisa seus erros detalhadamente.

        Parâmetros:
        - arg_dfXTreino (DataFrame): Dados de entrada para treinamento.
        - arg_serYtreino (Series): Valores alvo para treinamento.
        - arg_dfXTeste (DataFrame): Dados de entrada para teste.
        - arg_serYteste (Series): Valores alvo para teste.
        - arg_intTopN (int): Número de melhores modelos a analisar detalhadamente.
        - arg_boolSalvarMelhores (bool): Se True, salva os melhores modelos.

        Retorna:
        - Tuple[DataFrame, List[Dict]]: Comparação de modelos e avaliações detalhadas dos melhores.
        """
        logger.info(f"{'='*70}")
        logger.info(f"AVALIAÇÃO DOS MELHORES MODELOS (TOP {arg_intTopN})")
        logger.info(f"{'='*70}")
        
        # Primeiro fazer comparação geral
        var_dfComparacao = cls.comparar_modelos(
            arg_dfXTreino, arg_serYtreino,
            arg_dfXTeste, arg_serYteste
        )
        
        # Identificar top N modelos (menor RMSE = melhor)
        var_dfTopModelos = var_dfComparacao.head(arg_intTopN)
        var_listNomesTopModelos = var_dfTopModelos['Modelo'].tolist()
        
        logger.info(f"\nTOP {arg_intTopN} MODELOS IDENTIFICADOS:")
        for var_intIndex, var_strNome in enumerate(var_listNomesTopModelos, 1):
            var_dictInfo = var_dfTopModelos[var_dfTopModelos['Modelo'] == var_strNome].iloc[0]
            logger.info(f"  {var_intIndex}. {var_strNome}")
            logger.info(f"     RMSE: {var_dictInfo['RMSE_Teste']:.4f} | R²: {var_dictInfo['R2_Teste']:.4f}")
        
        # Avaliação detalhada dos melhores
        var_dictModelosDisponiveis = {
            'LinearRegression': cls.var_molLinReg,
            'DecisionTree': cls.var_molDecTree,
            'RandomForest': cls.var_molRandForest,
            'GradientBoosting': cls.var_molGradBoost,
            'SVR': cls.var_molSVR,
            'Ridge': cls.var_molRidge,
            'Lasso': cls.var_molLasso
        }
        
        var_listAvaliacoesDetalhadas = []
        
        logger.info(f"\n{'='*70}")
        logger.info(f"ANÁLISE DETALHADA DOS MELHORES MODELOS")
        logger.info(f"{'='*70}\n")
        
        for var_strNomeModelo in var_listNomesTopModelos:
            if var_strNomeModelo in var_dictModelosDisponiveis:
                var_objModelo = var_dictModelosDisponiveis[var_strNomeModelo]
                
                # Treinar o modelo novamente (se necessário)
                if not hasattr(var_objModelo, 'n_features_in_'):
                    var_objModelo.fit(arg_dfXTreino, arg_serYtreino)
                
                # Avaliação detalhada
                var_dictAvaliacao = cls.avaliar_modelo_detalhado(
                    var_objModelo, var_strNomeModelo,
                    arg_dfXTreino, arg_serYtreino,
                    arg_dfXTeste, arg_serYteste,
                    arg_boolSalvar=arg_boolSalvarMelhores
                )
                
                var_listAvaliacoesDetalhadas.append(var_dictAvaliacao)
        
        # Resumo final
        logger.info(f"{'='*70}")
        logger.info(f"RESUMO FINAL")
        logger.info(f"{'='*70}")
        logger.info(f"Total de modelos avaliados: {len(var_dfComparacao)}")
        logger.info(f"Modelos analisados em detalhe: {len(var_listAvaliacoesDetalhadas)}")
        
        var_strMelhorModelo = var_listNomesTopModelos[0]
        var_dictMelhorInfo = var_dfTopModelos.iloc[0]
        logger.info(f"\nMELHOR MODELO: {var_strMelhorModelo}")
        logger.info(f"   RMSE: {var_dictMelhorInfo['RMSE_Teste']:.4f}")
        logger.info(f"   MAE: {var_dictMelhorInfo['MAE_Teste']:.4f}")
        logger.info(f"   R²: {var_dictMelhorInfo['R2_Teste']:.4f}")
        logger.info(f"{'='*70}\n")
        
        return var_dfComparacao, var_listAvaliacoesDetalhadas
    
    @classmethod
    def avaliar_conjunto_testes(cls, arg_objModelo: Any, arg_strNomeModelo: str,
                               arg_dfXTeste: DataFrame, arg_serYteste: Series,
                               arg_boolGerarRelatorio: bool = True) -> Dict[str, Any]:
        """
        Avalia um modelo treinado em um conjunto de testes completo.

        Parâmetros:
        - arg_objModelo: Modelo treinado.
        - arg_strNomeModelo (str): Nome do modelo.
        - arg_dfXTeste (DataFrame): Conjunto de dados de teste.
        - arg_serYteste (Series): Valores alvo de teste.
        - arg_boolGerarRelatorio (bool): Se True, gera relatório detalhado.

        Retorna:
        - Dict: Resultado completo da avaliação no conjunto de testes.
        """
        logger.info(f"{'='*70}")
        logger.info(f"AVALIAÇÃO NO CONJUNTO DE TESTES")
        logger.info(f"Modelo: {arg_strNomeModelo}")
        logger.info(f"{'='*70}")
        
        # Informações do conjunto de testes
        logger.info(f"\nINFORMAÇÕES DO CONJUNTO DE TESTES:")
        logger.info(f"  Total de amostras: {len(arg_dfXTeste):,}")
        logger.info(f"  Número de features: {arg_dfXTeste.shape[1]}")
        logger.info(f"  Target - Média: {arg_serYteste.mean():.2f} | Std: {arg_serYteste.std():.2f}")
        logger.info(f"  Target - Min: {arg_serYteste.min():.2f} | Max: {arg_serYteste.max():.2f}")
        
        # Fazer previsões
        logger.info(f"\nRealizando previsões...")
        var_arrayPredTeste = arg_objModelo.predict(arg_dfXTeste)
        
        # Calcular métricas completas
        var_dictMetricas = cls.calcular_metricas_completas(
            arg_serYteste, var_arrayPredTeste, arg_strNomeModelo
        )
        
        # Análise de erros
        var_arrayErros = arg_serYteste.values - var_arrayPredTeste
        var_arrayErrosAbs = np.abs(var_arrayErros)
        var_arrayErrosPerc = np.abs(var_arrayErros / (arg_serYteste.values + 1e-10)) * 100
        
        # Estatísticas de erros
        var_dictEstatisticasErros = {
            'erro_medio': np.mean(var_arrayErros),
            'erro_mediano': np.median(var_arrayErros),
            'erro_std': np.std(var_arrayErros),
            'erro_abs_medio': np.mean(var_arrayErrosAbs),
            'erro_abs_mediano': np.median(var_arrayErrosAbs),
            'erro_max': np.max(var_arrayErrosAbs),
            'erro_min': np.min(var_arrayErrosAbs),
            'mape': np.mean(var_arrayErrosPerc)
        }
        
        # Distribuição de erros por faixas
        var_intErros_0_5 = np.sum(var_arrayErrosPerc <= 5)
        var_intErros_5_10 = np.sum((var_arrayErrosPerc > 5) & (var_arrayErrosPerc <= 10))
        var_intErros_10_20 = np.sum((var_arrayErrosPerc > 10) & (var_arrayErrosPerc <= 20))
        var_intErros_20_mais = np.sum(var_arrayErrosPerc > 20)
        
        var_dictDistribuicaoErros = {
            '0-5%': (var_intErros_0_5, var_intErros_0_5 / len(var_arrayErrosPerc) * 100),
            '5-10%': (var_intErros_5_10, var_intErros_5_10 / len(var_arrayErrosPerc) * 100),
            '10-20%': (var_intErros_10_20, var_intErros_10_20 / len(var_arrayErrosPerc) * 100),
            '>20%': (var_intErros_20_mais, var_intErros_20_mais / len(var_arrayErrosPerc) * 100)
        }
        
        # Compilar resultado final
        var_dictResultado = {
            'modelo': arg_strNomeModelo,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'tamanho_teste': len(arg_dfXTeste),
            'metricas': var_dictMetricas,
            'estatisticas_erros': var_dictEstatisticasErros,
            'distribuicao_erros': var_dictDistribuicaoErros,
            'predicoes': var_arrayPredTeste,
            'erros': var_arrayErros
        }
        
        # Exibir resultados
        if arg_boolGerarRelatorio:
            logger.info(f"\nMÉTRICAS DE DESEMPENHO:")
            logger.info(f"  RMSE: {var_dictMetricas['rmse']:.4f}")
            logger.info(f"  MAE: {var_dictMetricas['mae']:.4f}")
            logger.info(f"  R²: {var_dictMetricas['r2']:.4f}")
            logger.info(f"  MAPE: {var_dictMetricas['mape']:.2f}%")
            logger.info(f"  Explained Variance: {var_dictMetricas['explained_variance']:.4f}")
            
            logger.info(f"\nESTATÍSTICAS DE ERROS:")
            logger.info(f"  Erro Médio: {var_dictEstatisticasErros['erro_medio']:.4f}")
            logger.info(f"  Erro Mediano: {var_dictEstatisticasErros['erro_mediano']:.4f}")
            logger.info(f"  Desvio Padrão: {var_dictEstatisticasErros['erro_std']:.4f}")
            logger.info(f"  MAE: {var_dictEstatisticasErros['erro_abs_medio']:.4f}")
            logger.info(f"  Erro Máximo: {var_dictEstatisticasErros['erro_max']:.4f}")
            
            logger.info(f"\nDISTRIBUIÇÃO DE ERROS PERCENTUAIS:")
            for var_strFaixa, (var_intCount, var_floatPerc) in var_dictDistribuicaoErros.items():
                logger.info(f"  {var_strFaixa}: {var_intCount:,} amostras ({var_floatPerc:.1f}%)")
            
            # Avaliação da qualidade
            if var_dictMetricas['r2'] > 0.9:
                var_strQualidade = "EXCELENTE"
            elif var_dictMetricas['r2'] > 0.8:
                var_strQualidade = "MUITO BOM"
            elif var_dictMetricas['r2'] > 0.7:
                var_strQualidade = "BOM"
            elif var_dictMetricas['r2'] > 0.5:
                var_strQualidade = "REGULAR"
            else:
                var_strQualidade = "FRACO"
            
            logger.info(f"\nQUALIDADE DO MODELO: {var_strQualidade}")
            logger.info(f"   (baseado em R² = {var_dictMetricas['r2']:.4f})")
        
        logger.info(f"\n{'='*70}\n")
        
        return var_dictResultado
    
    @classmethod
    def gerar_relatorio_avaliacao(cls, arg_dictResultadoAvaliacao: Dict,
                                  arg_strCaminhoSaida: Optional[str] = None) -> str:
        """
        Gera um relatório detalhado de avaliação em formato texto.

        Parâmetros:
        - arg_dictResultadoAvaliacao (Dict): Resultado da avaliação.
        - arg_strCaminhoSaida (str, optional): Caminho para salvar o relatório.

        Retorna:
        - str: Conteúdo do relatório.
        """
        var_strRelatorio = []
        var_strRelatorio.append("=" * 80)
        var_strRelatorio.append("RELATÓRIO DE AVALIAÇÃO DE MODELO")
        var_strRelatorio.append("=" * 80)
        var_strRelatorio.append(f"\nModelo: {arg_dictResultadoAvaliacao['modelo']}")
        var_strRelatorio.append(f"Data/Hora: {arg_dictResultadoAvaliacao['timestamp']}")
        var_strRelatorio.append(f"Tamanho do Conjunto de Testes: {arg_dictResultadoAvaliacao['tamanho_teste']:,} amostras")
        
        var_strRelatorio.append(f"\n{'='*80}")
        var_strRelatorio.append("MÉTRICAS DE DESEMPENHO")
        var_strRelatorio.append("=" * 80)
        
        var_dictMetricas = arg_dictResultadoAvaliacao['metricas']
        var_strRelatorio.append(f"\nMSE (Mean Squared Error):        {var_dictMetricas['mse']:.6f}")
        var_strRelatorio.append(f"RMSE (Root Mean Squared Error):  {var_dictMetricas['rmse']:.6f}")
        var_strRelatorio.append(f"MAE (Mean Absolute Error):       {var_dictMetricas['mae']:.6f}")
        var_strRelatorio.append(f"R² Score:                        {var_dictMetricas['r2']:.6f}")
        var_strRelatorio.append(f"MAPE (Mean Abs. Perc. Error):    {var_dictMetricas['mape']:.2f}%")
        var_strRelatorio.append(f"Median Absolute Error:           {var_dictMetricas['median_ae']:.6f}")
        var_strRelatorio.append(f"Max Error:                       {var_dictMetricas['max_error']:.6f}")
        var_strRelatorio.append(f"Explained Variance Score:        {var_dictMetricas['explained_variance']:.6f}")
        
        var_strRelatorio.append(f"\n{'='*80}")
        var_strRelatorio.append("ESTATÍSTICAS DE ERROS")
        var_strRelatorio.append("=" * 80)
        
        var_dictEstats = arg_dictResultadoAvaliacao['estatisticas_erros']
        var_strRelatorio.append(f"\nErro Médio:                      {var_dictEstats['erro_medio']:.6f}")
        var_strRelatorio.append(f"Erro Mediano:                    {var_dictEstats['erro_mediano']:.6f}")
        var_strRelatorio.append(f"Desvio Padrão do Erro:           {var_dictEstats['erro_std']:.6f}")
        var_strRelatorio.append(f"Erro Absoluto Médio:             {var_dictEstats['erro_abs_medio']:.6f}")
        var_strRelatorio.append(f"Erro Absoluto Mediano:           {var_dictEstats['erro_abs_mediano']:.6f}")
        var_strRelatorio.append(f"Erro Máximo:                     {var_dictEstats['erro_max']:.6f}")
        var_strRelatorio.append(f"Erro Mínimo:                     {var_dictEstats['erro_min']:.6f}")
        
        var_strRelatorio.append(f"\n{'='*80}")
        var_strRelatorio.append("DISTRIBUIÇÃO DE ERROS PERCENTUAIS")
        var_strRelatorio.append("=" * 80)
        
        var_dictDist = arg_dictResultadoAvaliacao['distribuicao_erros']
        var_strRelatorio.append(f"\n0-5%:    {var_dictDist['0-5%'][0]:,} amostras ({var_dictDist['0-5%'][1]:.1f}%)")
        var_strRelatorio.append(f"5-10%:   {var_dictDist['5-10%'][0]:,} amostras ({var_dictDist['5-10%'][1]:.1f}%)")
        var_strRelatorio.append(f"10-20%:  {var_dictDist['10-20%'][0]:,} amostras ({var_dictDist['10-20%'][1]:.1f}%)")
        var_strRelatorio.append(f">20%:    {var_dictDist['>20%'][0]:,} amostras ({var_dictDist['>20%'][1]:.1f}%)")
        
        var_strRelatorio.append(f"\n{'='*80}\n")
        
        var_strConteudo = "\n".join(var_strRelatorio)
        
        # Salvar em arquivo se caminho fornecido
        if arg_strCaminhoSaida:
            try:
                var_pathDiretorio = Path(arg_strCaminhoSaida).parent
                var_pathDiretorio.mkdir(parents=True, exist_ok=True)
                
                with open(arg_strCaminhoSaida, 'w', encoding='utf-8') as f:
                    f.write(var_strConteudo)
                
                logger.info(f"Relatório salvo em: {arg_strCaminhoSaida}")
            except Exception as e:
                logger.error(f"Erro ao salvar relatório: {str(e)}")
        
        return var_strConteudo