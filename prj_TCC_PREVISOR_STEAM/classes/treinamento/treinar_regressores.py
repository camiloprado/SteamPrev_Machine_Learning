from prj_TCC_PREVISOR_STEAM.classes.treinamento.metricas import Metricas
from prj_TCC_PREVISOR_STEAM.classes.treinamento.plots import Plots
from prj_TCC_PREVISOR_STEAM.classes.treinamento.normalizar_modelos import NormalizarModelos

from sklearn.linear_model import LinearRegression
import logging
from datetime import datetime
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger("treino.regressores")

class TreinarRegressores:
    @classmethod
    def treinar_modelo_regressao_linear(cls, arg_strHorizonte: str = "30d", arg_strAlvo: str = "dias") -> dict:
        """
        Método para treinar o modelo de Regressão Linear.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE e tamanhos dos conjuntos de treino e teste.
        """
        # Obtém dados normalizados: X_train, X_test, y_train, y_test
        # Xr_train = features de REGRESSÃO no treino (r = regressão)
        # yr_train = alvo de REGRESSÃO no treino (dias até desconto)
        var_dictSplits = NormalizarModelos._obter_splits(arg_strHorizonte)

        # Instancia modelo de regressão linear vazio
        var_objModelo = LinearRegression()

        # Resolve X e y corretos ANTES do treino. Para o alvo "desconto", usa o conjunto
        # filtrado por horizonte (Xr_desc_train/Xr_desc_test), que contém apenas jogos cujo
        # desconto de fato ocorreu dentro da janela do horizonte — diferente do alvo "dias",
        # que usa o conjunto de regressão completo (Xr_train/Xr_test) com o valor capado.
        var_dfXTrain = var_dictSplits["Xr_train"] if arg_strAlvo == "dias" else var_dictSplits["Xr_desc_train"]
        var_dfXTest = var_dictSplits["Xr_test"] if arg_strAlvo == "dias" else var_dictSplits["Xr_desc_test"]

        # TREINA: ajusta os pesos do modelo aos dados de treino
        # O modelo encontra: y = a0 + a1*x1 + a2*x2 + ... + an*xn (reta multidimensional)
        var_serYTrain = var_dictSplits["yr_train"] if arg_strAlvo == "dias" else var_dictSplits["yr_desc_train"]
        var_serYTest = var_dictSplits["yr_test"] if arg_strAlvo == "dias" else var_dictSplits["yr_desc_test"]
        var_objModelo.fit(var_dfXTrain, var_serYTrain)

        # PREDIZ no treino: usa o modelo treinado para fazer predições
        var_arrPredTrain = var_objModelo.predict(var_dfXTrain)

        # PREDIZ no teste: usa o modelo em dados que nunca viu
        var_arrPredTest = var_objModelo.predict(var_dfXTest)

        # Centraliza o cálculo de métricas via _metricas_regressao (evita duplicação)
        var_dictMetricas = Metricas._metricas_regressao(var_serYTest, var_arrPredTest)

        # Log detalhado: treino vs teste
        Metricas._log_metricas_treino_teste_regressao(
            arg_strModelo=f"Regressão Linear ({arg_strHorizonte}, {arg_strAlvo})",
            arg_yTrain=var_serYTrain,
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_serYTest,
            arg_yPredTest=var_arrPredTest,
            arg_strAlvo=arg_strAlvo
        )

        # Log resumido para tabela final
        var_strUnidade = "dias" if arg_strAlvo == "dias" else "%"
        logger.info(
            f"Regressão linear ({arg_strHorizonte}, {arg_strAlvo}) - "
            f"RMSE: {var_dictMetricas['rmse']:.2f} {var_strUnidade} | "
            f"MAE: {var_dictMetricas['mae']:.2f} {var_strUnidade} | "
            f"MSE: {var_dictMetricas['mse']:.2f}"
        )

        # Gera plots de regressão (opcional, via configuração MATRIZ_CONFUSAO_PLOT)
        try:
            var_boolSalvarPng, var_boolMostrar, var_intDpi = Plots._obter_config_plots("regressao")
            if var_boolSalvarPng or var_boolMostrar:
                var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
                Plots._plot_regressao_predito_vs_real(
                    arg_strModelo=f"Linear_{arg_strHorizonte}_{arg_strAlvo}",
                    arg_arrYReal=var_serYTest,
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
                Plots._plot_regressao_residuos(
                    arg_strModelo=f"Linear_{arg_strHorizonte}_{arg_strAlvo}",
                    arg_arrYReal=var_serYTest,
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
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dfXTrain.shape[0],
            "test_size": var_dfXTest.shape[0],
        }


    @classmethod
    def treinar_modelo_xgboost_regressao(cls, arg_strHorizonte: str = "30d", arg_strAlvo: str = "dias") -> dict:
        """
        Método para treinar o modelo de XGBoost para REGRESSÃO.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE, MAE, MSE e tamanhos dos conjuntos.
        """
        # Obtém dados normalizados para regressão
        var_dictSplits = NormalizarModelos._obter_splits(arg_strHorizonte)

        # Instancia XGBoost para regressão (saída contínua) usando Pseudo Huber Loss
        var_objModelo = xgb.XGBRegressor(
            n_estimators=300,           # 300 iterações de boosting
            learning_rate=0.05,         # Aprendizado conservador
            max_depth=8,                # Árvores rasas para evitar overfitting
            subsample=0.9,              # Usa 90% das amostras
            colsample_bytree=0.9,       # Usa 90% das features
            random_state=42,            # Reprodutibilidade
        )

        # Resolve X e y corretos ANTES do try/except. Para o alvo "desconto", usa o
        # conjunto filtrado por horizonte (Xr_desc_train/Xr_desc_test), que contém
        # apenas jogos cujo desconto de fato ocorreu dentro da janela do horizonte.
        var_dfXTrain = var_dictSplits["Xr_train"] if arg_strAlvo == "dias" else var_dictSplits["Xr_desc_train"]
        var_dfXTest = var_dictSplits["Xr_test"] if arg_strAlvo == "dias" else var_dictSplits["Xr_desc_test"]
        var_serYTrain = var_dictSplits["yr_train"] if arg_strAlvo == "dias" else var_dictSplits["yr_desc_train"]
        var_serYTest = var_dictSplits["yr_test"] if arg_strAlvo == "dias" else var_dictSplits["yr_desc_test"]

        # TREINA com early stopping
        try:
            var_objModelo.fit(
                var_dfXTrain,
                var_serYTrain,
                eval_set=[(var_dfXTest, var_serYTest)],
                verbose=False,
                early_stopping_rounds=50,
            )
        except TypeError:
            var_objModelo.fit(var_dfXTrain, var_serYTrain)

        # PREDIZ no treino e teste
        var_arrPredTrain = var_objModelo.predict(var_dfXTrain)
        var_arrPredTest = var_objModelo.predict(var_dfXTest)

        # Calcula métricas no teste
        var_dictMetricas = Metricas._metricas_regressao(var_serYTest, var_arrPredTest)

        # Log detalhado: treino vs teste
        Metricas._log_metricas_treino_teste_regressao(
            arg_strModelo=f"XGBoost Regressão ({arg_strHorizonte}, {arg_strAlvo})",
            arg_yTrain=var_serYTrain,
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_serYTest,
            arg_yPredTest=var_arrPredTest,
            arg_strAlvo=arg_strAlvo
        )

        # Log resumido
        var_strUnidade = "dias" if arg_strAlvo == "dias" else "%"
        logger.info(
            f"XGBoost Regressão ({arg_strHorizonte}, {arg_strAlvo}) - "
            f"RMSE: {var_dictMetricas['rmse']:.2f} {var_strUnidade} | "
            f"MAE: {var_dictMetricas['mae']:.2f} {var_strUnidade} | "
            f"MSE: {var_dictMetricas['mse']:.2f}"
        )

        # Gera plots de regressão (opcional, via configuração MATRIZ_CONFUSAO_PLOT)
        try:
            var_boolSalvarPng, var_boolMostrar, var_intDpi = Plots._obter_config_plots("regressao")
            if var_boolSalvarPng or var_boolMostrar:
                var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
                Plots._plot_regressao_predito_vs_real(
                    arg_strModelo=f"XGBoost_{arg_strHorizonte}_{arg_strAlvo}",
                    arg_arrYReal=var_serYTest,
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
                Plots._plot_regressao_residuos(
                    arg_strModelo=f"XGBoost_{arg_strHorizonte}_{arg_strAlvo}",
                    arg_arrYReal=var_serYTest,
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
            "train_size": var_dfXTrain.shape[0],
            "test_size": var_dfXTest.shape[0],
        }


    @classmethod
    def treinar_modelo_lightgbm_regressao(cls, arg_strHorizonte: str = "30d", arg_strAlvo: str = "dias") -> dict:
        """
        Método para treinar o modelo de LightGBM para REGRESSÃO.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE, MAE, MSE e tamanhos dos conjuntos.
        """
        # Obtém dados normalizados para regressão
        var_dictSplits = NormalizarModelos._obter_splits(arg_strHorizonte)

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

        # Resolve X e y corretos ANTES do try/except. Para o alvo "desconto", usa o
        # conjunto filtrado por horizonte (Xr_desc_train/Xr_desc_test), que contém
        # apenas jogos cujo desconto de fato ocorreu dentro da janela do horizonte.
        var_dfXTrain = var_dictSplits["Xr_train"] if arg_strAlvo == "dias" else var_dictSplits["Xr_desc_train"]
        var_dfXTest = var_dictSplits["Xr_test"] if arg_strAlvo == "dias" else var_dictSplits["Xr_desc_test"]
        var_serYTrain = var_dictSplits["yr_train"] if arg_strAlvo == "dias" else var_dictSplits["yr_desc_train"]
        var_serYTest = var_dictSplits["yr_test"] if arg_strAlvo == "dias" else var_dictSplits["yr_desc_test"]

        # TREINA com early stopping
        try:
            var_objModelo.fit(
                var_dfXTrain,
                var_serYTrain,
                eval_set=[(var_dfXTest, var_serYTest)],
                eval_metric="rmse",
                callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
            )
        except TypeError:
            var_objModelo.fit(var_dfXTrain, var_serYTrain)

        # PREDIZ no treino e teste
        var_arrPredTrain = var_objModelo.predict(var_dfXTrain)
        var_arrPredTest = var_objModelo.predict(var_dfXTest)

        # Calcula métricas no teste
        var_dictMetricas = Metricas._metricas_regressao(var_serYTest, var_arrPredTest)

        # Log detalhado: treino vs teste
        Metricas._log_metricas_treino_teste_regressao(
            arg_strModelo=f"LightGBM Regressão ({arg_strHorizonte}, {arg_strAlvo})",
            arg_yTrain=var_serYTrain,
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_serYTest,
            arg_yPredTest=var_arrPredTest,
            arg_strAlvo=arg_strAlvo
        )

        # Log resumido
        var_strUnidade = "dias" if arg_strAlvo == "dias" else "%"
        logger.info(
            f"LightGBM Regressão ({arg_strHorizonte}, {arg_strAlvo}) - "
            f"RMSE: {var_dictMetricas['rmse']:.2f} {var_strUnidade} | "
            f"MAE: {var_dictMetricas['mae']:.2f} {var_strUnidade} | "
            f"MSE: {var_dictMetricas['mse']:.2f}"
        )

        # Gera plots de regressão (opcional, via configuração MATRIZ_CONFUSAO_PLOT)
        try:
            var_boolSalvarPng, var_boolMostrar, var_intDpi = Plots._obter_config_plots("regressao")
            if var_boolSalvarPng or var_boolMostrar:
                var_strTs = datetime.now().strftime("%Y%m%d_%H%M%S")
                Plots._plot_regressao_predito_vs_real(
                    arg_strModelo=f"LightGBM_{arg_strHorizonte}_{arg_strAlvo}",
                    arg_arrYReal=var_serYTest,
                    arg_arrYPred=var_arrPredTest,
                    arg_strTs=var_strTs,
                    arg_boolSalvarPng=var_boolSalvarPng,
                    arg_boolMostrar=var_boolMostrar,
                    arg_intDpi=var_intDpi,
                )
                Plots._plot_regressao_residuos(
                    arg_strModelo=f"LightGBM_{arg_strHorizonte}_{arg_strAlvo}",
                    arg_arrYReal=var_serYTest,
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
            "train_size": var_dfXTrain.shape[0],
            "test_size": var_dfXTest.shape[0],
        }


