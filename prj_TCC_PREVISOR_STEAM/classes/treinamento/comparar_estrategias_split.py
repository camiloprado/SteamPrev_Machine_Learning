"""
Compara as estratégias de split (grupo, walkforward, grupo_temporal) treinando
o pipeline completo sob cada uma e reportando qual performa melhor por horizonte.

Só a estratégia "grupo" é exportada/publicada (resources/models/export/, GitHub
Releases) — as demais são diagnósticas, para sustentar a discussão metodológica
do TCC, e não alteram os artefatos de produção.

Uso:
    python -m prj_TCC_PREVISOR_STEAM.classes.treinamento.comparar_estrategias_split
"""
import logging
import os

from prj_TCC_PREVISOR_STEAM.classes.treinamento.normalizar_modelos import NormalizarModelos
from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinar_modelos import Treinar_Modelos

logger = logging.getLogger("treino.comparador")


class ComparadorEstrategiasSplit:
    """
    Orquestra o treino completo sob múltiplas estratégias de split para comparação.
    """

    _var_listEstrategiasPadrao = ["grupo", "walkforward", "grupo_temporal"]

    @classmethod
    def executar_comparativo(cls, arg_listEstrategias: list[str] | None = None) -> dict:
        """
        Treina o pipeline completo (classificação + regressão, todos os horizontes)
        sob cada estratégia de split e resume o melhor F1-macro/RMSE por horizonte.

        Parâmetros:
        - arg_listEstrategias (list[str] | None): Estratégias a comparar
          (subconjunto de "grupo", "walkforward", "grupo_temporal"). Padrão: as três.

        Retorna:
        - dict: {estrategia: {"classificacao": {...}, "regressao_dias": {...}, "regressao_desconto": {...}}}
        """
        var_listEstrategias = arg_listEstrategias or cls._var_listEstrategiasPadrao
        var_strEstrategiaOriginal = os.getenv("ML_ESTRATEGIA_SPLIT", "grupo")

        # Constrói amostras temporais e calendário empírico UMA VEZ — reaproveitados
        # entre as estratégias (só o split em si muda a cada iteração).
        if NormalizarModelos._var_dfAmostrasTemporais is None:
            NormalizarModelos._construir_amostras_temporais()

        var_dictResultadosPorEstrategia = {}

        try:
            for var_strEstrategia in var_listEstrategias:
                logger.info("=" * 80)
                logger.info(f"COMPARATIVO DE SPLIT — ESTRATÉGIA: {var_strEstrategia}")
                logger.info("=" * 80)

                os.environ["ML_ESTRATEGIA_SPLIT"] = var_strEstrategia
                NormalizarModelos._var_dictSplits = None  # força recomputar o split com a nova estratégia

                var_dictResultadosPorEstrategia[var_strEstrategia] = Treinar_Modelos.executar_treinamento(
                    arg_boolExportar=(var_strEstrategia == "grupo")
                )
        finally:
            # Restaura o estado original — próximos treinos normais usam a estratégia configurada no .env.
            os.environ["ML_ESTRATEGIA_SPLIT"] = var_strEstrategiaOriginal
            NormalizarModelos._var_dictSplits = None

        cls._logar_resumo_comparativo(var_dictResultadosPorEstrategia)
        return var_dictResultadosPorEstrategia

    @classmethod
    def _logar_resumo_comparativo(cls, arg_dictResultados: dict) -> None:
        """Loga uma tabela comparativa (melhor F1-macro/RMSE por horizonte e estratégia) e a estratégia vencedora."""
        var_listHorizontes = NormalizarModelos.obter_horizontes_disponiveis()

        logger.info("=" * 80)
        logger.info("RESUMO COMPARATIVO DE ESTRATÉGIAS DE SPLIT")
        logger.info("=" * 80)

        var_dictMediaF1PorEstrategia = {}
        var_dictMediaRmsePorEstrategia = {}

        for var_strEstrategia, var_dictModelos in arg_dictResultados.items():
            var_listF1 = []
            var_listRmse = []

            logger.info(f"-- {var_strEstrategia} --")
            for var_strHorizonte in var_listHorizontes:
                var_dictClf = var_dictModelos.get("classificacao", {}).get(var_strHorizonte, {})
                if var_dictClf:
                    var_strMelhorAlgo = max(var_dictClf.items(), key=lambda x: x[1]["f1_macro"])[0]
                    var_floatF1 = var_dictClf[var_strMelhorAlgo]["f1_macro"]
                    var_listF1.append(var_floatF1)
                    logger.info(f"  Classificação {var_strHorizonte}: melhor={var_strMelhorAlgo} | F1-macro={var_floatF1:.4f}")

                var_dictReg = var_dictModelos.get("regressao_dias", {}).get(var_strHorizonte, {})
                if var_dictReg:
                    var_strMelhorAlgoReg = min(var_dictReg.items(), key=lambda x: x[1]["rmse"])[0]
                    var_floatRmse = var_dictReg[var_strMelhorAlgoReg]["rmse"]
                    var_listRmse.append(var_floatRmse)
                    logger.info(f"  Regressão dias {var_strHorizonte}: melhor={var_strMelhorAlgoReg} | RMSE={var_floatRmse:.2f}")

            if var_listF1:
                var_dictMediaF1PorEstrategia[var_strEstrategia] = sum(var_listF1) / len(var_listF1)
            if var_listRmse:
                var_dictMediaRmsePorEstrategia[var_strEstrategia] = sum(var_listRmse) / len(var_listRmse)

        logger.info("-" * 80)
        if var_dictMediaF1PorEstrategia:
            var_strMelhorClf = max(var_dictMediaF1PorEstrategia.items(), key=lambda x: x[1])[0]
            for var_strEstrategia, var_floatMedia in var_dictMediaF1PorEstrategia.items():
                logger.info(f"F1-macro médio ({var_strEstrategia}): {var_floatMedia:.4f}")
            logger.info(f"MELHOR ESTRATÉGIA (classificação, F1-macro médio): {var_strMelhorClf}")

        if var_dictMediaRmsePorEstrategia:
            var_strMelhorReg = min(var_dictMediaRmsePorEstrategia.items(), key=lambda x: x[1])[0]
            for var_strEstrategia, var_floatMedia in var_dictMediaRmsePorEstrategia.items():
                logger.info(f"RMSE médio ({var_strEstrategia}): {var_floatMedia:.2f}")
            logger.info(f"MELHOR ESTRATÉGIA (regressão, RMSE médio): {var_strMelhorReg}")

        logger.info("=" * 80)


if __name__ == "__main__":
    from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

    Settings.build()
    ComparadorEstrategiasSplit.executar_comparativo()
