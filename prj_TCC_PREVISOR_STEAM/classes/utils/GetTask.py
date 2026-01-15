from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinamento import TreinarModelo

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
        logger.info("Criando a fila de tarefas.")
        try:
            try:
                var_listDados = SteamClient.find_app_list()
                PostgreSQL.inserir_dadosSteamGenerico(arg_listDadosGerais=var_listDados)
            except:
                var_listDados = SteamClient.load_app_list()

            # Alimentação do banco de dados raw para o docker
            if PostgreSQL.buscar_appids_desatualizados_otimizado():
                Previsor.alimentar_banco_dados_raw_docker()

            # ProcessadorETL.processar_lote_unificado()

            # Alimentação do banco de dados ITAD para o docker
            if PostgreSQL.buscar_appids_desatualizados_otimizado(arg_strNomeTabela="itad_raw"):
                Previsor.alimentar_banco_dados_ITAD_docker()
                Previsor.alimentar_ITAD_historico_precos()

            # Verificar e executar treinamento ML se necessário (a cada 90 dias)
            # cls._verificar_executar_treinamento_ml()

            cls._var_listTaskQueue = [1]
            
        except Exception as e:
            logger.error(f"Erro ao criar a fila de tarefas: {e}")
            raise Exception(f"Erro ao criar a fila de tarefas: {e}")
        logger.info("Fila de tarefas criada com sucesso.")
        
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
    
    @classmethod
    def _verificar_executar_treinamento_ml(cls):
        """
        Verifica se há dados suficientes nos últimos 90 dias e se é necessário
        executar novo treinamento ML. Executa automaticamente se:
        1. Nunca houve treinamento, OU
        2. Último treinamento foi há mais de 90 dias
        
        Retorna:
        - None
        """
        try:
            # Verifica se treinamento ML está habilitado no .env
            var_boolMLHabilitado = os.getenv("ML_TREINAMENTO_AUTO", "False").upper() == "TRUE"
            
            if not var_boolMLHabilitado:
                logger.info("Treinamento ML automático desabilitado (ML_TREINAMENTO_AUTO=False)")
                return
            
            logger.info("="*60)
            logger.info("VERIFICANDO NECESSIDADE DE TREINAMENTO ML")
            logger.info("="*60)
            
            PostgreSQL.conectar()
            
            # Verifica quantidade de dados nos últimos 90 dias
            var_strSQL = """
                SELECT COUNT(*) 
                FROM steam_unificado 
                WHERE ultima_atualizacao >= NOW() - INTERVAL '90 days';
            """
            
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_intRegistros90Dias = cursor.fetchone()[0]
            
            logger.info(f"Registros disponíveis (últimos 90 dias): {var_intRegistros90Dias:,}")
            
            if var_intRegistros90Dias < 1000:
                logger.warning(f"Dados insuficientes para treinamento ML ({var_intRegistros90Dias} < 1000)")
                logger.info("Aguardando mais coleta de dados antes de treinar modelo.")
                return
            
            # Verificar último treinamento
            var_dictUltimo = TreinarModelo.verificar_ultimo_treinamento()
            
            var_boolPrecisaTreinar = False
            
            if var_dictUltimo is None:
                logger.info("Nenhum treinamento anterior encontrado - EXECUTANDO PRIMEIRO TREINAMENTO")
                var_boolPrecisaTreinar = True
            else:
                var_intDiasDesdeUltimo = int(var_dictUltimo['dias_desde_ultimo'])
                var_intIntervaloMinimo = int(os.getenv("ML_INTERVALO_DIAS", "90"))
                
                logger.info(f"Último treinamento: {var_intDiasDesdeUltimo} dias atrás")
                logger.info(f"  Algoritmo: {var_dictUltimo['algoritmo']}")
                logger.info(f"  Acurácia: {var_dictUltimo['acuracia']:.4f}")
                logger.info(f"  Intervalo mínimo configurado: {var_intIntervaloMinimo} dias")
                
                if var_intDiasDesdeUltimo >= var_intIntervaloMinimo:
                    logger.info(f"Intervalo atingido ({var_intDiasDesdeUltimo} >= {var_intIntervaloMinimo} dias) - EXECUTANDO NOVO TREINAMENTO")
                    var_boolPrecisaTreinar = True
                else:
                    logger.info(f"Treinamento atualizado (aguardar mais {var_intIntervaloMinimo - var_intDiasDesdeUltimo} dias)")
            
            if var_boolPrecisaTreinar:
                logger.info("="*60)
                logger.info("INICIANDO TREINAMENTO ML AUTOMÁTICO")
                logger.info("="*60)
                
                # Determinar algoritmo a usar
                var_strAlgoritmo = os.getenv("ML_ALGORITMO_PADRAO", "xgboost")
                logger.info(f"Algoritmo configurado: {var_strAlgoritmo}")
                
                # Executar treinamento incremental
                var_dictResultados = TreinarModelo.executar_treinamento_incremental_90dias(
                    arg_strAlgoritmo=var_strAlgoritmo
                )
                
                if var_dictResultados:
                    var_strMelhorModelo = var_dictResultados['melhor_modelo']
                    var_dictMetricas = var_dictResultados['modelos'][var_strMelhorModelo]['metricas']
                    
                    logger.info("="*60)
                    logger.info("✅ TREINAMENTO ML CONCLUÍDO COM SUCESSO!")
                    logger.info("="*60)
                    logger.info(f"Total de jogos: {var_dictResultados['total_amostras']:,}")
                    logger.info(f"Melhor modelo: {var_strMelhorModelo}")
                    logger.info(f"Acurácia: {var_dictMetricas['accuracy']*100:.2f}%")
                    logger.info(f"F1-Score: {var_dictMetricas['f1_score']:.4f}")
                    logger.info("="*60)
                else:
                    logger.error("❌ Falha no treinamento ML - verifique os logs detalhados")
            
        except Exception as e:
            logger.error(f"Erro ao verificar/executar treinamento ML: {e}", exc_info=True)
            logger.warning("Continuando execução normal apesar do erro no treinamento ML")
        finally:
            if PostgreSQL._var_connConnection:
                PostgreSQL.desconectar()