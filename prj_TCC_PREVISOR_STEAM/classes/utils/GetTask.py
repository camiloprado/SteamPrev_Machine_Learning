from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.local_steam import LocalClient
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_bdgeral import PostgreSQLBDGeral
from prj_TCC_PREVISOR_STEAM.classes.data.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorLimpeza import ProcessadorLimpeza
from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinamento import TreinarModelo
from prj_TCC_PREVISOR_STEAM.classes.treinamento.ProcessadorTreinamento import ProcessadorTreinamento

from datetime import datetime
from time import sleep
import asyncio, json, os, logging

logger = logging.getLogger(__name__)


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
            # Procura a lista genérica de apps na Steam
            try:
                var_listDados = LocalClient.find_app_list()
                PostgreSQLSteam.inserir_dadosSteamGenerico(arg_listDadosGerais=var_listDados)
            except Exception as e:
                logger.warning(f"Erro ao buscar lista de apps da Steam: {e}")
                logger.warning("Tentando carregar lista de apps da Steam do arquivo local...")
                # Se não encontrar, carrega do arquivo local
                var_listDados = LocalClient.load_app_list()

            # Alimentação do banco de dados raw para o docker
            var_listDadosRawDesatualizados = PostgreSQLSteam.buscar_appids_desatualizados_otimizado()
            if var_listDadosRawDesatualizados:
                Previsor.alimentar_banco_dados_raw_docker()
                ProcessadorETL.processar_lote_unificado(var_listDadosRawDesatualizados)
                Previsor.alimentar_tabela_Geral(arg_listAppids=var_listDadosRawDesatualizados, var_boolTotal=False)
            elif len(var_listDadosRawDesatualizados) == 0 and Settings._var_dictSettings["etl_processar_todos_dados"]:
                ProcessadorETL.processar_lote_unificado()
                Previsor.alimentar_tabela_Geral(var_boolTotal=True)
            else:
                logger.info("Nenhum dado desatualizado encontrado para processamento ETL.")
                
            # Alimentação do banco de dados ITAD para o docker
            if PostgreSQLSteam.buscar_appids_desatualizados_otimizado(arg_strNomeTabela="itad_raw"):
                Previsor.alimentar_banco_dados_ITAD_docker()
                Previsor.alimentar_ITAD_historico_precos()

            try:
                ProcessadorTreinamento.executar_treinamento()
            except Exception as e:
                # Treinamento falhou, mas não deve interromper o fluxo principal de coleta/ETL.
                logger.warning(f"Treinamento ML não executado nesta rodada: {e}")
            cls._var_listTaskQueue = [1]
            logger.info("Fila de tarefas criada com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro ao criar a fila de tarefas: {e}", exc_info=True)
            # Fornecer mais detalhes sobre o erro
            import traceback
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

        Retorna:
        - None
        """
        if arg_boolAbandonar:
            if len(cls._var_listTaskQueue) > 0:
                for var_intIndex in range(len(cls._var_listTaskQueue)):
                    cls._var_listTaskQueue.pop(var_intIndex)

    @classmethod
    def load_task_queue(cls) -> dict:
        """
        Carrega a fila de tarefas.

        Retorna:
        - None
        """
        return cls._var_listTaskQueue