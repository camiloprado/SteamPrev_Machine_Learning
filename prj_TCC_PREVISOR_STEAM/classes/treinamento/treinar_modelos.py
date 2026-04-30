from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.treinamento.normalizar_modelos import NormalizarModelos
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    f1_score,
    root_mean_squared_error,
    confusion_matrix,
)

import xgboost as xgb
import lightgbm as lgb
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

import logging

logger = logging.getLogger(__name__)

class Treinar_Modelos:
    """
    Classe responsável por unificar o treinamento entre os diversos modelos preditivos utilizados no projeto.
    """

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
        var_floatAcc = accuracy_score(arg_arrReal, arg_arrPred)
        var_floatPrecision = precision_score(arg_arrReal, arg_arrPred, average="macro", zero_division=0)
        var_floatF1 = f1_score(arg_arrReal, arg_arrPred, average="macro")
        var_intErros = int((arg_arrReal != arg_arrPred).sum())
        var_floatErroTaxa = 1.0 - var_floatAcc

        return {
            "accuracy": var_floatAcc,
            "precision_macro": var_floatPrecision,
            "f1_macro": var_floatF1,
            "error_count": var_intErros,
            "error_rate": var_floatErroTaxa,
        }

    @classmethod
    def _obter_diretorio_relatorios(cls) -> Path:
        """
        Obtém o diretório padrão do projeto para relatórios (resources/relatorios).
        
        Retorna:
        - Path: Objeto Path do diretório de relatórios, garantindo que exista.
        """
        var_pathBase = Path(__file__).resolve().parents[2]
        var_pathRelatorios = var_pathBase / "resources" / "relatorios"
        var_pathRelatorios.mkdir(parents=True, exist_ok=True)
        return var_pathRelatorios

    @staticmethod
    def _obter_config_plot_matriz_confusao() -> tuple[bool, bool, int]:
        """Define se deve gerar plot da matriz de confusão.

        Retorna:
        - (salvar_png, mostrar, dpi)
        """
        var_strMode = (os.getenv("MATRIZ_CONFUSAO_PLOT", "") or "").strip().lower()
        var_strDpi = (os.getenv("MATRIZ_CONFUSAO_PLOT_DPI", "") or "").strip()

        var_intDpi = 300
        try:
            if var_strDpi:
                var_intDpi = int(var_strDpi)
        except Exception:
            var_intDpi = 300

        if var_strMode in ("", "0", "false", "no", "nao"):
            return (False, False, var_intDpi)

        if var_strMode in ("show", "mostrar"):
            return (False, True, var_intDpi)

        if var_strMode in ("both", "save_show", "save+show", "salvar_mostrar"):
            return (True, True, var_intDpi)

        # Default para modos "1"/"true"/"save"/"salvar" => salvar PNG
        return (True, False, var_intDpi)

    @classmethod
    def _plot_confusion_matrix(cls, arg_strModelo: str, arg_strSplit: str, arg_arrCounts, arg_arrNorm, arg_listLabelNames, arg_strTs: str, arg_boolSalvarPng: bool, arg_boolMostrar: bool, arg_intDpi: int) -> None:
        """
        Gera um plot da matriz de confusão (heatmap) via Matplotlib.

        Parâmetros:
        - arg_strModelo (str): Nome do modelo para contextualizar o título do plot.
        - arg_strSplit (str): Identificador do split (ex: "teste", "treino") para contextualizar o título do plot.
        - arg_arrCounts (array-like): Matriz de confusão com contagens absolutas.
        - arg_arrNorm (array-like): Matriz de confusão normalizada (por exemplo, por linha).
        - arg_listLabelNames (list): Lista de nomes para os rótulos/classes, usada nos ticks do plot.
        - arg_strTs (str): Timestamp para contextualizar o título do plot e nome do arquivo.
        - arg_boolSalvarPng (bool): Se True, salva o plot como PNG em resources/relatorios.
        - arg_boolMostrar (bool): Se True, exibe o plot na tela.
        - arg_intDpi (int): DPI para salvar o PNG (se arg_boolSalvarPng for True).

        Retorna:
        """
        try:
            # Se vamos apenas salvar (sem mostrar), garante backend não-interativo.
            if arg_boolSalvarPng and not arg_boolMostrar:
                import matplotlib

                matplotlib.use("Agg")

            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            logger.warning(f"Matplotlib indisponível para plotar matriz de confusão ({arg_strModelo}): {e}")
            return

        try:
            var_arrCounts = np.asarray(arg_arrCounts)
            var_arrNorm = np.asarray(arg_arrNorm)
            var_intN = int(var_arrCounts.shape[0])
            var_strFigSize = os.getenv("MATRIZ_CONFUSAO_PLOT_FIGSIZE", "7.5,6.0").split(",")
            var_objFig, var_objAxes = plt.subplots(figsize=(float(var_strFigSize[0]), float(var_strFigSize[1])), dpi=max(72, int(arg_intDpi)))
            var_objImage = var_objAxes.imshow(var_arrNorm, interpolation="nearest", cmap="Blues", vmin=0.0, vmax=1.0)
            var_objAxes.figure.colorbar(var_objImage, ax=var_objAxes, fraction=0.046, pad=0.04)

            var_objAxes.set(
                xticks=list(range(var_intN)),
                yticks=list(range(var_intN)),
                xticklabels=arg_listLabelNames,
                yticklabels=arg_listLabelNames,
                ylabel="Verdadeiro",
                xlabel="Predito",
                title=f"Matriz de Confusão - {arg_strModelo} ({arg_strSplit})",
            )

            plt.setp(var_objAxes.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor")

            # Anotações: contagem + porcentagem (normalizada por linha)
            for var_intI in range(var_intN):
                for var_intJ in range(var_intN):
                    var_intCount = int(var_arrCounts[var_intI, var_intJ])
                    try:
                        var_floatPct = float(var_arrNorm[var_intI, var_intJ])
                    except Exception:
                        var_floatPct = 0.0

                    var_strText = f"{var_intCount:,}\n({var_floatPct:.1%})"
                    var_strColor = "white" if var_floatPct >= 0.50 else "black"
                    var_objAxes.text(var_intJ, var_intI, var_strText, ha="center", va="center", color=var_strColor, fontsize=8)

            var_objFig.tight_layout()

            if arg_boolSalvarPng:
                var_pathRelatorios = cls._obter_diretorio_relatorios()
                var_strBaseName = f"confusion_{arg_strModelo}_{arg_strSplit}_{arg_strTs}"
                var_pathPng = var_pathRelatorios / f"{var_strBaseName}_plot.png"
                var_objFig.savefig(var_pathPng, dpi=max(72, int(arg_intDpi)))
                logger.info(f"PNG matriz de confusão salvo: {var_pathPng}")

            if arg_boolMostrar:
                plt.show()
        except Exception as e:
            logger.warning(f"Falha ao gerar plot da matriz de confusão ({arg_strModelo}): {e}")
        finally:
            try:
                plt.close("all")
            except Exception:
                pass

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

        var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
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
                var_pathRelatorios = cls._obter_diretorio_relatorios()
                var_strBaseName = f"confusion_{arg_strModelo}_{arg_strSplit}_{var_strTs}"

                var_pathCounts = var_pathRelatorios / f"{var_strBaseName}_counts.csv"
                var_pathNorm = var_pathRelatorios / f"{var_strBaseName}_norm.csv"

                var_dfConfusionMatrix.to_csv(var_pathCounts, index=True)
                var_dfConfusionMatrixNorm.to_csv(var_pathNorm, index=True)

                logger.info(f"CSV matriz de confusão salvo: {var_pathCounts}")
                logger.info(f"CSV matriz de confusão (normalizada) salvo: {var_pathNorm}")

            # Plot (opt-in) para uso em artigo
            try:
                var_boolSalvarPng, var_boolMostrar, var_intDpi = cls._obter_config_plot_matriz_confusao()
                if var_boolSalvarPng or var_boolMostrar:
                    cls._plot_confusion_matrix(
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
            var_dictTrain = cls._metricas_classificacao(arg_yTrain, arg_yPredTrain)
            var_dictTest = cls._metricas_classificacao(arg_yTest, arg_yPredTest)
        except Exception as e:
            logger.warning(f"Não foi possível calcular métricas treino/teste ({arg_strModelo}): {e}")
            return

        logger.info(
            f"{arg_strModelo} (direção de preço) - TREINO | "
            f"ACC: {var_dictTrain['accuracy']:.4f} | "
            f"Precisão(macro): {var_dictTrain['precision_macro']:.4f} | "
            f"F1-macro: {var_dictTrain['f1_macro']:.4f} | "
            f"Erros: {var_dictTrain['error_count']:,} ({var_dictTrain['error_rate']:.4f})"
        )
        logger.info(
            f"{arg_strModelo} (direção de preço) - TESTE  | "
            f"ACC: {var_dictTest['accuracy']:.4f} | "
            f"Precisão(macro): {var_dictTest['precision_macro']:.4f} | "
            f"F1-macro: {var_dictTest['f1_macro']:.4f} | "
            f"Erros: {var_dictTest['error_count']:,} ({var_dictTest['error_rate']:.4f})"
        )

    @classmethod
    def _log_metricas_treino_teste_regressao(cls, arg_strModelo: str, arg_yTrain, arg_yPredTrain, arg_yTest, arg_yPredTest) -> None:
        """
        Registra métricas (RMSE/MAE/MSE) em treino e teste.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo para contextualizar o log.
        - arg_yTrain (array-like): Valores reais do conjunto de treino.
        - arg_yPredTrain (array-like): Valores preditos do conjunto de treino.
        - arg_yTest (array-like): Valores reais do conjunto de teste.
        - arg_yPredTest (array-like): Valores preditos do conjunto de teste.

        Retorna:
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

        logger.info(
            f"{arg_strModelo} - TREINO | RMSE: {var_floatRmseTrain:.2f} dias | MAE: {var_floatMaeTrain:.2f} dias | MSE: {var_floatMseTrain:.2f}"
        )
        logger.info(
            f"{arg_strModelo} - TESTE  | RMSE: {var_floatRmseTest:.2f} dias | MAE: {var_floatMaeTest:.2f} dias | MSE: {var_floatMseTest:.2f}"
        )
    
    @classmethod
    def treinar_modelo_regressao_linear(cls) -> dict:
        """
        Método para treinar o modelo de Regressão Linear.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits()

        var_objModelo = LinearRegression()
        var_objModelo.fit(var_dictSplits["Xr_train"], var_dictSplits["yr_train"])
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["Xr_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["Xr_test"])

        if root_mean_squared_error is not None:
            var_floatRmse = root_mean_squared_error(var_dictSplits["yr_test"], var_arrPredTest)
        else:
            # Compatibilidade com versões antigas do sklearn sem root_mean_squared_error.
            var_floatRmse = mean_squared_error(var_dictSplits["yr_test"], var_arrPredTest) ** 0.5

        var_floatMse = mean_squared_error(var_dictSplits["yr_test"], var_arrPredTest)
        var_floatMae = mean_absolute_error(var_dictSplits["yr_test"], var_arrPredTest)

        cls._log_metricas_treino_teste_regressao(
            arg_strModelo="Regressão Linear (dias até desconto)",
            arg_yTrain=var_dictSplits["yr_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["yr_test"],
            arg_yPredTest=var_arrPredTest,
        )

        logger.info(
            "Regressão linear (dias até desconto) - "
            f"RMSE: {var_floatRmse:.2f} dias | "
            f"MAE: {var_floatMae:.2f} dias | "
            f"MSE: {var_floatMse:.2f}"
        )
        return {
            "modelo": var_objModelo,
            "rmse": var_floatRmse,
            "mae": var_floatMae,
            "mse": var_floatMse,
            "train_size": var_dictSplits["Xr_train"].shape[0],
            "test_size": var_dictSplits["Xr_test"].shape[0],
        }

    @classmethod
    def treinar_modelo_random_forest(cls) -> dict:
        """
        Método para treinar o modelo de Random Forest.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits()

        var_objModelo = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            n_jobs=-1,
            random_state=42,
        )
        var_objModelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = cls._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        cls._log_metricas_treino_teste_classificacao(
            arg_strModelo="Random Forest",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        cls._log_confusion_matrix(
            arg_strModelo="RandomForest",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
            arg_strSplit="teste"
        )

        logger.info(
            "Random Forest (direção de preço) - "
            f"ACC: {var_dictMetricas['accuracy']:.4f} | "
            f"Precisão(macro): {var_dictMetricas['precision_macro']:.4f} | "
            f"F1-macro: {var_dictMetricas['f1_macro']:.4f} | "
            f"Erros: {var_dictMetricas['error_count']:,} ({var_dictMetricas['error_rate']:.4f})"
        )
        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dictSplits["X_train"].shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }

    @classmethod
    def treinar_modelo_xgboost(cls) -> dict:
        """
        Método para treinar o modelo de XGBoost.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits()

        var_objModelo = xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            n_estimators=300,
            learning_rate=0.05,
            max_depth=8,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )

        # Early stopping (quando suportado)
        try:
            var_objModelo.fit(
                var_dictSplits["X_train"],
                var_dictSplits["y_train"],
                eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],
                verbose=False,
                early_stopping_rounds=50,
            )
        except TypeError:
            var_objModelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])

        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = cls._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        cls._log_metricas_treino_teste_classificacao(
            arg_strModelo="XGBoost",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        var_intBestIter = getattr(var_objModelo, "best_iteration", None)
        if var_intBestIter is not None:
            logger.info(f"XGBoost - best_iteration (early stopping): {var_intBestIter}")

        cls._log_confusion_matrix(
            arg_strModelo="XGBoost",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
        )

        logger.info(
            "XGBoost (direção de preço) - "
            f"ACC: {var_dictMetricas['accuracy']:.4f} | "
            f"Precisão(macro): {var_dictMetricas['precision_macro']:.4f} | "
            f"F1-macro: {var_dictMetricas['f1_macro']:.4f} | "
            f"Erros: {var_dictMetricas['error_count']:,} ({var_dictMetricas['error_rate']:.4f})"
        )
        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dictSplits["X_train"].shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }

    @classmethod
    def treinar_modelo_lightgbm(cls) -> dict:
        """
        Método para treinar o modelo de LightGBM.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits()

        var_objModelo = lgb.LGBMClassifier(
            objective="multiclass",
            num_class=3,
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            verbose=-1,
        )

        # Early stopping (quando suportado)
        try:
            var_objModelo.fit(
                var_dictSplits["X_train"],
                var_dictSplits["y_train"],
                eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],
                eval_metric="multi_logloss",
                callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
            )
        except TypeError:
            var_objModelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])

        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = cls._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        cls._log_metricas_treino_teste_classificacao(
            arg_strModelo="LightGBM",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        var_intBestIter = getattr(var_objModelo, "best_iteration_", None)
        if var_intBestIter is not None:
            logger.info(f"LightGBM - best_iteration (early stopping): {var_intBestIter}")

        cls._log_confusion_matrix(
            arg_strModelo="LightGBM",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
        )

        logger.info(
            "LightGBM (direção de preço) - "
            f"ACC: {var_dictMetricas['accuracy']:.4f} | "
            f"Precisão(macro): {var_dictMetricas['precision_macro']:.4f} | "
            f"F1-macro: {var_dictMetricas['f1_macro']:.4f} | "
            f"Erros: {var_dictMetricas['error_count']:,} ({var_dictMetricas['error_rate']:.4f})"
        )
        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dictSplits["X_train"].shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }

    @classmethod
    def executar_treinamento(cls):
        """
        Método para executar o treinamento de todos os modelos.

        Parâmetros:

        Retorna:
        """
        logger.info("Iniciando treinamento de todos os modelos...")
        
        var_dictLGBM = Treinar_Modelos.treinar_modelo_lightgbm()
        var_dictXGB = Treinar_Modelos.treinar_modelo_xgboost()
        var_dictRF = Treinar_Modelos.treinar_modelo_random_forest()
        var_dictReg = Treinar_Modelos.treinar_modelo_regressao_linear()

        logger.info("Resultado de cada modelo:")
        logger.info(
            "LightGBM - "
            f"Treinamento: {var_dictLGBM['train_size']}, Teste: {var_dictLGBM['test_size']}, "
            f"ACC: {var_dictLGBM['accuracy']:.4f}, Precisão: {var_dictLGBM['precision_macro']:.4f}, "
            f"F1: {var_dictLGBM['f1_macro']:.4f}, Erros: {var_dictLGBM['error_count']:,} ({var_dictLGBM['error_rate']:.4f})"
        )
        logger.info(
            "XGBoost - "
            f"Treinamento: {var_dictXGB['train_size']}, Teste: {var_dictXGB['test_size']}, "
            f"ACC: {var_dictXGB['accuracy']:.4f}, Precisão: {var_dictXGB['precision_macro']:.4f}, "
            f"F1: {var_dictXGB['f1_macro']:.4f}, Erros: {var_dictXGB['error_count']:,} ({var_dictXGB['error_rate']:.4f})"
        )
        logger.info(
            "Random Forest - "
            f"Treinamento: {var_dictRF['train_size']}, Teste: {var_dictRF['test_size']}, "
            f"ACC: {var_dictRF['accuracy']:.4f}, Precisão: {var_dictRF['precision_macro']:.4f}, "
            f"F1: {var_dictRF['f1_macro']:.4f}, Erros: {var_dictRF['error_count']:,} ({var_dictRF['error_rate']:.4f})"
        )
        logger.info(
            "Regressão Linear (dias até desconto) - "
            f"Treinamento: {var_dictReg['train_size']}, Teste: {var_dictReg['test_size']}, "
            f"RMSE: {var_dictReg['rmse']:.2f} dias, MAE: {var_dictReg['mae']:.2f} dias, MSE: {var_dictReg['mse']:.2f}"
        )
        logger.info("Treinamento de todos os modelos concluído com sucesso.")

if __name__ == "__main__":
    Treinar_Modelos.executar_treinamento()