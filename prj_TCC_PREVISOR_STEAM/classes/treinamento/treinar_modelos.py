from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.treinamento.normalizar_modelos import NormalizarModelos
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,              # Taxa de acerto geral (TP+TN)/(Total)
    mean_absolute_error,         # Erro médio absoluto em valores de saída
    mean_squared_error,          # Erro quadrático médio (eleva ao quadrado para penalizar erros grandes)
    precision_score,             # De todas as predições positivas, quantas estavam corretas
    f1_score,                    # Média harmônica de Precisão e Recall (equilibra ambos)
    root_mean_squared_error,     # Raiz do erro quadrático médio (interpretável na escala dos dados)
    confusion_matrix,            # Matriz que mostra TP, FP, FN, TN
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
            "f1_macro": var_floatF1,           # Score F1 equilibrado (PRINCIPAL PARA TCC)
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
    def _obter_diretorio_relatorios(cls) -> Path:
        """
        Obtém o diretório padrão do projeto para relatórios (resources/relatorios).
        
        Retorna:
        - Path: Objeto Path do diretório de relatórios, garantindo que exista.
        """
        var_pathBase = Path(__file__).resolve().parents[2]
        
        # Constrói caminho até resources/relatorios
        var_pathRelatorios = var_pathBase / "resources" / "relatorios"
        
        # Cria a pasta se não existir (mkdir com parents=True faz criação em cascata)
        var_pathRelatorios.mkdir(parents=True, exist_ok=True)
        
        # Retorna o Path object (pode usar para salvar arquivos)
        return var_pathRelatorios

    @staticmethod
    def _obter_config_plot_matriz_confusao() -> tuple[bool, bool, int]:
        """Define se deve gerar plot da matriz de confusão.

        Retorna:
        - (salvar_png, mostrar, dpi)
        """
        var_strMode = (os.getenv("MATRIZ_CONFUSAO_PLOT", "") or "").strip().lower()
        
        # Lê DPI da imagem (qualidade), padrão é string vazia
        var_strDpi = (os.getenv("MATRIZ_CONFUSAO_PLOT_DPI", "") or "").strip()

        # Define DPI padrão em 300
        var_intDpi = 300
        try:
            # Tenta converter DPI da variável de ambiente para inteiro
            if var_strDpi:
                var_intDpi = int(var_strDpi)
        except Exception:
            # Se falhar, mantém 300 como padrão
            var_intDpi = 300

        # Verifica cada modo possível e retorna configuração apropriada
        if var_strMode in ("", "0", "false", "no", "nao"):
            # Não salva, não mostra
            return (False, False, var_intDpi)

        if var_strMode in ("show", "mostrar"):
            # Mostra na tela, mas não salva (útil para debugging)
            return (False, True, var_intDpi)

        if var_strMode in ("both", "save_show", "save+show", "salvar_mostrar"):
            # Salva PNG E mostra na tela (útil para análise imediata)
            return (True, True, var_intDpi)

        # Modo padrão: salva PNG com qualidade DPI, não mostra
        # (melhor para processamento em lote, evita bloquear execução)
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
            # Calcula métricas NO CONJUNTO DE TREINO (dados que o modelo viu)
            var_dictTrain = cls._metricas_classificacao(arg_yTrain, arg_yPredTrain)
            
            # Calcula métricas NO CONJUNTO DE TESTE (dados novos, nunca vistos)
            var_dictTest = cls._metricas_classificacao(arg_yTest, arg_yPredTest)
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
    def _plot_regressao_predito_vs_real(cls, arg_strModelo: str, arg_arrYReal, arg_arrYPred, arg_strTs: str, arg_boolSalvarPng: bool, arg_boolMostrar: bool, arg_intDpi: int) -> None:
        """
        Gera scatter plot de valores preditos vs reais para regressão.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo
        - arg_arrYReal (array-like): Valores reais (y_true)
        - arg_arrYPred (array-like): Valores preditos (y_pred)
        - arg_strTs (str): Timestamp para nome do arquivo
        - arg_boolSalvarPng (bool): Se True, salva como PNG
        - arg_boolMostrar (bool): Se True, exibe na tela
        - arg_intDpi (int): DPI para salvar PNG
        """
        try:
            if arg_boolSalvarPng and not arg_boolMostrar:
                import matplotlib
                matplotlib.use("Agg")
            
            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            logger.warning(f"Matplotlib indisponível para plotar regressão ({arg_strModelo}): {e}")
            return
        
        try:
            var_arrYReal = np.asarray(arg_arrYReal, dtype=np.float64)
            var_arrYPred = np.asarray(arg_arrYPred, dtype=np.float64)
            
            var_objFig, var_objAxes = plt.subplots(figsize=(8.0, 6.0), dpi=max(72, int(arg_intDpi)))
            
            # Scatter plot: preditos vs reais
            var_objAxes.scatter(var_arrYReal, var_arrYPred, alpha=0.5, s=10, edgecolors='none')
            
            # Linha perfeita (y=x) onde predito seria igual ao real
            var_floatMin = min(var_arrYReal.min(), var_arrYPred.min())
            var_floatMax = max(var_arrYReal.max(), var_arrYPred.max())
            var_objAxes.plot([var_floatMin, var_floatMax], [var_floatMin, var_floatMax], 'r--', lw=2, label='Predição Perfeita')
            
            var_objAxes.set_xlabel('Valores Reais (dias)', fontsize=11)
            var_objAxes.set_ylabel('Valores Preditos (dias)', fontsize=11)
            var_objAxes.set_title(f'Predito vs Real - {arg_strModelo}', fontsize=12, fontweight='bold')
            var_objAxes.legend()
            var_objAxes.grid(True, alpha=0.3)
            
            var_objFig.tight_layout()
            
            if arg_boolSalvarPng:
                var_pathRelatorios = cls._obter_diretorio_relatorios()
                var_strBaseName = f"regressao_{arg_strModelo}_predito_vs_real_{arg_strTs}"
                var_pathPng = var_pathRelatorios / f"{var_strBaseName}.png"
                var_objFig.savefig(var_pathPng, dpi=max(72, int(arg_intDpi)))
                logger.info(f"Plot regressão (predito vs real) salvo: {var_pathPng}")
            
            if arg_boolMostrar:
                plt.show()
        except Exception as e:
            logger.warning(f"Falha ao gerar plot predito vs real ({arg_strModelo}): {e}")
        finally:
            try:
                plt.close("all")
            except Exception:
                pass

    @classmethod
    def _plot_regressao_residuos(cls, arg_strModelo: str, arg_arrYReal, arg_arrYPred, arg_strTs: str, arg_boolSalvarPng: bool, arg_boolMostrar: bool, arg_intDpi: int) -> None:
        """
        Gera scatter plot de resíduos (erros) vs valores preditos.
        Visualiza padrões de erro sistemático no modelo.
        
        Parâmetros:
        - arg_strModelo (str): Nome do modelo
        - arg_arrYReal (array-like): Valores reais (y_true)
        - arg_arrYPred (array-like): Valores preditos (y_pred)
        - arg_strTs (str): Timestamp para nome do arquivo
        - arg_boolSalvarPng (bool): Se True, salva como PNG
        - arg_boolMostrar (bool): Se True, exibe na tela
        - arg_intDpi (int): DPI para salvar PNG
        """
        try:
            if arg_boolSalvarPng and not arg_boolMostrar:
                import matplotlib
                matplotlib.use("Agg")
            
            import matplotlib.pyplot as plt
            import numpy as np
        except Exception as e:
            logger.warning(f"Matplotlib indisponível para plotar resíduos ({arg_strModelo}): {e}")
            return
        
        try:
            var_arrYReal = np.asarray(arg_arrYReal, dtype=np.float64)
            var_arrYPred = np.asarray(arg_arrYPred, dtype=np.float64)
            var_arrResiduos = var_arrYReal - var_arrYPred  # Erro = real - predito
            
            var_objFig, var_objAxes = plt.subplots(figsize=(8.0, 6.0), dpi=max(72, int(arg_intDpi)))
            
            # Scatter plot: resíduos vs preditos
            var_objAxes.scatter(var_arrYPred, var_arrResiduos, alpha=0.5, s=10, edgecolors='none')
            
            # Linha no zero (resíduos perfeitos)
            var_objAxes.axhline(y=0, color='r', linestyle='--', lw=2, label='Sem erro')
            
            var_objAxes.set_xlabel('Valores Preditos (dias)', fontsize=11)
            var_objAxes.set_ylabel('Resíduos = Real - Predito (dias)', fontsize=11)
            var_objAxes.set_title(f'Resíduos vs Predito - {arg_strModelo}', fontsize=12, fontweight='bold')
            var_objAxes.legend()
            var_objAxes.grid(True, alpha=0.3)
            
            var_objFig.tight_layout()
            
            if arg_boolSalvarPng:
                var_pathRelatorios = cls._obter_diretorio_relatorios()
                var_strBaseName = f"regressao_{arg_strModelo}_residuos_{arg_strTs}"
                var_pathPng = var_pathRelatorios / f"{var_strBaseName}.png"
                var_objFig.savefig(var_pathPng, dpi=max(72, int(arg_intDpi)))
                logger.info(f"Plot regressão (resíduos) salvo: {var_pathPng}")
            
            if arg_boolMostrar:
                plt.show()
        except Exception as e:
            logger.warning(f"Falha ao gerar plot de resíduos ({arg_strModelo}): {e}")
        finally:
            try:
                plt.close("all")
            except Exception:
                pass
    
    @classmethod
    def treinar_modelo_regressao_linear(cls) -> dict:
        """
        Método para treinar o modelo de Regressão Linear.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE e tamanhos dos conjuntos de treino e teste.
        """
        # Obtém dados normalizados: X_train, X_test, y_train, y_test
        # Xr_train = features de REGRESSÃO no treino (r = regressão)
        # yr_train = alvo de REGRESSÃO no treino (dias até desconto)
        var_dictSplits = NormalizarModelos._obter_splits()

        # Instancia modelo de regressão linear vazio
        var_objModelo = LinearRegression()
        
        # TREINA: ajusta os pesos do modelo aos dados de treino
        # O modelo encontra: y = a0 + a1*x1 + a2*x2 + ... + an*xn (reta multidimensional)
        var_objModelo.fit(var_dictSplits["Xr_train"], var_dictSplits["yr_train"])
        
        # PREDIZ no treino: usa o modelo treinado para fazer predições
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["Xr_train"])
        
        # PREDIZ no teste: usa o modelo em dados que nunca viu
        var_arrPredTest = var_objModelo.predict(var_dictSplits["Xr_test"])

        # Calcula RMSE (Raiz do Erro Quadrático Médio)
        # Métrica principal para regressão: quanto menor, melhor
        # Interpretação: erro médio em "dias"
        if root_mean_squared_error is not None:
            # Se sklearn tiver função nativa RMSE, usa ela (mais recente)
            var_floatRmse = root_mean_squared_error(var_dictSplits["yr_test"], var_arrPredTest)
        else:
            # Se não, calcula manualmente: sqrt(MSE)
            # Compatibilidade com sklearn antigo
            var_floatRmse = mean_squared_error(var_dictSplits["yr_test"], var_arrPredTest) ** 0.5

        # Calcula MSE (Erro Quadrático Médio)
        # Penaliza erros grandes (ao quadrado) mais do que linearly
        var_floatMse = mean_squared_error(var_dictSplits["yr_test"], var_arrPredTest)
        
        # Calcula MAE (Erro Médio Absoluto)
        # Mais "robusto" que MSE: não penaliza tanto outliers
        var_floatMae = mean_absolute_error(var_dictSplits["yr_test"], var_arrPredTest)

        # Log detalhado: treino vs teste com status de overfitting
        cls._log_metricas_treino_teste_regressao(
            arg_strModelo="Regressão Linear (dias até desconto)",
            arg_yTrain=var_dictSplits["yr_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["yr_test"],
            arg_yPredTest=var_arrPredTest,
        )

        # Log resumido para tabela final
        logger.info(
            "Regressão linear (dias até desconto) - "
            f"RMSE: {var_floatRmse:.2f} dias | "
            f"MAE: {var_floatMae:.2f} dias | "
            f"MSE: {var_floatMse:.2f}"
        )

        # Gera plots de regressão (opcional, via configuração MATRIZ_CONFUSAO_PLOT)
        try:
            var_boolSalvarPng, var_boolMostrar, var_intDpi = cls._obter_config_plot_matriz_confusao()
            if var_boolSalvarPng or var_boolMostrar:
                var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
                cls._plot_regressao_predito_vs_real(
                    arg_strModelo="Linear",
                    arg_arrYReal=var_dictSplits["yr_test"],
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
                cls._plot_regressao_residuos(
                    arg_strModelo="Linear",
                    arg_arrYReal=var_dictSplits["yr_test"],
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
        except Exception as e:
            logger.debug(f"Plots de regressão não foram gerados (Linear): {e}")
        
        # Retorna dicionário com tudo para tabela comparativa final
        return {
            "modelo": var_objModelo,     # Modelo treinado (pode ser usado para predições futuras)
            "rmse": var_floatRmse,       # Erro quadrático médio (PRINCIPAL MÉTRICA)
            "mae": var_floatMae,         # Erro médio absoluto
            "mse": var_floatMse,         # Erro quadrático (antes da raiz)
            "train_size": var_dictSplits["Xr_train"].shape[0],  # Quantas amostras usou para treinar
            "test_size": var_dictSplits["Xr_test"].shape[0],    # Quantas amostras usou para testar
        }

    @classmethod
    def treinar_modelo_xgboost_regressao(cls) -> dict:
        """
        Método para treinar o modelo de XGBoost para REGRESSÃO.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE, MAE, MSE e tamanhos dos conjuntos.
        """
        # Obtém dados normalizados para regressão
        var_dictSplits = NormalizarModelos._obter_splits()

        # Instancia XGBoost para regressão (saída contínua)
        var_objModelo = xgb.XGBRegressor(
            n_estimators=300,           # 300 iterações de boosting
            learning_rate=0.05,         # Aprendizado conservador
            max_depth=8,                # Árvores rasas para evitar overfitting
            subsample=0.9,              # Usa 90% das amostras
            colsample_bytree=0.9,       # Usa 90% das features
            random_state=42,            # Reprodutibilidade
        )

        # TREINA com early stopping
        try:
            var_objModelo.fit(
                var_dictSplits["Xr_train"],
                var_dictSplits["yr_train"],
                eval_set=[(var_dictSplits["Xr_test"], var_dictSplits["yr_test"])],
                verbose=False,
                early_stopping_rounds=50,
            )
        except TypeError:
            var_objModelo.fit(var_dictSplits["Xr_train"], var_dictSplits["yr_train"])

        # PREDIZ no treino e teste
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["Xr_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["Xr_test"])

        # Calcula métricas no teste
        var_dictMetricas = cls._metricas_regressao(var_dictSplits["yr_test"], var_arrPredTest)

        # Log detalhado: treino vs teste
        cls._log_metricas_treino_teste_regressao(
            arg_strModelo="XGBoost (dias até desconto)",
            arg_yTrain=var_dictSplits["yr_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["yr_test"],
            arg_yPredTest=var_arrPredTest,
        )

        # Log resumido
        logger.info(
            "XGBoost (dias até desconto) - "
            f"RMSE: {var_dictMetricas['rmse']:.2f} dias | "
            f"MAE: {var_dictMetricas['mae']:.2f} dias | "
            f"MSE: {var_dictMetricas['mse']:.2f}"
        )

        # Gera plots de regressão (opcional, via configuração MATRIZ_CONFUSAO_PLOT)
        try:
            var_boolSalvarPng, var_boolMostrar, var_intDpi = cls._obter_config_plot_matriz_confusao()
            if var_boolSalvarPng or var_boolMostrar:
                var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
                cls._plot_regressao_predito_vs_real(
                    arg_strModelo="XGBoost",
                    arg_arrYReal=var_dictSplits["yr_test"],
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
                cls._plot_regressao_residuos(
                    arg_strModelo="XGBoost",
                    arg_arrYReal=var_dictSplits["yr_test"],
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
        except Exception as e:
            logger.debug(f"Plots de regressão não foram gerados (XGBoost): {e}")

        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dictSplits["Xr_train"].shape[0],
            "test_size": var_dictSplits["Xr_test"].shape[0],
        }

    @classmethod
    def treinar_modelo_lightgbm_regressao(cls) -> dict:
        """
        Método para treinar o modelo de LightGBM para REGRESSÃO.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE, MAE, MSE e tamanhos dos conjuntos.
        """
        # Obtém dados normalizados para regressão
        var_dictSplits = NormalizarModelos._obter_splits()

        # Instancia LightGBM para regressão (saída contínua)
        var_objModelo = lgb.LGBMRegressor(
            n_estimators=300,           # 300 iterações de boosting
            learning_rate=0.05,         # Aprendizado conservador
            num_leaves=31,              # Máximo de folhas (complexidade)
            subsample=0.9,              # Usa 90% das amostras
            colsample_bytree=0.9,       # Usa 90% das features
            random_state=42,            # Reprodutibilidade
            verbose=-1,                 # Silencioso
        )

        # TREINA com early stopping
        try:
            var_objModelo.fit(
                var_dictSplits["Xr_train"],
                var_dictSplits["yr_train"],
                eval_set=[(var_dictSplits["Xr_test"], var_dictSplits["yr_test"])],
                eval_metric="rmse",
                callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
            )
        except TypeError:
            var_objModelo.fit(var_dictSplits["Xr_train"], var_dictSplits["yr_train"])

        # PREDIZ no treino e teste
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["Xr_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["Xr_test"])

        # Calcula métricas no teste
        var_dictMetricas = cls._metricas_regressao(var_dictSplits["yr_test"], var_arrPredTest)

        # Log detalhado: treino vs teste
        cls._log_metricas_treino_teste_regressao(
            arg_strModelo="LightGBM (dias até desconto)",
            arg_yTrain=var_dictSplits["yr_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["yr_test"],
            arg_yPredTest=var_arrPredTest,
        )

        # Log resumido
        logger.info(
            "LightGBM (dias até desconto) - "
            f"RMSE: {var_dictMetricas['rmse']:.2f} dias | "
            f"MAE: {var_dictMetricas['mae']:.2f} dias | "
            f"MSE: {var_dictMetricas['mse']:.2f}"
        )

        # Gera plots de regressão (opcional, via configuração MATRIZ_CONFUSAO_PLOT)
        try:
            var_boolSalvarPng, var_boolMostrar, var_intDpi = cls._obter_config_plot_matriz_confusao()
            if var_boolSalvarPng or var_boolMostrar:
                var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
                cls._plot_regressao_predito_vs_real(
                    arg_strModelo="LightGBM",
                    arg_arrYReal=var_dictSplits["yr_test"],
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
                cls._plot_regressao_residuos(
                    arg_strModelo="LightGBM",
                    arg_arrYReal=var_dictSplits["yr_test"],
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
        except Exception as e:
            logger.debug(f"Plots de regressão não foram gerados (LightGBM): {e}")

        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
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
        # Obtém dados normalizados para CLASSIFICAÇÃO
        # X_train, y_train = features e rótulos do treino
        # X_test, y_test = features e rótulos do teste
        var_dictSplits = NormalizarModelos._obter_splits()

        # Instancia Random Forest com 300 árvores
        # Cada árvore independente = diversidade = robustez
        var_objModelo = RandomForestClassifier(
            n_estimators=300,      # 300 árvores de decisão
            max_depth=12,          # Cada árvore tem profundidade máxima 12 (controla complexidade)
            n_jobs=-1,             # -1 = usa todos os cores disponíveis
            random_state=42,       # Seed para reprodutibilidade
        )
        
        # TREINA: cada árvore aprende com features aleatórios
        var_objModelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])
        
        # PREDIZ no treino: cada árvore vota, vence a classe com mais votos
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        
        # PREDIZ no teste: usa as 300 árvores treinadas para dados novos
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        # Calcula métricas (accuracy, precision, f1, erros) apenas no TESTE
        var_dictMetricas = cls._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        # Log detalhado: treino vs teste com detecção de overfitting
        cls._log_metricas_treino_teste_classificacao(
            arg_strModelo="Random Forest",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        # Log matriz de confusão: como o modelo confundiu cada classe
        # Salva em CSV (contagens + normalizado) e PNG (heatmap visual)
        cls._log_confusion_matrix(
            arg_strModelo="RandomForest",           # Nome para arquivo
            arg_arrYTrue=var_dictSplits["y_test"],  # Rótulos verdadeiros
            arg_arrYPred=var_arrPredTest,           # Rótulos preditos
            arg_listLabels=[0, 1, 2],               # Classes (cai, mantem, sobe)
            arg_listLabelNames=["cai", "mantem", "sobe"],  # Nomes legíveis
            arg_strSplit="teste"                    # Indica que é no conjunto de teste
        )
        
        # Retorna dicionário com tudo para tabela comparativa final
        return {
            "modelo": var_objModelo,               # Modelo treinado (300 árvores)
            **var_dictMetricas,                    # Expande: accuracy, precision, f1, errors
            "train_size": var_dictSplits["X_train"].shape[0],  # Tamanho do treino
            "test_size": var_dictSplits["X_test"].shape[0],    # Tamanho do teste
        }

    @classmethod
    def treinar_modelo_xgboost(cls) -> dict:
        """
        Método para treinar o modelo de XGBoost.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        # Obtém dados normalizados para classificação
        var_dictSplits = NormalizarModelos._obter_splits()

        # Instancia XGBoost para classificação multiclasse (3 classes)
        var_objModelo = xgb.XGBClassifier(
            objective="multi:softprob",        # Softmax para 3+ classes (probs somam 1)
            num_class=3,                       # 3 classes: cai, mantem, sobe
            eval_metric="mlogloss",            # Métrica de avaliação (log loss para multiclasse)
            n_estimators=300,                  # 300 iterações de boosting
            learning_rate=0.05,                # Aprendizado conservador (evita overfitting)
            max_depth=8,                       # Árvores rasas (12 em RF, 8 em XGB)
            subsample=0.9,                     # Usa 90% das amostras por iteração
            colsample_bytree=0.9,              # Usa 90% das features por iteração
            random_state=42,                   # Reprodutibilidade
        )

        # TREINA com EARLY STOPPING (parada se não melhorar)
        try:
            # Tenta treinar com early stopping (requer dataset de validação)
            var_objModelo.fit(
                var_dictSplits["X_train"],
                var_dictSplits["y_train"],
                eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],  # Valida no teste
                verbose=False,                 # Sem logs intermediários (mais limpo)
                early_stopping_rounds=50,      # Para se 50 rounds sem melhoria
            )
        except TypeError:
            # Se a versão do XGB não suporta early stopping, treina normalmente
            var_objModelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])

        # PREDIZ no treino
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        
        # PREDIZ no teste
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        # Calcula métricas apenas no TESTE
        var_dictMetricas = cls._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        # Log detalhado: treino vs teste com detecção de overfitting
        cls._log_metricas_treino_teste_classificacao(
            arg_strModelo="XGBoost",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        # Log matriz de confusão
        cls._log_confusion_matrix(
            arg_strModelo="XGBoost",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
        )
        
        # Retorna dicionário para tabela comparativa
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
        # Obtém dados normalizados para classificação
        var_dictSplits = NormalizarModelos._obter_splits()

        # Instancia LightGBM para classificação multiclasse
        var_objModelo = lgb.LGBMClassifier(
            objective="multiclass",             # Classificação em 3+ classes
            num_class=3,                        # 3 classes: cai, mantem, sobe
            n_estimators=300,                   # 300 iterações de boosting
            learning_rate=0.05,                 # Aprendizado conservador
            num_leaves=31,                      # Máximo de folhas por árvore (complexidade)
            subsample=0.9,                      # Usa 90% das amostras
            colsample_bytree=0.9,               # Usa 90% das features
            random_state=42,                    # Reprodutibilidade
            verbose=-1,                         # Silencioso (sem logs de treinamento)
        )

        # TREINA com EARLY STOPPING
        try:
            # Tenta treinar com early stopping
            var_objModelo.fit(
                var_dictSplits["X_train"],
                var_dictSplits["y_train"],
                eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],  # Validação
                eval_metric="multi_logloss",   # Métrica de parada
                callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],  # Para se não melhorar
            )
        except TypeError:
            # Fallback se a sintaxe for diferente em versão anterior do LGB
            var_objModelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])

        # PREDIZ no treino
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        
        # PREDIZ no teste
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        # Calcula métricas apenas no TESTE
        var_dictMetricas = cls._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        # Log detalhado: treino vs teste com detecção de overfitting
        cls._log_metricas_treino_teste_classificacao(
            arg_strModelo="LightGBM",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        # Log matriz de confusão
        cls._log_confusion_matrix(
            arg_strModelo="LightGBM",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
        )
        
        # Retorna dicionário para tabela comparativa
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
        logger.info("=" * 80)
        logger.info("INICIANDO TREINAMENTO DE MODELOS DE CLASSIFICAÇÃO E REGRESSÃO")
        logger.info("=" * 80)
        
        # Treina LightGBM (gradual boosting, mais rápido)
        var_dictLGBM = Treinar_Modelos.treinar_modelo_lightgbm()
        
        # Treina XGBoost (extreme gradient boosting, mais poderoso)
        var_dictXGB = Treinar_Modelos.treinar_modelo_xgboost()
        
        # Treina Random Forest (múltiplas árvores independentes, mais robusto)
        var_dictRF = Treinar_Modelos.treinar_modelo_random_forest()
        
        # Treina Regressão Linear (dias até desconto)
        var_dictReg = Treinar_Modelos.treinar_modelo_regressao_linear()
        
        # Treina XGBoost Regressão (dias até desconto)
        var_dictRegXGB = Treinar_Modelos.treinar_modelo_xgboost_regressao()
        
        # Treina LightGBM Regressão (dias até desconto)
        var_dictRegLGB = Treinar_Modelos.treinar_modelo_lightgbm_regressao()

        # Tabela comparativa final - MODELOS DE CLASSIFICAÇÃO
        logger.info("=" * 80)
        logger.info("RESUMO COMPARATIVO - MODELOS DE CLASSIFICAÇÃO (DIREÇÃO DE PREÇO)")
        logger.info("=" * 80)
        
        # Cabeçalho da tabela
        logger.info(f"{'Modelo':<18} | {'Accuracy':>10} | {'Precision':>10} | {'F1-Score':>10} | Dataset")
        logger.info("-" * 80)
        
        # Linha LightGBM com métricas
        logger.info(
            f"{'LightGBM':<18} | {var_dictLGBM['accuracy']:>10.4f} | "
            f"{var_dictLGBM['precision_macro']:>10.4f} | {var_dictLGBM['f1_macro']:>10.4f} | "
            f"{var_dictLGBM['train_size']:,} treino / {var_dictLGBM['test_size']:,} teste"
        )
        
        # Linha XGBoost com métricas
        logger.info(
            f"{'XGBoost':<18} | {var_dictXGB['accuracy']:>10.4f} | "
            f"{var_dictXGB['precision_macro']:>10.4f} | {var_dictXGB['f1_macro']:>10.4f} | "
            f"{var_dictXGB['train_size']:,} treino / {var_dictXGB['test_size']:,} teste"
        )
        
        # Linha Random Forest com métricas
        logger.info(
            f"{'Random Forest':<18} | {var_dictRF['accuracy']:>10.4f} | "
            f"{var_dictRF['precision_macro']:>10.4f} | {var_dictRF['f1_macro']:>10.4f} | "
            f"{var_dictRF['train_size']:,} treino / {var_dictRF['test_size']:,} teste"
        )
        
        # Identifica melhor modelo
        # Cria dicionário com nome e resultados de cada modelo
        var_dictModelos = {"LightGBM": var_dictLGBM, "XGBoost": var_dictXGB, "Random Forest": var_dictRF}
        
        # Identifica qual modelo tem o MAIOR F1-Score
        # F1 é melhor que Accuracy porque penaliza tanto falsos positivos quanto falsos negativos
        var_strMelhorModelo = max(var_dictModelos.items(), key=lambda x: x[1]['f1_macro'])[0]
        var_floatMelhorF1 = var_dictModelos[var_strMelhorModelo]['f1_macro']
        
        logger.info(f"MELHOR MODELO: {var_strMelhorModelo} (F1-Score: {var_floatMelhorF1:.4f})")
        
        # Regressão Linear
        logger.info("=" * 80)
        logger.info("RESUMO COMPARATIVO - MODELOS DE REGRESSÃO (DIAS ATÉ DESCONTO)")
        logger.info("=" * 80)
        
        # Cabeçalho da tabela de regressão
        logger.info(f"{'Modelo':<18} | {'RMSE (dias)':>12} | {'MAE (dias)':>11} | {'MSE':>10} | Dataset")
        logger.info("-" * 80)
        
        # Linha LightGBM Regressão
        logger.info(
            f"{'LightGBM':<18} | {var_dictRegLGB['rmse']:>12.2f} | "
            f"{var_dictRegLGB['mae']:>11.2f} | {var_dictRegLGB['mse']:>10.2f} | "
            f"{var_dictRegLGB['train_size']:,} treino / {var_dictRegLGB['test_size']:,} teste"
        )
        
        # Linha XGBoost Regressão
        logger.info(
            f"{'XGBoost':<18} | {var_dictRegXGB['rmse']:>12.2f} | "
            f"{var_dictRegXGB['mae']:>11.2f} | {var_dictRegXGB['mse']:>10.2f} | "
            f"{var_dictRegXGB['train_size']:,} treino / {var_dictRegXGB['test_size']:,} teste"
        )
        
        # Linha Regressão Linear
        logger.info(
            f"{'Linear Regression':<18} | {var_dictReg['rmse']:>12.2f} | "
            f"{var_dictReg['mae']:>11.2f} | {var_dictReg['mse']:>10.2f} | "
            f"{var_dictReg['train_size']:,} treino / {var_dictReg['test_size']:,} teste"
        )
        
        # Identifica melhor regressor
        var_dictRegressores = {"LightGBM": var_dictRegLGB, "XGBoost": var_dictRegXGB, "Linear Regression": var_dictReg}
        var_strMelhorRegressor = min(var_dictRegressores.items(), key=lambda x: x[1]['rmse'])[0]
        var_floatMelhorRMSE = var_dictRegressores[var_strMelhorRegressor]['rmse']
        
        logger.info(f"MELHOR MODELO REGRESSÃO: {var_strMelhorRegressor} (RMSE: {var_floatMelhorRMSE:.2f} dias)")
        
        logger.info("=" * 80)
        logger.info("TREINAMENTO CONCLUÍDO COM SUCESSO")
        logger.info("Matrizes de confusão salvas em: resources/relatorios/")
        logger.info("=" * 80)

if __name__ == "__main__":
    Treinar_Modelos.executar_treinamento()