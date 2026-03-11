from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.local_steam import LocalClient
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.scripts.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.scripts.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorLimpeza import ProcessadorLimpeza
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
        logger.info("Criando a fila de tarefas.")
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
            if len(var_listDadosRawDesatualizados) == 0 and Settings._var_dictSettings["etl_processar_todos_dados"]:
                ProcessadorETL.processar_lote_unificado()

            # Alimentação do banco de dados ITAD para o docker
            if PostgreSQLSteam.buscar_appids_desatualizados_otimizado(arg_strNomeTabela="itad_raw"):
                Previsor.alimentar_banco_dados_ITAD_docker()
                Previsor.alimentar_ITAD_historico_precos()

            # Verificar se o .joblib de limpeza existe e se está atualizado
            if cls._verificar_necessidade_processamento_limpeza():
                ProcessadorLimpeza.processar_completo()
            else:
                logger.info("Pipeline de limpeza já está atualizado - Processamento ignorado")
            
            ProcessadorTreinamento.executar_treinamento()
            cls._var_listTaskQueue = [1]
            logger.info("Fila de tarefas criada com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro ao criar a fila de tarefas: {e}", exc_info=True)
            # Fornecer mais detalhes sobre o erro
            import traceback
            logger.error(f"Traceback completo:\n{traceback.format_exc()}")
            raise Exception(f"Erro ao criar a fila de tarefas: {e}")
        
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
    def _verificar_necessidade_processamento_limpeza(cls) -> bool:
        """
        Verifica se o pipeline de limpeza precisa ser reprocessado.
        
        Critérios:
        1. Pipeline não existe
        2. Pipeline existe mas dados brutos foram atualizados recentemente
        3. Pipeline tem mais de 7 dias
        
        Retorna:
        - bool: True se precisa processar, False caso contrário
        """
        try:
            var_strCaminhoPipeline = os.path.join(
                "prj_TCC_PREVISOR_STEAM/resources/models", 
                "pipeline_escalonamento.joblib"
            )
            
            # Verificar se pipeline existe
            if not os.path.exists(var_strCaminhoPipeline):
                logger.info("Pipeline de limpeza não encontrado - Processamento necessário")
                return True
            
            # Obter data de modificação do pipeline
            var_floatTempoModificacao = os.path.getmtime(var_strCaminhoPipeline)
            var_dateDataPipeline = datetime.fromtimestamp(var_floatTempoModificacao)
            var_intDiasDesdeAtualizacao = (datetime.now() - var_dateDataPipeline).days
            
            logger.info(f"Pipeline de limpeza encontrado - Última atualização: {var_intDiasDesdeAtualizacao} dias atrás")
            
            # Se pipeline tem mais de 7 dias, reprocessar
            var_intIntervaloMaximo = int(os.getenv("LIMPEZA_INTERVALO_DIAS", "7"))
            if var_intDiasDesdeAtualizacao >= var_intIntervaloMaximo:
                logger.info(f"Pipeline desatualizado ({var_intDiasDesdeAtualizacao} >= {var_intIntervaloMaximo} dias) - Reprocessamento necessário")
                return True
            
            # Verificar se há novos dados no banco
            try:
                PostgreSQL.conectar()
                var_strSQL = """
                    SELECT MAX(ultima_atualizacao) 
                    FROM steam_unificado 
                    WHERE ultima_atualizacao >= %s;
                """
                
                with PostgreSQL._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL, (var_dateDataPipeline,))
                    var_tupleResultado = cursor.fetchone()
                    
                    if var_tupleResultado and var_tupleResultado[0]:
                        logger.info(f"Novos dados encontrados desde última limpeza - Reprocessamento necessário")
                        return True
                        
            except Exception as e:
                logger.warning(f"Não foi possível verificar novos dados: {e}")
                # Em caso de erro, processar por segurança
                return True
            finally:
                if PostgreSQL._var_connConnection:
                    PostgreSQL.desconectar()
            
            logger.info("Pipeline de limpeza está atualizado")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar necessidade de processamento de limpeza: {e}")
            # Em caso de erro, processar por segurança
            return True
    
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