from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_itad import PostgreSQLITAD
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_bdgeral import PostgreSQLBDGeral
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_checkpoint import PostgreSQLCheckpoint

import logging

logger = logging.getLogger("framework.close")

class Close:
    """
    Classe para gerenciar o fechamento da aplicação.
    """

    # O connection pool agora é sempre único e compartilhado na classe base
    # PostgreSQL (ver postgre_generico.py:_init_pool). O laço abaixo ainda
    # itera todas as subclasses por segurança/histórico, mas na prática só
    # PostgreSQL.__dict__ terá um pool próprio para fechar.
    _var_listRepositorios = [
        PostgreSQL,
        PostgreSQLSteam,
        PostgreSQLITAD,
        PostgreSQLBDGeral,
        PostgreSQLCheckpoint,
    ]

    @classmethod
    def execute(cls):
        """
        Fecha as aplicações de forma segura.

        Retorna:
        - None
        """
        for var_intTentativa in range(Settings._var_dictSettings["max_tentativas"]):
            try:
                # Devolve a conexão em uso (se houver) e encerra definitivamente
                # o connection pool de cada repositório PostgreSQL, liberando os
                # recursos do banco de dados antes do encerramento da aplicação.
                for var_classRepositorio in cls._var_listRepositorios:
                    var_classRepositorio.desconectar()

                    var_poolAtual = var_classRepositorio.__dict__.get("_var_poolConnectionPool")
                    if var_poolAtual is not None:
                        var_poolAtual.closeall()
                        var_classRepositorio._var_poolConnectionPool = None
                        logger.info(f"Connection pool de {var_classRepositorio.__name__} fechado com sucesso.")
            except Exception as e:
                if var_intTentativa == Settings._var_dictSettings["max_tentativas"] - 1:
                    raise e
                else: continue
            else:
                break