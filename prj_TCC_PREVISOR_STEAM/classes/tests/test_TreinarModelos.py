import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH para permitir imports do projeto
# O caminho atual é d:/Projeto_TCC_CC/prj_TCC_PREVISOR_STEAM/test_TreinarModelos.py
sys.path.append(str(Path(__file__).resolve().parents[1]))

from prj_TCC_PREVISOR_STEAM.classes.treinamento.ProcessadorTreinamento import ProcessadorTreinamento

def testar_treinamento():
    """
    Script de teste para inicializar e executar o treinamento de modelos.
    """
    # Configuração básica de log para exibir no console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("teste.treinamento")
    
    logger.info("Iniciando o script de teste do treinamento de modelos...")
    
    try:
        # Chama a orquestração do treinamento
        # Isso vai buscar os dados no DB, normalizar e treinar todos os modelos.
        ProcessadorTreinamento.executar_treinamento()
        logger.info("Script de teste de treinamento concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro durante o teste de treinamento: {e}", exc_info=True)

if __name__ == "__main__":
    testar_treinamento()
