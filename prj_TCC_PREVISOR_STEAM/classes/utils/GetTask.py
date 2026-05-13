from prj_TCC_PREVISOR_STEAM.classes.api.local_steam import LocalClient
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam

import logging
import traceback

logger = logging.getLogger("task")


class GetTask:
    """
    Classe utilitária para gerenciar as tarefas.
    """
    _var_listTaskQueue = []

    @classmethod
    def criar_fila(cls):
        """
        Cria a fila de tarefas.

        Retorna:
        """
        logger.info("="*60)
        logger.info("CRIANDO FILA DE TAREFAS")
        logger.info("="*60)

        try:
            # Atualiza o índice de apps a partir da Steam/SteamSpy e persiste em steam_generico.
            # Este passo ocorre uma única vez por sessão, na inicialização.
            try:
                var_listDados = LocalClient.find_app_list()
                PostgreSQLSteam.inserir_dadosSteamGenerico(arg_listDadosGerais=var_listDados)
            except Exception as e:
                logger.warning(f"Erro ao buscar lista de apps da Steam: {e}")
                logger.warning("Tentando carregar lista de apps da Steam do arquivo local...")
                # Fallback: carrega do arquivo local sem atualizar o banco
                LocalClient.load_app_list()

            # Insere 1 item genérico na fila. O Loop o consumirá e delegará
            # a execução do pipeline completo para Process.execute().
            cls._var_listTaskQueue = [1]
            logger.info("Fila de tarefas criada com sucesso. 1 tarefa agendada.")

        except Exception as e:
            logger.error(f"Erro ao criar a fila de tarefas: {e}", exc_info=True)
            logger.error(f"Traceback completo:\n{traceback.format_exc()}")
            raise Exception(f"Erro ao criar a fila de tarefas: {e}")
        finally:
            logger.info("="*60)
            logger.info("FIM DA CRIAÇÃO DA FILA DE TAREFAS")
            logger.info("="*60)

    @classmethod
    def abandona_fila(cls, arg_boolAbandonar: bool = True):
        """
        Abandona a fila de tarefas.

        Parâmetros:
        - arg_boolAbandonar (bool): Se True, esvazia a fila.

        Retorna:
        - None
        """
        if arg_boolAbandonar:
            cls._var_listTaskQueue.clear()

    @classmethod
    def load_task_queue(cls) -> list:
        """
        Retorna a fila de tarefas atual.

        Retorna:
        - list: Fila de tarefas.
        """
        return cls._var_listTaskQueue