import sys
import logging
from pathlib import Path

import psycopg2
import pytest

# Adiciona o diretório raiz ao PYTHONPATH para permitir imports do projeto
# O caminho atual é d:/Projeto_TCC_CC/prj_TCC_PREVISOR_STEAM/test_TreinarModelos.py
sys.path.append(str(Path(__file__).resolve().parents[1]))

from prj_TCC_PREVISOR_STEAM.classes.treinamento.ProcessadorTreinamento import ProcessadorTreinamento


def _eh_erro_de_conexao_com_banco(arg_excException: BaseException) -> bool:
    """
    Verifica, subindo a cadeia de causas/contexto da exceção, se ela se origina
    de uma falha de conexão com o banco de dados (psycopg2.OperationalError).

    Necessário porque `PostgreSQL.conectar()`/`_init_pool()` (postgre_generico.py)
    capturam o psycopg2.OperationalError original e o relançam envolto em uma
    Exception genérica (ex.: "Erro ao obter conexão do pool: ..."). Como o
    `raise Exception(...)` é feito dentro do bloco except sem `from None`, o
    Python preserva o erro original em `__context__`, o que permite localizá-lo.

    Parâmetros:
    - arg_excException (BaseException): Exceção capturada no teste.

    Retorna:
    - bool: True se algum erro na cadeia for um psycopg2.OperationalError.
    """
    var_excAtual = arg_excException
    var_setVisitados = set()
    while var_excAtual is not None and id(var_excAtual) not in var_setVisitados:
        var_setVisitados.add(id(var_excAtual))
        if isinstance(var_excAtual, psycopg2.OperationalError):
            return True
        var_excAtual = var_excAtual.__cause__ or var_excAtual.__context__
    return False


def testar_treinamento():
    """
    Script de teste para inicializar e executar o treinamento de modelos.

    - Se o banco de dados estiver indisponível, o teste é pulado (skip),
      já que essa é uma condição de ambiente e não uma falha real do código.
    - Qualquer outra exceção deve propagar, para que o teste falhe de fato
      quando `executar_treinamento()` levantar um erro real.
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
        if _eh_erro_de_conexao_com_banco(e):
            logger.warning(f"Banco de dados indisponível, pulando teste: {e}")
            pytest.skip(f"Banco de dados indisponível: {e}")
        # Qualquer outro erro é uma falha real do treinamento: propaga.
        raise

if __name__ == "__main__":
    testar_treinamento()
