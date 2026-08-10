import joblib
from pathlib import Path
from functools import lru_cache
from typing import Any
import logging

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Registry Pattern + Singleton + Lazy Loading para Modelos .joblib.
    Garante que o modelo seja carregado apenas UMA vez para a memória (RAM)
    e reutilizado nas próximas predições, prevenindo gargalos de disco.
    """
    
    @staticmethod
    @lru_cache(maxsize=10)
    def _load_model_from_disk(arg_strCaminhoModelo: str) -> Any:
        """
        Método interno cacheado para carregar o modelo a partir do disco.
        """
        var_pathCaminhoArquivoModelo = Path(arg_strCaminhoModelo)
        if not var_pathCaminhoArquivoModelo.exists():
            raise FileNotFoundError(f"Modelo não encontrado em: {arg_strCaminhoModelo}")
        logger.info(f"I/O DISCO: Carregando modelo para a memória ({var_pathCaminhoArquivoModelo.name})")
        return joblib.load(var_pathCaminhoArquivoModelo)

    @classmethod
    def get_model(cls, arg_strCaminhoModelo: str) -> Any:
        """
        Retorna o modelo carregado. Na 1ª vez executa I/O de disco.
        Nas demais, devolve a referência instantânea da memória (Cache hit).
        """
        try:
            return cls._load_model_from_disk(arg_strCaminhoModelo)
        except Exception as e:
            logger.critical(f"Falha ao recuperar modelo '{arg_strCaminhoModelo}'. Erro: {e}")
            return None
