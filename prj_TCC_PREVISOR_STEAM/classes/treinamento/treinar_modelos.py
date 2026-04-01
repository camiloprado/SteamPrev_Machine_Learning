from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_bdgeral import PostgreSQLBDGeral
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import accuracy_score, mean_squared_error, f1_score
from sklearn.model_selection import train_test_split

import xgboost as xgb
import lightgbm as lgb
import pandas as pd
import numpy as np
import json

import logging

logger = logging.getLogger(__name__)

class Treinar_Modelos:
    """
    Classe responsável por unificar o treinamento entre os diversos modelos preditivos utilizados no projeto.
    """
    _var_dfDadosTreinamento = None
    _var_dfAmostrasTemporais = None
    _var_dictSplits = None
    _var_intJanelaHistorico = 5
    _var_floatThresholdDirecao = 0.03

    @classmethod
    def carregar_dados_treinamento(cls) -> pd.DataFrame:
        """
        Método para carregar os dados de treinamento.

        Parâmetros:

        Retorna:
        - pd.DataFrame: DataFrame contendo os dados de treinamento.
        """
        logger.info("Carregando dados de treinamento...")
        var_dictDados = PostgreSQLBDGeral.buscar_dados_Geral(arg_boolFiltroPadrao=True)
        cls._var_dfDadosTreinamento = pd.DataFrame(var_dictDados)
        logger.info("Dados de treinamento carregados com sucesso.")

        return cls._var_dfDadosTreinamento

    @staticmethod
    def _converter_preco_para_float(arg_valor) -> float:
        """
        Converte string monetária no formato brasileiro para float.
        
        Parâmetros:
        - arg_valor: Valor a ser convertido, pode ser string ou numérico.

        Retorna:
        - float: Valor convertido para float, ou np.nan se a conversão falhar.
        """
        if arg_valor is None or (isinstance(arg_valor, float) and np.isnan(arg_valor)):
            return np.nan
        if isinstance(arg_valor, (int, float)):
            return float(arg_valor)

        var_strValor = str(arg_valor).strip()
        if not var_strValor:
            return np.nan

        var_strValor = var_strValor.replace("R$", "").replace(" ", "")
        var_strValor = var_strValor.replace(".", "").replace(",", ".")
        try:
            return float(var_strValor)
        except ValueError:
            return np.nan

    @staticmethod
    def _normalizar_historico(arg_listHistorico:list) -> list:
        """
        Normaliza o histórico para uma lista de pontos com timestamp, preço e desconto.

        Parâmetros:
        - arg_listHistorico: Lista de pontos com timestamp, preço e desconto.

        Retorna:
        - list: Lista de pontos normalizados.
        """
        if arg_listHistorico is None or (isinstance(arg_listHistorico, float) and np.isnan(arg_listHistorico)):
            return []

        if isinstance(arg_listHistorico, list):
            var_listBase = arg_listHistorico
        else:
            return []

        var_listPontos = []
        for var_dictItem in var_listBase:
            if not isinstance(var_dictItem, dict):
                continue

            var_strTimestamp = var_dictItem.get("timestamp")
            var_dictDeal = var_dictItem.get("deal")
            var_dictPreco = var_dictDeal.get("price", {})
            var_floatPreco = var_dictPreco.get("amount")
            if var_floatPreco is None:
                var_floatPreco = var_dictItem.get("price")
            if var_floatPreco is None:
                var_floatPreco = var_dictItem.get("new")

            try:
                var_intTimestamp = int(var_strTimestamp)
                var_floatPreco = float(var_floatPreco)
            except (TypeError, ValueError):
                continue

            if var_intTimestamp <= 0 or var_floatPreco <= 0:
                continue

            var_floatDesconto = var_dictItem.get("cut", 0) or 0
            try:
                var_floatDesconto = float(var_floatDesconto)
            except (TypeError, ValueError):
                var_floatDesconto = 0.0

            var_listPontos.append(
                {
                    "timestamp": var_intTimestamp,
                    "preco": var_floatPreco,
                    "desconto": var_floatDesconto,
                }
            )

        var_listPontos.sort(key=lambda item: item["timestamp"])
        return var_listPontos

    @classmethod
    def _construir_amostras_temporais(cls) -> pd.DataFrame:
        """
        Cria amostras supervisionadas temporais para direção de preço e dias até desconto.
        
        Parâmetros:
        
        Retorna:
        - pd.DataFrame: DataFrame com as amostras temporais criadas.
        """
        if cls._var_dfDadosTreinamento is None:
            cls.carregar_dados_treinamento()

        var_listAmostras = []
        var_intJanela = cls._var_intJanelaHistorico
        var_floatThreshold = cls._var_floatThresholdDirecao

        for _, var_dictRow in cls._var_dfDadosTreinamento.iterrows():
            var_listHistorico = cls._normalizar_historico(var_dictRow.get("historico_preco"))
            if len(var_listHistorico) < (var_intJanela + 1):
                continue

            var_floatReviewScore = pd.to_numeric(var_dictRow.get("review_score"), errors="coerce")
            var_floatPrecoAtualCatalogo = cls._converter_preco_para_float(var_dictRow.get("preco"))

            for var_intIdx in range(var_intJanela, len(var_listHistorico) - 1):
                var_listJanela = var_listHistorico[var_intIdx - var_intJanela: var_intIdx + 1]
                var_dictAtual = var_listHistorico[var_intIdx]
                var_dictFuturo = var_listHistorico[var_intIdx + 1]

                var_floatPrecoAtual = var_dictAtual["preco"]
                var_floatPrecoFuturo = var_dictFuturo["preco"]
                if var_floatPrecoAtual <= 0:
                    continue

                var_floatVariacao = (var_floatPrecoFuturo - var_floatPrecoAtual) / var_floatPrecoAtual

                if var_floatVariacao <= -var_floatThreshold:
                    var_strDirecao = "cai"
                elif var_floatVariacao >= var_floatThreshold:
                    var_strDirecao = "sobe"
                else:
                    var_strDirecao = "mantem"

                var_intDiasProxDesconto = np.nan
                for var_intJ in range(var_intIdx + 1, len(var_listHistorico)):
                    var_dictPontoFuturo = var_listHistorico[var_intJ]
                    if var_dictPontoFuturo.get("desconto", 0) > 0:
                        var_intDiasProxDesconto = int(
                            (var_dictPontoFuturo["timestamp"] - var_dictAtual["timestamp"]) / 86400
                        )
                        break

                var_listPrecosJanela = [item["preco"] for item in var_listJanela]
                var_listDescontosJanela = [item["desconto"] for item in var_listJanela]
                var_listTimestampsJanela = [item["timestamp"] for item in var_listJanela]

                var_intDiasDesdeUltimoDesconto = 9999
                for var_intK in range(len(var_listJanela) - 1, -1, -1):
                    if var_listJanela[var_intK]["desconto"] > 0:
                        var_intDiasDesdeUltimoDesconto = int(
                            (var_dictAtual["timestamp"] - var_listJanela[var_intK]["timestamp"]) / 86400
                        )
                        break

                var_listAmostras.append(
                    {
                        "appid": var_dictRow.get("appid"),
                        "review_score": float(var_floatReviewScore) if pd.notna(var_floatReviewScore) else 0.0,
                        "preco_catalogo": float(var_floatPrecoAtualCatalogo) if pd.notna(var_floatPrecoAtualCatalogo) else 0.0,
                        "preco_atual_hist": var_floatPrecoAtual,
                        "preco_media_janela": float(np.mean(var_listPrecosJanela)),
                        "preco_std_janela": float(np.std(var_listPrecosJanela)),
                        "preco_min_janela": float(np.min(var_listPrecosJanela)),
                        "preco_max_janela": float(np.max(var_listPrecosJanela)),
                        "desconto_atual": float(var_dictAtual.get("desconto", 0.0)),
                        "desconto_medio_janela": float(np.mean(var_listDescontosJanela)),
                        "desconto_max_janela": float(np.max(var_listDescontosJanela)),
                        "num_promocoes_janela": int(sum(1 for d in var_listDescontosJanela if d > 0)),
                        "dias_janela": int((var_listTimestampsJanela[-1] - var_listTimestampsJanela[0]) / 86400),
                        "dias_desde_ultimo_desconto": var_intDiasDesdeUltimoDesconto,
                        "alvo_direcao_preco": var_strDirecao,
                        "alvo_dias_ate_desconto": var_intDiasProxDesconto,
                    }
                )

        cls._var_dfAmostrasTemporais = pd.DataFrame(var_listAmostras)
        if cls._var_dfAmostrasTemporais.empty:
            raise ValueError("Nenhuma amostra temporal foi gerada a partir de historico_preco.")

        logger.info(
            "Amostras temporais criadas: %s (classes: %s)",
            len(cls._var_dfAmostrasTemporais),
            cls._var_dfAmostrasTemporais["alvo_direcao_preco"].value_counts().to_dict(),
        )

        return cls._var_dfAmostrasTemporais

    @classmethod
    def _obter_splits(cls) -> dict:
        """
        Prepara split único para manter comparabilidade entre modelos.
        
        Parâmetros:

        Retorna:
        - dict: Dicionário contendo os splits de treino e teste para classificação e regressão.
        """
        if cls._var_dictSplits is not None:
            return cls._var_dictSplits

        if cls._var_dfAmostrasTemporais is None:
            cls._construir_amostras_temporais()

        var_df = cls._var_dfAmostrasTemporais.copy()
        var_listFeatures = [
            "review_score",
            "preco_catalogo",
            "preco_atual_hist",
            "preco_media_janela",
            "preco_std_janela",
            "preco_min_janela",
            "preco_max_janela",
            "desconto_atual",
            "desconto_medio_janela",
            "desconto_max_janela",
            "num_promocoes_janela",
            "dias_janela",
            "dias_desde_ultimo_desconto",
        ]

        var_X = var_df[var_listFeatures].fillna(0.0)

        var_mapRotulo = {"cai": 0, "mantem": 1, "sobe": 2}
        var_yClass = var_df["alvo_direcao_preco"].map(var_mapRotulo)

        var_X_train, var_X_test, var_y_train, var_y_test = train_test_split(
            var_X,
            var_yClass,
            test_size=0.2,
            random_state=42,
            stratify=var_yClass,
        )

        var_dfReg = var_df.dropna(subset=["alvo_dias_ate_desconto"]).copy()
        var_X_reg = var_dfReg[var_listFeatures].fillna(0.0)
        var_y_reg = pd.to_numeric(var_dfReg["alvo_dias_ate_desconto"], errors="coerce")

        var_Xr_train, var_Xr_test, var_yr_train, var_yr_test = train_test_split(
            var_X_reg,
            var_y_reg,
            test_size=0.2,
            random_state=42,
        )

        cls._var_dictSplits = {
            "X_train": var_X_train,
            "X_test": var_X_test,
            "y_train": var_y_train,
            "y_test": var_y_test,
            "Xr_train": var_Xr_train,
            "Xr_test": var_Xr_test,
            "yr_train": var_yr_train,
            "yr_test": var_yr_test,
        }
        return cls._var_dictSplits

    @classmethod
    def treinar_modelo_regressao_linear(cls) -> dict:
        """
        Método para treinar o modelo de Regressão Linear.

        Parâmetros:

        Retorna:
        - dict: Dicionário contendo o modelo treinado, RMSE e tamanhos dos conjuntos de treino e teste.
        """
        logger.info("Começando treinamento do modelo de Regressão Linear...")
        var_dictSplits = cls._obter_splits()

        var_modelo = LinearRegression()
        var_modelo.fit(var_dictSplits["Xr_train"], var_dictSplits["yr_train"])
        var_arrPred = var_modelo.predict(var_dictSplits["Xr_test"])
        var_floatRmse = mean_squared_error(var_dictSplits["yr_test"], var_arrPred, squared=False)

        logger.info("Regressão linear (dias até desconto) - RMSE: %.2f dias", var_floatRmse)
        return {
            "modelo": var_modelo,
            "rmse": var_floatRmse,
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
        logger.info("Começando treinamento do modelo de Random Forest...")
        var_dictSplits = cls._obter_splits()

        var_modelo = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            n_jobs=-1,
            random_state=42,
        )
        var_modelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])
        var_arrPred = var_modelo.predict(var_dictSplits["X_test"])

        var_floatAcc = accuracy_score(var_dictSplits["y_test"], var_arrPred)
        var_floatF1 = f1_score(var_dictSplits["y_test"], var_arrPred, average="macro")

        logger.info("Random Forest (direção de preço) - ACC: %.4f | F1-macro: %.4f", var_floatAcc, var_floatF1)
        return {
            "modelo": var_modelo,
            "accuracy": var_floatAcc,
            "f1_macro": var_floatF1,
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
        logger.info("Começando treinamento do modelo de XGBoost...")
        var_dictSplits = cls._obter_splits()

        var_modelo = xgb.XGBClassifier(
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
        var_modelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])
        var_arrPred = var_modelo.predict(var_dictSplits["X_test"])

        var_floatAcc = accuracy_score(var_dictSplits["y_test"], var_arrPred)
        var_floatF1 = f1_score(var_dictSplits["y_test"], var_arrPred, average="macro")

        logger.info("XGBoost (direção de preço) - ACC: %.4f | F1-macro: %.4f", var_floatAcc, var_floatF1)
        return {
            "modelo": var_modelo,
            "accuracy": var_floatAcc,
            "f1_macro": var_floatF1,
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
        logger.info("Começando treinamento do modelo de LightGBM...")
        var_dictSplits = cls._obter_splits()

        var_modelo = lgb.LGBMClassifier(
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
        var_modelo.fit(var_dictSplits["X_train"], var_dictSplits["y_train"])
        var_arrPred = var_modelo.predict(var_dictSplits["X_test"])

        var_floatAcc = accuracy_score(var_dictSplits["y_test"], var_arrPred)
        var_floatF1 = f1_score(var_dictSplits["y_test"], var_arrPred, average="macro")

        logger.info("LightGBM (direção de preço) - ACC: %.4f | F1-macro: %.4f", var_floatAcc, var_floatF1)
        return {
            "modelo": var_modelo,
            "accuracy": var_floatAcc,
            "f1_macro": var_floatF1,
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
            "LightGBM - Treinamento: %s, Teste: %s, ACC: %.4f, F1: %.4f",
            var_dictLGBM["train_size"],
            var_dictLGBM["test_size"],
            var_dictLGBM["accuracy"],
            var_dictLGBM["f1_macro"],
        )
        logger.info(
            "XGBoost - Treinamento: %s, Teste: %s, ACC: %.4f, F1: %.4f",
            var_dictXGB["train_size"],
            var_dictXGB["test_size"],
            var_dictXGB["accuracy"],
            var_dictXGB["f1_macro"],
        )
        logger.info(
            "Random Forest - Treinamento: %s, Teste: %s, ACC: %.4f, F1: %.4f",
            var_dictRF["train_size"],
            var_dictRF["test_size"],
            var_dictRF["accuracy"],
            var_dictRF["f1_macro"],
        )
        logger.info(
            "Regressão Linear (dias até desconto) - Treinamento: %s, Teste: %s, RMSE: %.2f dias",
            var_dictReg["train_size"],
            var_dictReg["test_size"],
            var_dictReg["rmse"],
        )
        logger.info("Treinamento de todos os modelos concluído com sucesso.")

Treinar_Modelos.executar_treinamento()