"""
Treino avulso, em processo separado da coleta.

Le o snapshot atual (jogos pagos com historico_preco) sem esperar
o pipeline de alimentacao terminar.
"""
import logging
from pathlib import Path

from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.treinamento.ProcessadorTreinamento import ProcessadorTreinamento

if __name__ == "__main__":
    Settings.build()

    var_pathLog = Path(__file__).resolve().parent / "resources" / "logs" / "treino.log"
    var_pathLog.parent.mkdir(parents=True, exist_ok=True)
    var_objHandler = logging.FileHandler(var_pathLog, encoding="utf-8")
    var_objHandler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logging.getLogger().addHandler(var_objHandler)

    logger = logging.getLogger("treino.snapshot")
    logger.info("=" * 80)
    logger.info("TREINO SNAPSHOT — processo separado da coleta ITAD/Steam")
    logger.info("Fonte: steam_unificado + steam_itad_mapping + itad_raw (historico_preco NOT NULL)")
    logger.info("=" * 80)

    ProcessadorTreinamento.executar_treinamento()
