"""
Script de exportação de modelos ML com nomenclatura padronizada.

Avalia os modelos treinados, seleciona o melhor por categoria/horizonte,
e exporta com nomenclatura padronizada para distribuição via GitHub Releases.

Nomenclatura de saída:
    Classificação: modelo_classificacao_30d.joblib, modelo_classificacao_60d.joblib, modelo_classificacao_90d.joblib
    Regressão:     modelo_regressao_30d.joblib, modelo_regressao_60d.joblib, modelo_regressao_90d.joblib
    Geral:         modelo_latest.joblib (melhor classificador geral)
    Metadados:     manifest.json

Uso:
    # Chamado automaticamente ao final do treinamento
    ExportarModelos.exportar(var_dictTodosModelos)

    # Ou via linha de comando (re-exporta dos modelos _latest existentes, sem métricas)
    python -m prj_TCC_PREVISOR_STEAM.classes.treinamento.exportar_modelos
"""
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import AllSettings
from prj_TCC_PREVISOR_STEAM.classes.utils.model_registry import ModelRegistry
import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

import joblib

logger = logging.getLogger("treino.exportar")


class ExportarModelos:
    """
    Classe responsável por exportar os melhores modelos treinados com nomenclatura padronizada.
    """

    @classmethod
    def _calcular_sha256(cls, arg_pathArquivo: Path) -> str:
        """
        Calcula o hash SHA-256 de um arquivo.

        Parâmetros:
        - arg_pathArquivo (Path): Caminho do arquivo.

        Retorna:
        - str: Hash SHA-256 hexadecimal do arquivo.
        """
        var_objHash = hashlib.sha256()
        with open(arg_pathArquivo, "rb") as var_fileObj:
            for var_bytesChunk in iter(lambda: var_fileObj.read(8192), b""):
                var_objHash.update(var_bytesChunk)
        return var_objHash.hexdigest()

    @classmethod
    def _obter_diretorio_export(cls) -> Path:
        """
        Obtém o diretório de exportação (resources/models/export).

        Retorna:
        - Path: Caminho do diretório de exportação.
        """
        var_pathBase = Path(__file__).resolve().parents[2]
        var_pathExport = var_pathBase / "resources" / "models" / "export"
        var_pathExport.mkdir(parents=True, exist_ok=True)
        return var_pathExport

    @classmethod
    def exportar(cls, arg_dictModelos: dict) -> Path:
        """
        Exporta os melhores modelos com nomenclatura padronizada.

        Avalia os modelos por categoria e horizonte, seleciona o melhor
        de cada, e exporta para resources/models/export/ com nomes padronizados.

        Parâmetros:
        - arg_dictModelos (dict): Dicionário com modelos treinados.
            Estrutura esperada:
            {
                "classificacao": {horizonte: {algo: {modelo, accuracy, f1_macro, ...}}},
                "regressao": {horizonte: {algo: {modelo, rmse, mae, mse, ...}}}
            }

        Retorna:
        - Path: Caminho do diretório de exportação.
        """
        var_pathExport = cls._obter_diretorio_export()

        logger.info("=" * 60)
        logger.info("EXPORTAÇÃO DE MODELOS - NOMENCLATURA PADRONIZADA")
        logger.info(f"Diretório: {var_pathExport}")
        logger.info("=" * 60)

        var_dictManifest = {
            "version": cls._obter_versao_projeto(),
            "exported_at": datetime.now().isoformat(),
            "github_repo": "camiloprado/SteamPrev_Machine_Learning",
            "models": {},
        }

        var_floatMelhorF1Global = -1.0
        var_strMelhorHorizonteGlobal = None
        var_strMelhorAlgoGlobal = None

        # =====================================================================
        # CLASSIFICAÇÃO — Seleciona melhor modelo por horizonte (F1-macro)
        # =====================================================================
        if "classificacao" in arg_dictModelos:
            for var_strHorizonte, var_dictAlgos in arg_dictModelos["classificacao"].items():
                # Encontra o melhor algoritmo para este horizonte
                var_strMelhorAlgo = None
                var_floatMelhorF1 = -1.0

                for var_strAlgo, var_dictResultado in var_dictAlgos.items():
                    var_floatF1 = var_dictResultado.get("f1_macro", 0.0)
                    if var_floatF1 > var_floatMelhorF1:
                        var_floatMelhorF1 = var_floatF1
                        var_strMelhorAlgo = var_strAlgo

                if var_strMelhorAlgo is None:
                    logger.warning(f"Nenhum modelo de classificação encontrado para horizonte: {var_strHorizonte}")
                    continue

                var_objModelo = var_dictAlgos[var_strMelhorAlgo]["modelo"]
                var_strNomeArq = f"modelo_classificacao_{var_strHorizonte}.joblib"
                var_pathArq = var_pathExport / var_strNomeArq

                joblib.dump(var_objModelo, var_pathArq)
                var_strHash = cls._calcular_sha256(var_pathArq)

                var_dictManifest["models"][var_strNomeArq] = {
                    "algorithm": var_strMelhorAlgo,
                    "type": "classificacao",
                    "horizon": var_strHorizonte,
                    "metrics": {
                        "f1_macro": round(var_floatMelhorF1, 6),
                        "accuracy": round(var_dictAlgos[var_strMelhorAlgo].get("accuracy", 0.0), 6),
                        "precision_macro": round(var_dictAlgos[var_strMelhorAlgo].get("precision_macro", 0.0), 6),
                    },
                    "sha256": var_strHash,
                    "size_bytes": var_pathArq.stat().st_size,
                }

                logger.info(
                    f"✅ Exportado: {var_strNomeArq} "
                    f"(Algoritmo: {var_strMelhorAlgo}, F1: {var_floatMelhorF1:.4f})"
                )

                # Rastreia o melhor classificador global
                if var_floatMelhorF1 > var_floatMelhorF1Global:
                    var_floatMelhorF1Global = var_floatMelhorF1
                    var_strMelhorHorizonteGlobal = var_strHorizonte
                    var_strMelhorAlgoGlobal = var_strMelhorAlgo

        # =====================================================================
        # MODELO LATEST — Alias para o melhor classificador geral
        # =====================================================================
        if var_strMelhorHorizonteGlobal is not None:
            var_strNomeFonte = f"modelo_classificacao_{var_strMelhorHorizonteGlobal}.joblib"
            var_pathFonte = var_pathExport / var_strNomeFonte
            var_pathLatest = var_pathExport / "modelo_latest.joblib"

            shutil.copy2(var_pathFonte, var_pathLatest)
            var_strHashLatest = cls._calcular_sha256(var_pathLatest)

            var_dictManifest["models"]["modelo_latest.joblib"] = {
                "algorithm": var_strMelhorAlgoGlobal,
                "type": "classificacao",
                "horizon": var_strMelhorHorizonteGlobal,
                "alias_of": var_strNomeFonte,
                "metrics": var_dictManifest["models"][var_strNomeFonte]["metrics"],
                "sha256": var_strHashLatest,
                "size_bytes": var_pathLatest.stat().st_size,
            }

            logger.info(
                f"✅ Alias: modelo_latest.joblib → {var_strNomeFonte} "
                f"({var_strMelhorAlgoGlobal}, F1: {var_floatMelhorF1Global:.4f})"
            )

        # =====================================================================
        # REGRESSÃO — Seleciona melhor modelo por horizonte (menor RMSE)
        # =====================================================================
        if "regressao" in arg_dictModelos:
            for var_strHorizonte, var_dictAlgos in arg_dictModelos["regressao"].items():
                var_strMelhorAlgoReg = None
                var_floatMelhorRMSE = float("inf")

                for var_strAlgo, var_dictResultado in var_dictAlgos.items():
                    var_floatRMSE = var_dictResultado.get("rmse", float("inf"))
                    if var_floatRMSE < var_floatMelhorRMSE:
                        var_floatMelhorRMSE = var_floatRMSE
                        var_strMelhorAlgoReg = var_strAlgo

                if var_strMelhorAlgoReg is None:
                    logger.warning(f"Nenhum modelo de regressão encontrado para horizonte: {var_strHorizonte}")
                    continue

                var_objModeloReg = var_dictAlgos[var_strMelhorAlgoReg]["modelo"]
                var_strNomeArqReg = f"modelo_regressao_{var_strHorizonte}.joblib"
                var_pathArqReg = var_pathExport / var_strNomeArqReg

                joblib.dump(var_objModeloReg, var_pathArqReg)
                var_strHashReg = cls._calcular_sha256(var_pathArqReg)

                var_dictManifest["models"][var_strNomeArqReg] = {
                    "algorithm": var_strMelhorAlgoReg,
                    "type": "regressao",
                    "horizon": var_strHorizonte,
                    "metrics": {
                        "rmse": round(var_floatMelhorRMSE, 6),
                        "mae": round(var_dictAlgos[var_strMelhorAlgoReg].get("mae", 0.0), 6),
                        "mse": round(var_dictAlgos[var_strMelhorAlgoReg].get("mse", 0.0), 6),
                    },
                    "sha256": var_strHashReg,
                    "size_bytes": var_pathArqReg.stat().st_size,
                }

                logger.info(
                    f"✅ Exportado: {var_strNomeArqReg} "
                    f"(Algoritmo: {var_strMelhorAlgoReg}, RMSE: {var_floatMelhorRMSE:.2f} dias)"
                )

        # =====================================================================
        # MANIFEST — Salva metadados da exportação
        # =====================================================================
        var_pathManifest = var_pathExport / "manifest.json"
        with open(var_pathManifest, "w", encoding="utf-8") as var_fileManifest:
            json.dump(var_dictManifest, var_fileManifest, indent=2, ensure_ascii=False)

        logger.info(f"📋 Manifest salvo: {var_pathManifest}")
        logger.info(f"Total de modelos exportados: {len(var_dictManifest['models'])}")
        logger.info("=" * 60)
        logger.info("EXPORTAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info("=" * 60)

        return var_pathExport

    @classmethod
    def _obter_versao_projeto(cls) -> str:
        """
        Lê a versão do projeto do arquivo VERSION.

        Retorna:
        - str: Versão do projeto ou 'unknown' se não encontrado.
        """
        try:
            var_pathVersion = Path(__file__).resolve().parents[3] / "VERSION"
            return var_pathVersion.read_text(encoding="utf-8").strip()
        except Exception:
            return "unknown"


if __name__ == "__main__":
    # Re-exportação standalone: carrega modelos _latest existentes
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    logger.info("Re-exportação standalone dos modelos _latest existentes...")
    logger.warning(
        "Modo standalone não re-avalia métricas. "
        "Para exportação com métricas, execute o treinamento completo."
    )

    var_pathModels = Path(__file__).resolve().parents[2] / "resources" / "models"

    if not var_pathModels.exists():
        logger.error(f"Diretório de modelos não encontrado: {var_pathModels}")
        sys.exit(1)

    # Constrói dict simulado com modelos _latest (sem métricas reais)
    var_dictModelos: dict = {"classificacao": {}, "regressao": {}}
    var_listHorizontes = ["30d", "60d", "90d"]
    var_listAlgosClass = ["LightGBM", "XGBoost", "RandomForest"]
    var_listAlgosReg = ["LightGBM", "XGBoost", "LinearRegression"]

    for var_strHorizonte in var_listHorizontes:
        var_dictModelos["classificacao"][var_strHorizonte] = {}
        for var_strAlgo in var_listAlgosClass:
            var_pathLatest = var_pathModels / f"modelo_classificacao_{var_strAlgo}_{var_strHorizonte}_latest.joblib"
            if var_pathLatest.exists():
                var_objModelo = ModelRegistry.get_model(var_pathLatest)
                var_dictModelos["classificacao"][var_strHorizonte][var_strAlgo] = {
                    "modelo": var_objModelo,
                    "f1_macro": 0.0,
                    "accuracy": 0.0,
                    "precision_macro": 0.0,
                }
                logger.info(f"Carregado: {var_pathLatest.name}")

        var_dictModelos["regressao"][var_strHorizonte] = {}
        for var_strAlgo in var_listAlgosReg:
            var_pathLatest = var_pathModels / f"modelo_regressao_{var_strAlgo}_{var_strHorizonte}_latest.joblib"
            if not var_pathLatest.exists():
                # Fallback para naming sem horizonte (modelos antigos)
                var_pathLatest = var_pathModels / f"modelo_regressao_{var_strAlgo}_latest.joblib"
            if var_pathLatest.exists():
                var_objModelo = ModelRegistry.get_model(var_pathLatest)
                var_dictModelos["regressao"][var_strHorizonte][var_strAlgo] = {
                    "modelo": var_objModelo,
                    "rmse": 0.0,
                    "mae": 0.0,
                    "mse": 0.0,
                }
                logger.info(f"Carregado: {var_pathLatest.name}")

    var_boolTemClassificacao = any(var_dictModelos["classificacao"].values())
    var_boolTemRegressao = any(var_dictModelos["regressao"].values())

    if not var_boolTemClassificacao and not var_boolTemRegressao:
        logger.error("Nenhum modelo _latest encontrado para exportar.")
        sys.exit(1)

    ExportarModelos.exportar(var_dictModelos)
