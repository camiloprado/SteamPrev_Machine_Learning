from prj_TCC_PREVISOR_STEAM.classes.treinamento.normalizar_modelos import NormalizarModelos
from prj_TCC_PREVISOR_STEAM.classes.treinamento.exportar_modelos import ExportarModelos

from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinar_classificadores import TreinarClassificadores
from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinar_regressores import TreinarRegressores

import joblib
import shutil
from pathlib import Path
from datetime import datetime
import os
import logging

logger = logging.getLogger("treino.modelos")

class Treinar_Modelos:
    """
    Classe responsável por unificar o treinamento entre os diversos modelos preditivos utilizados no projeto.
    (Versão Refatorada - Delega a execução para módulos especializados)
    """

    @classmethod
    def executar_treinamento(cls):
        """
        Método para executar o treinamento de todos os modelos para todos os horizontes temporais.

        Parâmetros:

        Retorna:
        """
        logger.info("=" * 80)
        logger.info("INICIANDO TREINAMENTO DE MODELOS DE CLASSIFICAÇÃO E REGRESSÃO")
        logger.info("=" * 80)

        var_listHorizontes = NormalizarModelos.obter_horizontes_disponiveis()
        var_dictModelosClassificacao = {}

        for var_strHorizonte in var_listHorizontes:
            logger.info("=" * 80)
            logger.info(f"TREINANDO CLASSIFICADORES - HORIZONTE: {var_strHorizonte}")
            logger.info("=" * 80)

            var_dictLGBM = TreinarClassificadores.treinar_modelo_lightgbm(arg_strHorizonte=var_strHorizonte)
            var_dictXGB = TreinarClassificadores.treinar_modelo_xgboost(arg_strHorizonte=var_strHorizonte)
            var_dictRF = TreinarClassificadores.treinar_modelo_random_forest(arg_strHorizonte=var_strHorizonte)

            var_dictModelosClassificacao[var_strHorizonte] = {
                "LightGBM": var_dictLGBM,
                "XGBoost": var_dictXGB,
                "RandomForest": var_dictRF,
            }

            logger.info("-" * 80)
            logger.info(f"RESUMO COMPARATIVO - {var_strHorizonte.upper()}")
            logger.info(f"{'Modelo':<18} | {'Accuracy':>10} | {'Precision':>10} | {'F1-Score':>10} | Dataset")
            logger.info("-" * 80)

            for var_strNome, var_dictMetricas in var_dictModelosClassificacao[var_strHorizonte].items():
                logger.info(
                    f"{var_strNome:<18} | {var_dictMetricas['accuracy']:>10.4f} | "
                    f"{var_dictMetricas['precision_macro']:>10.4f} | {var_dictMetricas['f1_macro']:>10.4f} | "
                    f"{var_dictMetricas['train_size']:,} treino / {var_dictMetricas['test_size']:,} teste"
                )

            var_strMelhorModelo = max(var_dictModelosClassificacao[var_strHorizonte].items(), key=lambda x: x[1]['f1_macro'])[0]
            var_floatMelhorF1 = var_dictModelosClassificacao[var_strHorizonte][var_strMelhorModelo]['f1_macro']
            logger.info(f"MELHOR MODELO ({var_strHorizonte}): {var_strMelhorModelo} (F1-Score: {var_floatMelhorF1:.4f})")

        # =====================================================================
        # TREINA REGRESSORES DE DIAS E DE DESCONTO, POR HORIZONTE
        # =====================================================================
        # O regressor de desconto (profundidade esperada do desconto) é treinado
        # DENTRO do loop por horizonte, usando o conjunto filtrado por horizonte
        # vindo de NormalizarModelos (apenas jogos cujo desconto de fato ocorreu
        # dentro da janela do horizonte). Antes desta correção, o regressor de
        # desconto era treinado uma única vez com horizonte fixo "30d" e o mesmo
        # modelo era copiado para os 3 horizontes, dando falsa impressão de
        # diferenciação por horizonte nos arquivos .joblib salvos em disco.
        var_dictModelosRegressaoDias = {}
        var_dictModelosRegressaoDesconto = {}

        for var_strHorizonte in var_listHorizontes:
            logger.info("=" * 80)
            logger.info(f"TREINANDO REGRESSORES (DIAS) - HORIZONTE: {var_strHorizonte}")
            logger.info("=" * 80)

            var_dictReg = TreinarRegressores.treinar_modelo_regressao_linear(arg_strHorizonte=var_strHorizonte, arg_strAlvo="dias")
            var_dictRegXGB = TreinarRegressores.treinar_modelo_xgboost_regressao(arg_strHorizonte=var_strHorizonte, arg_strAlvo="dias")
            var_dictRegLGB = TreinarRegressores.treinar_modelo_lightgbm_regressao(arg_strHorizonte=var_strHorizonte, arg_strAlvo="dias")

            var_dictModelosRegressaoDias[var_strHorizonte] = {
                "LightGBM": var_dictRegLGB,
                "XGBoost": var_dictRegXGB,
                "LinearRegression": var_dictReg,
            }

            logger.info("-" * 80)
            logger.info(f"RESUMO COMPARATIVO - REGRESSÃO ({var_strHorizonte.upper()})")
            logger.info(f"{'Modelo':<18} | {'RMSE (dias)':>12} | {'MAE (dias)':>11} | {'MSE':>10} | Dataset")
            logger.info("-" * 80)

            for var_strNome, var_dictMetricas in var_dictModelosRegressaoDias[var_strHorizonte].items():
                logger.info(
                    f"{var_strNome:<18} | {var_dictMetricas['rmse']:>12.2f} | "
                    f"{var_dictMetricas['mae']:>11.2f} | {var_dictMetricas['mse']:>10.2f} | "
                    f"{var_dictMetricas['train_size']:,} treino / {var_dictMetricas['test_size']:,} teste"
                )

            var_strMelhorRegressor = min(var_dictModelosRegressaoDias[var_strHorizonte].items(), key=lambda x: x[1]["rmse"])[0]
            var_floatMelhorRMSE = var_dictModelosRegressaoDias[var_strHorizonte][var_strMelhorRegressor]["rmse"]
            logger.info(f"MELHOR MODELO REGRESSÃO ({var_strHorizonte}): {var_strMelhorRegressor} (RMSE: {var_floatMelhorRMSE:.2f} dias)")

            # -----------------------------------------------------------------
            # REGRESSORES DE DESCONTO — TREINADOS PARA ESTE HORIZONTE
            # -----------------------------------------------------------------
            logger.info("=" * 80)
            logger.info(f"TREINANDO REGRESSORES (DESCONTO) - HORIZONTE: {var_strHorizonte}")
            logger.info("=" * 80)

            var_dictRegDesc = TreinarRegressores.treinar_modelo_regressao_linear(arg_strHorizonte=var_strHorizonte, arg_strAlvo="desconto")
            var_dictRegXGBDesc = TreinarRegressores.treinar_modelo_xgboost_regressao(arg_strHorizonte=var_strHorizonte, arg_strAlvo="desconto")
            var_dictRegLGBDesc = TreinarRegressores.treinar_modelo_lightgbm_regressao(arg_strHorizonte=var_strHorizonte, arg_strAlvo="desconto")

            var_dictModelosRegressaoDesconto[var_strHorizonte] = {
                "LightGBM": var_dictRegLGBDesc,
                "XGBoost": var_dictRegXGBDesc,
                "LinearRegression": var_dictRegDesc,
            }

            logger.info("-" * 80)
            logger.info(f"RESUMO COMPARATIVO - REGRESSÃO DESCONTO ({var_strHorizonte.upper()})")
            logger.info(f"{'Modelo':<18} | {'RMSE (%)':>12} | {'MAE (%)':>11} | {'MSE':>10} | Dataset")
            logger.info("-" * 80)

            for var_strNome, var_dictMetricas in var_dictModelosRegressaoDesconto[var_strHorizonte].items():
                logger.info(
                    f"{var_strNome:<18} | {var_dictMetricas['rmse']:>12.2f} | "
                    f"{var_dictMetricas['mae']:>11.2f} | {var_dictMetricas['mse']:>10.2f} | "
                    f"{var_dictMetricas['train_size']:,} treino / {var_dictMetricas['test_size']:,} teste"
                )

            var_strMelhorRegressorDesc = min(var_dictModelosRegressaoDesconto[var_strHorizonte].items(), key=lambda x: x[1]["rmse"])[0]
            var_floatMelhorRMSEDesc = var_dictModelosRegressaoDesconto[var_strHorizonte][var_strMelhorRegressorDesc]["rmse"]
            logger.info(f"MELHOR MODELO REGRESSÃO DESCONTO ({var_strHorizonte}): {var_strMelhorRegressorDesc} (RMSE: {var_floatMelhorRMSEDesc:.2f}%)")

        logger.info("="*80)
        logger.info("TREINAMENTO CONCLUÍDO COM SUCESSO")
        logger.info("Matrizes de confusão salvas em: resources/relatorios/")
        logger.info("="*80)

        try:
            var_dictTodosModelos = {
                "classificacao": var_dictModelosClassificacao,
                "regressao_dias": var_dictModelosRegressaoDias,
                "regressao_desconto": var_dictModelosRegressaoDesconto,
            }
            cls._salvar_modelos(var_dictTodosModelos)
        except Exception as e:
            logger.warning(f"Falha ao salvar modelos em disco: {e}")

        # Exportar melhores modelos com nomenclatura padronizada
        try:
            ExportarModelos.exportar(var_dictTodosModelos)
        except Exception as e:
            logger.warning(f"Falha ao exportar modelos padronizados: {e}")


    @classmethod
    def _salvar_modelos(cls, arg_dictModelos: dict) -> None:
        """
        Persiste todos os modelos treinados em resources/models/.

        Parâmetros:
        - arg_dictModelos (dict)

        Retorna:
        - None
        """
        var_strSalvar = (os.getenv("ML_SALVAR_MODELOS", "True") or "True").strip().lower()
        if var_strSalvar in ("0", "false", "no", "nao"):
            logger.info("ML_SALVAR_MODELOS=False — modelos não serão salvos em disco.")
            return

        var_pathModels = Path(__file__).resolve().parents[2] / "resources" / "models"
        var_pathModels.mkdir(parents=True, exist_ok=True)
        var_strTimestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info("="*60)
        logger.info("SALVANDO MODELOS EM DISCO")
        logger.info(f"Diretório: {var_pathModels}")
        logger.info("="*60)

        if "classificacao" in arg_dictModelos:
            for var_strHorizonte, var_dictAlgos in arg_dictModelos["classificacao"].items():
                for var_strAlgo, var_dictResultado in var_dictAlgos.items():
                    var_objModelo = var_dictResultado.get("modelo")
                    if var_objModelo is None:
                        continue

                    var_strNomeArq = f"modelo_classificacao_{var_strAlgo}_{var_strHorizonte}_{var_strTimestamp}.joblib"
                    var_pathArq = var_pathModels / var_strNomeArq
                    joblib.dump(var_objModelo, var_pathArq)
                    logger.info(f"Salvo: {var_strNomeArq}")

                    # Copia o arquivo versionado para o alias _latest (evita segundo joblib.dump)
                    var_strNomeLatest = f"modelo_classificacao_{var_strAlgo}_{var_strHorizonte}_latest.joblib"
                    var_pathLatest = var_pathModels / var_strNomeLatest
                    shutil.copy2(var_pathArq, var_pathLatest)
                    logger.info(f"Atualizado: {var_strNomeLatest}")

        # As chaves reais em arg_dictModelos são "regressao_dias" e "regressao_desconto"
        # (ver executar_treinamento -> var_dictTodosModelos). Iterar sobre as duas garante
        # que ambos os regressores sejam persistidos em disco com nomes que os distinguem.
        for var_strTipoRegressao in ("regressao_dias", "regressao_desconto"):
            if var_strTipoRegressao not in arg_dictModelos:
                continue

            for var_strHorizonte, var_dictAlgos in arg_dictModelos[var_strTipoRegressao].items():
                for var_strAlgo, var_dictResultado in var_dictAlgos.items():
                    var_objModelo = var_dictResultado.get("modelo")
                    if var_objModelo is None:
                        continue

                    var_strNomeArq = f"modelo_{var_strTipoRegressao}_{var_strAlgo}_{var_strHorizonte}_{var_strTimestamp}.joblib"
                    var_pathArq = var_pathModels / var_strNomeArq
                    joblib.dump(var_objModelo, var_pathArq)
                    logger.info(f"Salvo: {var_strNomeArq}")

                    # Copia o arquivo versionado para o alias _latest (evita segundo joblib.dump)
                    var_strNomeLatest = f"modelo_{var_strTipoRegressao}_{var_strAlgo}_{var_strHorizonte}_latest.joblib"
                    var_pathLatest = var_pathModels / var_strNomeLatest
                    shutil.copy2(var_pathArq, var_pathLatest)
                    logger.info(f"Atualizado: {var_strNomeLatest}")

        logger.info("="*60)
        logger.info("MODELOS SALVOS COM SUCESSO")
        logger.info("="*60)
