from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from datetime import datetime
from time import sleep
import json, logging, asyncio, os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class Previsor:
    """
    Classe responsável por gerenciar módulos gerais do projeto.
    """
       
    @classmethod
    def alimentar_banco_dados_raw_docker(cls):
        """
        Alimenta o banco de dados PostgreSQL (Docker) com os dados coletados da API.
        Versão otimizada que usa o PostgreSQL local em vez do Supabase.
        Suporta divisão de trabalho entre múltiplos PCs usando PC_ID.

        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            PostgreSQL.conectar()
            
            # Define o range de processamento por vez pelo .env
            var_intRange = int(os.getenv("RANGE_PROCESSAMENTO_APPIDS_RAW", 1000))
            
            # Identifica qual PC está executando (1 ou 2)
            var_intPcId = int(os.getenv("PC_ID", "1"))
            var_intTotalPcs = int(os.getenv("TOTAL_PCS", "1"))
            
            if var_intTotalPcs > 1:
                logger.info(f"{'='*60}")
                logger.info(f"MODO MULTI-PC ATIVADO: PC {var_intPcId} de {var_intTotalPcs}")
                logger.info(f"{'='*60}")
            
            # Carregamento de teste de carga
            var_intAmbiente = os.getenv("AMBIENTE", "PRD").upper()

            # Busca apenas AppIDs não processados (LEFT JOIN no banco)
            # Já aplica filtro de divisão de trabalho entre PCs
            logger.info("Consultando AppIDs não processados...")
            var_listAppIDParaProcessar = PostgreSQL.buscar_appids_nao_processados_otimizado(
                arg_intPcId=var_intPcId,
                arg_intTotalPcs=var_intTotalPcs
            )
            
            var_strTexto = f"{10*'='} AppIDs novos para processar {10*'='}"
            logger.info(var_strTexto)
            logger.info(f"AppIDs novos atribuídos ao PC {var_intPcId}: {len(var_listAppIDParaProcessar):,}")
            logger.info(len(var_strTexto)*"=")

            # Busca AppIDs desatualizados e adiciona à lista
            logger.info("Consultando AppIDs desatualizados")
            var_listAppIDDesatualizados = PostgreSQL.buscar_appids_desatualizados_otimizado(
                arg_intPcId=var_intPcId,
                arg_intTotalPcs=var_intTotalPcs
            )
            
            # Adiciona desatualizados (evita duplicatas)
            var_setAppIDParaProcessar = set(var_listAppIDParaProcessar)
            for var_intAppID in var_listAppIDDesatualizados:
                if var_intAppID not in var_setAppIDParaProcessar:
                    var_listAppIDParaProcessar.append(var_intAppID)
                    var_setAppIDParaProcessar.add(var_intAppID)
            
            if var_listAppIDDesatualizados:
                logger.info(f"AppIDs desatualizados adicionados: {len(var_listAppIDDesatualizados):,}")
            
            var_intTamanhoTotalFila = len(var_listAppIDParaProcessar)
            logger.info(f"Total final de AppIDs a processar (PC {var_intPcId}): {var_intTamanhoTotalFila:,}")

            if var_intTamanhoTotalFila == 0:
                logger.info("Nenhum AppID para processar! Todos os dados estão atualizados.")
                return

            # Itera sobre os aplicativos em lotes
            for i in range(0, var_intTamanhoTotalFila, var_intRange):
                logger.info(f"Processando aplicativos de {i + 1} a {min(i + var_intRange, var_intTamanhoTotalFila)} de {var_intTamanhoTotalFila}")
                logger.info(f"Progresso: {(i/var_intTamanhoTotalFila)*100:.1f}%")
                logger.info(f"Tempo estimado restante: {((var_intTamanhoTotalFila - i) / var_intRange) * 2} minutos")
                logger.info(f"----------------------------------------")
                
                # Carrega os aplicativos atuais
                if var_intAmbiente == "HML":
                    var_listAppIDAtual = var_listAppIDParaProcessar[i:i+int(os.getenv("BATCH_TESTE", 20))]
                else:
                    var_listAppIDAtual = var_listAppIDParaProcessar[i:i+var_intRange]
                
                logger.info(f"Número de IDs a processar neste lote: {len(var_listAppIDAtual)}")
                
                # Busca detalhes dos jogos
                asyncio.run(SteamClient.fetch_details_bulk_batched(arg_seqAppids=var_listAppIDAtual))
                
                # Busca reviews dos jogos
                asyncio.run(SteamClient.fetch_reviews_summary_batched(arg_seqAppids=var_listAppIDAtual))
            
            logger.info("Processamento concluído com sucesso!")
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados PostgreSQL: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados PostgreSQL: {e}")
        finally:
            PostgreSQL.desconectar()
            
    @classmethod
    def alimentar_banco_dados_ITAD_docker(cls):
        """
        Alimenta o banco de dados PostgreSQL (Docker) com dados do ITAD.
        Versão otimizada que usa o PostgreSQL local em vez do Supabase.
        
        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            PostgreSQL.conectar()
            var_listDados = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="steam_raw")

            # Define o range de processamento por vez pelo .env
            var_intRange = int(os.getenv("RANGE_PROCESSAMENTO_ITAD_RAW", 5000))
            
            # Identifica qual PC está executando
            var_intPcId = int(os.getenv("PC_ID", "1"))
            var_intTotalPcs = int(os.getenv("TOTAL_PCS", "1"))
            
            if var_intTotalPcs > 1:
                logger.info(f"{'='*60}")
                logger.info(f"MODO MULTI-PC ATIVADO (ITAD): PC {var_intPcId} de {var_intTotalPcs}")
                logger.info(f"{'='*60}")
            
            # Carregamento de teste de carga
            var_intAmbiente = os.getenv("AMBIENTE", "PRD").upper()

            # Busca AppIDs do steam_bd que ainda não têm dados no ITAD
            logger.info("Consultando AppIDs sem dados ITAD...")
            var_listAppIDParaProcessar = PostgreSQL.buscar_appids_sem_itad()
            
            var_strTexto = f"{10*'='} AppIDs para processar ITAD {10*'='}"
            logger.info(var_strTexto)
            logger.info(f"AppIDs novos atribuídos ao PC {var_intPcId}: {len(var_listAppIDParaProcessar):,}")
            logger.info(len(var_strTexto)*"=")

            # Busca AppIDs ITAD desatualizados (>90 dias)
            logger.info("Consultando AppIDs ITAD desatualizados")
            var_listAppIDDesatualizados = PostgreSQL.buscar_appids_itad_desatualizados(
                arg_intPcId=var_intPcId,
                arg_intTotalPcs=var_intTotalPcs
            )
            
            # Adiciona desatualizados (evita duplicatas)
            var_setAppIDParaProcessar = set(var_listAppIDParaProcessar)
            for var_intAppID in var_listAppIDDesatualizados:
                if var_intAppID not in var_setAppIDParaProcessar:
                    var_listAppIDParaProcessar.append(var_intAppID)
                    var_setAppIDParaProcessar.add(var_intAppID)
            
            if var_listAppIDDesatualizados:
                logger.info(f"AppIDs ITAD desatualizados adicionados: {len(var_listAppIDDesatualizados):,}")
            
            var_intTamanhoTotalFila = len(var_listAppIDParaProcessar)
            logger.info(f"Total final de AppIDs a processar ITAD (PC {var_intPcId}): {var_intTamanhoTotalFila:,}")

            if var_intTamanhoTotalFila == 0:
                logger.info("Nenhum AppID para processar no ITAD! Todos os dados estão atualizados.")
                return

            # Itera sobre os aplicativos em lotes
            for i in range(0, var_intTamanhoTotalFila, var_intRange):
                logger.info(f"Processando aplicativos ITAD de {i + 1} a {min(i + var_intRange, var_intTamanhoTotalFila)} de {var_intTamanhoTotalFila}")
                logger.info(f"Progresso: {(i/var_intTamanhoTotalFila)*100:.1f}%")
                logger.info(f"----------------------------------------")
                
                # Carrega os aplicativos atuais
                if var_intAmbiente == "HML":
                    var_listAppIDAtual = var_listAppIDParaProcessar[i:i+int(os.getenv("BATCH_TESTE", 20))]
                else:
                    var_listAppIDAtual = var_listAppIDParaProcessar[i:i+var_intRange]
                
                logger.info(f"Número de IDs ITAD a processar neste lote: {len(var_listAppIDAtual)}")
                
                # Busca dados ITAD para os AppIDs
                asyncio.run(SteamClient.lookup_itad_ids_batched(arg_seqAppids=var_listAppIDAtual))
                
                var_listITADID = list(PostgreSQL.buscar_itad_id_por_appid(arg_listAppids=var_listAppIDAtual))

                # Busca histórico de preços ITAD para os AppIDs
                asyncio.run(SteamClient.fetch_price_history_bulk_batched(arg_seqItadPlain=var_listITADID))
                # Pausa entre lotes
                if i + var_intRange < var_intTamanhoTotalFila:
                    logger.info("Aguardando 2 segundos antes do próximo lote...")
                    sleep(2)
            
            logger.info("Processamento ITAD concluído com sucesso!")
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados ITAD (PostgreSQL): {e}")
            raise Exception(f"Erro ao alimentar o banco de dados ITAD (PostgreSQL): {e}")
        finally:
            PostgreSQL.desconectar()

    @classmethod
    def alimentar_ITAD_historico_precos(cls):
        """
        Alimenta o histórico de preços do ITAD para jogos desatualizados ou sem histórico.
        Processa apenas registros que:
        - Estão desatualizados (>90 dias) OU
        - Não possuem histórico de preços

        Retorna:
        - None
        """
        try:
            PostgreSQL.conectar()
            
            # Busca todos os dados ITAD
            logger.info("Consultando registros ITAD...")
            var_listITAD = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="itad_raw")
            
            # Filtra registros que precisam de atualização
            var_listITADID = []
            var_intSemHistorico = 0
            var_intDesatualizados = 0
            
            for var_dictItem in var_listITAD:
                # Verifica se tem id_itad válido
                if not ('id_itad' in var_dictItem and var_dictItem['id_itad']):
                    continue
                
                var_strIdItad = var_dictItem['id_itad']
                var_boolHistoricoVazio = not var_dictItem.get('historico_preco') or var_dictItem.get('historico_preco') in ['{}', '[]', None]
                var_boolDesatualizado = False
                
                # Verifica se está desatualizado (>90 dias)
                if var_dictItem.get('ultima_atualizacao'):
                    try:
                        var_dtUltimaAtualizacao = datetime.fromisoformat(str(var_dictItem['ultima_atualizacao']))
                        var_intDiasDesdeAtualizacao = (datetime.now() - var_dtUltimaAtualizacao).days
                        var_boolDesatualizado = var_intDiasDesdeAtualizacao > 90
                    except:
                        var_boolDesatualizado = True
                else:
                    var_boolDesatualizado = True
                
                # Adiciona à lista se histórico vazio OU desatualizado
                if var_boolHistoricoVazio or var_boolDesatualizado:
                    var_listITADID.append(var_strIdItad)
                    if var_boolHistoricoVazio:
                        var_intSemHistorico += 1
                    if var_boolDesatualizado:
                        var_intDesatualizados += 1
            
            logger.info(f"{'='*60}")
            logger.info(f"Registros que precisam de atualização:")
            logger.info(f"  - Sem histórico: {var_intSemHistorico:,}")
            logger.info(f"  - Desatualizados (>90 dias): {var_intDesatualizados:,}")
            logger.info(f"  - Total a processar: {len(var_listITADID):,}")
            logger.info(f"{'='*60}")
            
            if len(var_listITADID) == 0:
                logger.info("Nenhum registro ITAD precisa de atualização de histórico!")
                return

            logger.info(f"Iniciando alimentação do histórico de preços ITAD para {len(var_listITADID):,} jogos.")
            
            # Busca histórico de preços ITAD para os IDs selecionados
            asyncio.run(SteamClient.fetch_price_history_bulk_batched(arg_seqItadPlain=var_listITADID))
            
            logger.info("Alimentação do histórico de preços ITAD concluída com sucesso!")
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o histórico de preços ITAD: {e}")
            raise Exception(f"Erro ao alimentar o histórico de preços ITAD: {e}")
        finally:
            PostgreSQL.desconectar()