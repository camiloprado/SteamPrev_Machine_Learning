from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.api.itad_api import ITADClient
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_itad import PostgreSQLITAD
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_checkpoint import PostgreSQLCheckpoint
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_bdgeral import PostgreSQLBDGeral

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
            var_listAppIDParaProcessar = PostgreSQLSteam.buscar_appids_nao_processados_otimizado(
                arg_intPcId=var_intPcId,
                arg_intTotalPcs=var_intTotalPcs
            )
            
            var_strTexto = f"{10*'='} AppIDs novos para processar {10*'='}"
            logger.info(var_strTexto)
            logger.info(f"AppIDs novos atribuídos ao PC {var_intPcId}: {len(var_listAppIDParaProcessar):,}")
            logger.info(len(var_strTexto)*"=")

            # Busca AppIDs desatualizados e adiciona à lista
            logger.info("Consultando AppIDs desatualizados")
            var_listAppIDDesatualizados = PostgreSQLSteam.buscar_appids_desatualizados_otimizado(
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
            
            # Deduplicação final - converte set de volta para lista ordenada
            var_listAppIDParaProcessar = sorted(list(var_setAppIDParaProcessar))
            
            var_intTamanhoTotalFila = len(var_listAppIDParaProcessar)
            logger.info(f"Total final de AppIDs a processar (PC {var_intPcId}): {var_intTamanhoTotalFila:,}")

            if var_intTamanhoTotalFila == 0:
                logger.info("Nenhum AppID para processar! Todos os dados estão atualizados.")
                return

            # Recupera checkpoint se houver
            var_intInicioCheckpoint = PostgreSQLCheckpoint.recuperar_checkpoint(var_intPcId, "STEAM")
            logger.info(f"Iniciando do índice: {var_intInicioCheckpoint:,}")

            # Itera sobre os aplicativos em lotes
            for i in range(var_intInicioCheckpoint, var_intTamanhoTotalFila, var_intRange):
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
                
                # Salva checkpoint após batch bem-sucedido
                PostgreSQLCheckpoint.salvar_checkpoint(var_intPcId, i + var_intRange, "STEAM")
                
                # Pausa entre lotes
                if i + var_intRange < var_intTamanhoTotalFila:
                    logger.info("Aguardando 2 segundos antes do próximo lote...")
                    sleep(2)
            
            # Limpa checkpoint após conclusão total
            PostgreSQLCheckpoint.limpar_checkpoint(var_intPcId, "STEAM")
            logger.info("Processamento Steam completo! Checkpoint limpo.")
            logger.info("Processamento concluído com sucesso!")
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados PostgreSQL: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados PostgreSQL: {e}")
            
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
            var_listAppIDParaProcessar = PostgreSQLITAD.buscar_appids_sem_itad()
            
            var_strTexto = f"{10*'='} AppIDs para processar ITAD {10*'='}"
            logger.info(var_strTexto)
            logger.info(f"AppIDs novos atribuídos ao PC {var_intPcId}: {len(var_listAppIDParaProcessar):,}")
            logger.info(len(var_strTexto)*"=")

            # Busca AppIDs ITAD desatualizados (>90 dias)
            logger.info("Consultando AppIDs ITAD desatualizados")
            var_listAppIDDesatualizados = PostgreSQLITAD.buscar_appids_itad_desatualizados(
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
            
            # Deduplicação final - converte set de volta para lista ordenada
            var_listAppIDParaProcessar = sorted(list(var_setAppIDParaProcessar))
            
            var_intTamanhoTotalFila = len(var_listAppIDParaProcessar)
            logger.info(f"Total final de AppIDs a processar ITAD (PC {var_intPcId}): {var_intTamanhoTotalFila:,}")

            if var_intTamanhoTotalFila == 0:
                logger.info("Nenhum AppID para processar no ITAD! Todos os dados estão atualizados.")
                return

            # Recupera checkpoint se houver
            var_intInicioCheckpoint = PostgreSQLCheckpoint.recuperar_checkpoint(var_intPcId, "ITAD")
            logger.info(f"Iniciando ITAD do índice: {var_intInicioCheckpoint:,}")

            # Itera sobre os aplicativos em lotes
            for i in range(var_intInicioCheckpoint, var_intTamanhoTotalFila, var_intRange):
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
                asyncio.run(ITADClient.lookup_itad_ids_batched(arg_seqAppids=var_listAppIDAtual))
                
                # Busca os IDs ITAD correspondentes aos AppIDs processados
                var_listITADID = list(PostgreSQLITAD.buscar_itad_id_por_appid(arg_listAppids=var_listAppIDAtual))

                # Busca histórico de preços ITAD para os AppIDs
                asyncio.run(ITADClient.fetch_price_history_bulk_batched(arg_seqItadPlain=var_listITADID))
                
                # Salva checkpoint após batch ITAD bem-sucedido
                PostgreSQLCheckpoint.salvar_checkpoint(var_intPcId, i + var_intRange, "ITAD")
                
                # Pausa entre lotes
                if i + var_intRange < var_intTamanhoTotalFila:
                    logger.info("Aguardando 2 segundos antes do próximo lote...")
                    sleep(2)
            
            # Limpa checkpoint após conclusão total ITAD
            PostgreSQLCheckpoint.limpar_checkpoint(var_intPcId, "ITAD")
            logger.info("Processamento ITAD completo! Checkpoint limpo.")
            
            logger.info("Processamento ITAD concluído com sucesso!")
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados ITAD (PostgreSQL): {e}")
            raise Exception(f"Erro ao alimentar o banco de dados ITAD (PostgreSQL): {e}")
        
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
            # Busca todos os dados ITAD
            logger.info("Consultando registros ITAD...")
            var_listITADID = PostgreSQLITAD.buscar_itad_historico_preco_desatualizado()

            if len(var_listITADID) == 0:
                logger.info("Nenhum registro ITAD precisa de atualização de histórico!")
                return

            logger.info(f"Iniciando alimentação do histórico de preços ITAD para {len(var_listITADID):,} jogos.")
            
            # Busca histórico de preços ITAD para os IDs selecionados
            asyncio.run(ITADClient.fetch_price_history_bulk_batched(arg_seqItadPlain=var_listITADID))
            
            logger.info("Alimentação do histórico de preços ITAD concluída com sucesso!")
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o histórico de preços ITAD: {e}")
            raise Exception(f"Erro ao alimentar o histórico de preços ITAD: {e}")
        
    @classmethod
    def alimentar_tabela_Geral(cls, var_boolTotal: bool = True, arg_listAppids: list = None) -> None:
        """
        Alimenta a tabela steam_geral com os dados mais recentes.

        Parâmetros:
        - var_boolTotal (bool): Se True, força a alimentação completa da tabela. Caso contrário, pode aplicar filtros para alimentar apenas parte dos dados.
        - arg_listAppids (list): Lista de AppIDs para filtrar os dados.

        Retorna:
        - None
        """
        try:
            logger.info("Iniciando alimentação da tabela steam_geral.")
            if var_boolTotal:
                logger.info("Alimentação completa selecionada. Buscando todos os dados para alimentar a tabela steam_geral.")
                var_listDados = PostgreSQLBDGeral.buscar_dados_Geral()
            else:
                var_listDados = PostgreSQLBDGeral.buscar_dados_Geral_por_appid(arg_listAppIDs=arg_listAppids)
            if var_listDados:
                PostgreSQLBDGeral.inserir_dados_Geral_Bulk(var_listDados)
                logger.info(f"Alimentação da tabela steam_geral concluída com sucesso. Total de registros processados: {len(var_listDados)}")
            else:
                logger.warning("Nenhum dado encontrado para alimentar a tabela steam_geral.")

        except Exception as err:
            logger.error(f"Erro ao alimentar a tabela steam_geral: {err}")
            raise Exception(f"Erro ao alimentar a tabela steam_geral: {err}")
        