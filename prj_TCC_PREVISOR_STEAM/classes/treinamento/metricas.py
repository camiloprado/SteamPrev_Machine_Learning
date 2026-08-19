from prj_TCC_PREVISOR_STEAM.classes.treinamento.plots import Plots
import logging
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    f1_score,
    root_mean_squared_error,
    confusion_matrix,
)
import pandas as pd
from datetime import datetime

logger = logging.getLogger("treino.metricas")

class Metricas:
    @staticmethod
    def _metricas_classificacao(arg_arrReal, arg_arrPred) -> dict:
        """
        Calcula métricas de classificação e indicadores de erro.

        Parâmetros:
        - arg_arrReal (array-like): Array de rótulos reais.
        - arg_arrPred (array-like): Array de rótulos preditos.

        Retorna:
        - dict: Dicionário contendo as métricas de acurácia, precisão macro, F1-macro, contagem de erros e taxa de erro.
        """
        # Calcula acurácia global: quantos acertou no total (TP+TN) dividido pelo total de amostras
        var_floatAcc = accuracy_score(arg_arrReal, arg_arrPred)
        
        # Calcula precisão média entre as 3 classes (cai/mantem/sobe)
        # average="macro" = trata cada classe igualmente (não importa frequência)
        var_floatPrecision = precision_score(arg_arrReal, arg_arrPred, average="macro", zero_division=0)
        
        # Calcula F1-score macro (balanço entre Precisão e Recall)
        var_floatF1 = f1_score(arg_arrReal, arg_arrPred, average="macro")
        
        # Conta quantas predições ficaram erradas (verdadeiro != predito)
        var_intErros = int((arg_arrReal != arg_arrPred).sum())
        
        # Taxa de erro: porcentagem de erros = 1 - acurácia
        var_floatErroTaxa = 1.0 - var_floatAcc

        # Retorna dicionário com todas as métricas para uso posterior
        return {
            "accuracy": var_floatAcc,           # Taxa global de acerto
            "precision_macro": var_floatPrecision,  # Precisão equilibrada entre classes
            "f1_macro": var_floatF1,           # Score F1 equilibrado
            "error_count": var_intErros,       # Contagem absoluta de erros
            "error_rate": var_floatErroTaxa,   # Taxa relativa de erros (%)
        }


    @staticmethod
    def _metricas_regressao(arg_arrReal, arg_arrPred) -> dict:
        """
        Calcula métricas de regressão (erro contínuo).

        Parâmetros:
        - arg_arrReal (array-like): Array de valores reais (dias até desconto).
        - arg_arrPred (array-like): Array de valores preditos.

        Retorna:
        - dict: Dicionário contendo RMSE, MAE, MSE.
        """
        # Calcula RMSE (Raiz do Erro Quadrático Médio) - MÉTRICA PRINCIPAL
        if root_mean_squared_error is not None:
            var_floatRmse = root_mean_squared_error(arg_arrReal, arg_arrPred)
        else:
            var_floatRmse = mean_squared_error(arg_arrReal, arg_arrPred) ** 0.5

        # Calcula MAE (Erro Médio Absoluto) - mais robusto a outliers
        var_floatMae = mean_absolute_error(arg_arrReal, arg_arrPred)
        
        # Calcula MSE (Erro Quadrático Médio) - penaliza erros grandes
        var_floatMse = mean_squared_error(arg_arrReal, arg_arrPred)

        return {
            "rmse": var_floatRmse,  # Interpretável em "dias"
            "mae": var_floatMae,    # Erro médio absoluto
            "mse": var_floatMse,    # Erro quadrático
        }


    @classmethod
    def _log_confusion_matrix(cls, arg_strModelo: str, arg_arrYTrue, arg_arrYPred, arg_listLabels=None, arg_listLabelNames=None, arg_strSplit: str = "teste", arg_boolSalvarCsv: bool = True) -> None:
        """
        Calcula e registra a matriz de confusão (contagens e normalizada).
        Opcionalmente salva CSVs em resources/relatorios.

        Parâmetros:
        - arg_strModelo (str): Nome do modelo para contextualizar o log.
        - arg_arrYTrue (array-like): Array de rótulos verdadeiros.
        - arg_arrYPred (array-like): Array de rótulos preditos.
        - arg_listLabels (list, opcional): Lista de rótulos/classes para a matriz. Se None, inferida do arg_arrYTrue.
        - arg_listLabelNames (list, opcional): Lista de nomes para os rótulos/classes. Se None, usa os rótulos como nomes.
        - arg_strSplit (str, opcional): Identificador do split (ex: "teste", "treino") para contextualizar o log e nome do arquivo. (default: "teste")
        - arg_boolSalvarCsv (bool, opcional): Se True, salva os CSVs da matriz de confusão em resources/relatorios. (default: True)

        Retorna:
        """
        try:
            var_objConfusionMatrix = confusion_matrix(arg_arrYTrue, arg_arrYPred, labels=arg_listLabels)
        except Exception as e:
            logger.warning(f"Não foi possível calcular matriz de confusão para {arg_strModelo}: {e}")
            return

        # Constrói DataFrame para exibição
        if arg_listLabelNames is None and arg_listLabels is not None:
            arg_listLabelNames = [str(var_strLabel) for var_strLabel in arg_listLabels]
        if arg_listLabelNames is None:
            # tenta inferir do y_true
            arg_listLabelNames = sorted(list(pd.Series(arg_arrYTrue).dropna().unique()))

        var_strTs = datetime.now().strftime("%Y%m%d")
        try:
            var_dfConfusionMatrix = pd.DataFrame(var_objConfusionMatrix, index=arg_listLabelNames, columns=arg_listLabelNames)
            logger.info(f"Matriz de confusão ({arg_strModelo} | {arg_strSplit}) - contagens:\n\n%s", var_dfConfusionMatrix.to_string())

            # Normalizada por verdadeiros (linhas)
            var_arrDen = var_objConfusionMatrix.sum(axis=1, keepdims=True)
            try:
                var_arrDen[var_arrDen == 0] = 1
            except Exception:
                pass

            var_arrNorm = var_objConfusionMatrix.astype(float) / var_arrDen
            var_dfConfusionMatrixNorm = pd.DataFrame(var_arrNorm, index=arg_listLabelNames, columns=arg_listLabelNames)

            with pd.option_context("display.float_format", "{:0.4f}".format):
                logger.info(
                    f"Matriz de confusão ({arg_strModelo} | {arg_strSplit}) - normalizada por classe (linhas):\n\n%s",
                    var_dfConfusionMatrixNorm.to_string(),
                )

            if arg_boolSalvarCsv:
                var_pathRelatorios = Plots._obter_diretorio_relatorios()
                var_strBaseName = f"confusion_{arg_strModelo}_{arg_strSplit}_{var_strTs}"

                var_pathCounts = var_pathRelatorios / f"{var_strBaseName}_counts.csv"
                var_pathNorm = var_pathRelatorios / f"{var_strBaseName}_norm.csv"

                var_dfConfusionMatrix.to_csv(var_pathCounts, index=True)
                var_dfConfusionMatrixNorm.to_csv(var_pathNorm, index=True)

                logger.info(f"CSV matriz de confusão salvo: {var_pathCounts}")
                logger.info(f"CSV matriz de confusão (normalizada) salvo: {var_pathNorm}")

            # Plot (opt-in) para uso em artigo
            try:
                var_boolSalvarPng, var_boolMostrar, var_intDpi = Plots._obter_config_plots("matriz_confusao")
                if var_boolSalvarPng or var_boolMostrar:
                    Plots._plot_confusion_matrix(
                        arg_strModelo=arg_strModelo,
                        arg_strSplit=arg_strSplit,
                        arg_arrCounts=var_objConfusionMatrix,
                        arg_arrNorm=var_arrNorm,
                        arg_listLabelNames=arg_listLabelNames,
                        arg_strTs=var_strTs,
                        arg_boolSalvarPng=var_boolSalvarPng,
                        arg_boolMostrar=var_boolMostrar,
                        arg_intDpi=var_intDpi,
                    )
            except Exception as e:
                logger.warning(f"Falha ao configurar plot da matriz de confusão ({arg_strModelo}): {e}")
        except Exception as e:
            # Fallback texto simples
            logger.info(f"Matriz de confusão ({arg_strModelo} | {arg_strSplit}): {var_objConfusionMatrix.tolist()}")
            logger.warning(f"Falha ao formatar/salvar matriz de confusão ({arg_strModelo}): {e}")


    @classmethod
    def _log_metricas_treino_teste_classificacao(cls, arg_strModelo: str, arg_yTrain, arg_yPredTrain, arg_yTest, arg_yPredTest) -> None:
        """
        Registra métricas comparando treino vs teste para detectar overfitting.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo para contextualizar o log.
        - arg_yTrain (array-like): Rótulos reais do conjunto de treino.
        - arg_yPredTrain (array-like): Rótulos preditos do conjunto de treino.
        - arg_yTest (array-like): Rótulos reais do conjunto de teste.
        - arg_yPredTest (array-like): Rótulos preditos do conjunto de teste.

        Retorna:
        """
        try:
            # Calcula métricas NO CONJUNTO DE TREINO (dados que o modelo viu)
            var_dictTrain = Metricas._metricas_classificacao(arg_yTrain, arg_yPredTrain)
            
            # Calcula métricas NO CONJUNTO DE TESTE (dados novos, nunca vistos)
            var_dictTest = Metricas._metricas_classificacao(arg_yTest, arg_yPredTest)
        except Exception as e:
            # Se algo der errado, registra aviso e sai da função
            logger.warning(f"Não foi possível calcular métricas treino/teste ({arg_strModelo}): {e}")
            return

        # DETECÇÃO DE OVERFITTING: calcula diferença de acurácia entre treino e teste
        # Quanto maior a diferença, mais o modelo "decorou" em vez de "aprender"
        var_floatDiferencaAcc = abs(var_dictTrain['accuracy'] - var_dictTest['accuracy'])
        
        # Classificação automática do status de overfitting
        if var_floatDiferencaAcc < 0.03:  # < 3% de diferença
            var_strOverfitting = " Estável"  # Modelo generaliza bem
        elif var_floatDiferencaAcc >= 0.05:  # ≥ 5% de diferença
            var_strOverfitting = " Overfitting detectado"  # Problema sério
        else:  # 3-5% de diferença
            var_strOverfitting = " Possível overfitting"  # Zona cinzenta
        
        # LOG TREINO: mostra performance no conjunto que o modelo utilizou para aprender
        logger.info(
            f"{arg_strModelo} - TREINO: Acc={var_dictTrain['accuracy']:.4f} | "
            f"Prec={var_dictTrain['precision_macro']:.4f} | F1={var_dictTrain['f1_macro']:.4f}"
        )
        
        # LOG TESTE: mostra performance em dados novos + STATUS DE OVERFITTING
        logger.info(
            f"{arg_strModelo} - TESTE : Acc={var_dictTest['accuracy']:.4f} | "
            f"Prec={var_dictTest['precision_macro']:.4f} | F1={var_dictTest['f1_macro']:.4f} | {var_strOverfitting}"
        )


    @classmethod
    def _log_metricas_treino_teste_regressao(cls, arg_strModelo: str, arg_yTrain, arg_yPredTrain, arg_yTest, arg_yPredTest, arg_strAlvo: str = "dias") -> None:
        """
        Registra métricas (RMSE/MAE/MSE) em treino e teste.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo para contextualizar o log.
        - arg_yTrain (array-like): Valores reais do conjunto de treino.
        - arg_yPredTrain (array-like): Valores preditos do conjunto de treino.
        - arg_yTest (array-like): Valores reais do conjunto de teste.
        - arg_yPredTest (array-like): Valores preditos do conjunto de teste.
        - arg_strAlvo (str): Alvo da predição ("dias" ou "desconto").
        """
        try:
            if root_mean_squared_error is not None:
                var_floatRmseTrain = root_mean_squared_error(arg_yTrain, arg_yPredTrain)
                var_floatRmseTest = root_mean_squared_error(arg_yTest, arg_yPredTest)
            else:
                var_floatRmseTrain = mean_squared_error(arg_yTrain, arg_yPredTrain) ** 0.5
                var_floatRmseTest = mean_squared_error(arg_yTest, arg_yPredTest) ** 0.5

            var_floatMseTrain = mean_squared_error(arg_yTrain, arg_yPredTrain)
            var_floatMseTest = mean_squared_error(arg_yTest, arg_yPredTest)
            var_floatMaeTrain = mean_absolute_error(arg_yTrain, arg_yPredTrain)
            var_floatMaeTest = mean_absolute_error(arg_yTest, arg_yPredTest)
        except Exception as e:
            logger.warning(f"Não foi possível calcular métricas de regressão ({arg_strModelo}): {e}")
            return

        var_strUnidade = "%" if arg_strAlvo == "desconto" else "dias"
        
        logger.info(
            f"{arg_strModelo} - TREINO | RMSE: {var_floatRmseTrain:.2f} {var_strUnidade} | MAE: {var_floatMaeTrain:.2f} {var_strUnidade} | MSE: {var_floatMseTrain:.2f}"
        )
        logger.info(
            f"{arg_strModelo} - TESTE  | RMSE: {var_floatRmseTest:.2f} {var_strUnidade} | MAE: {var_floatMaeTest:.2f} {var_strUnidade} | MSE: {var_floatMseTest:.2f}"
        )


