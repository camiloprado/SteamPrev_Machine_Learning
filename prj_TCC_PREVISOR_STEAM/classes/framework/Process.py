from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.data.previsor import Previsor
from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorETL import ProcessadorETL
from prj_TCC_PREVISOR_STEAM.classes.treinamento.ProcessadorTreinamento import ProcessadorTreinamento

import logging
import psycopg2
from aiohttp.client_exceptions import ClientError

logger = logging.getLogger("framework.process")


class Process:
    """
    Classe para gerenciar o processamento das tarefas.

    Executa o pipeline completo de coleta, ETL, integração ITAD e treinamento ML
    a cada iteração do loop principal.
    """

    @classmethod
    def execute(cls):
        """
        Executa o pipeline completo de dados e ML para uma iteração do loop.

        Etapas:
        1. Coleta de detalhes e reviews da Steam API (AppIDs desatualizados)
        2. Processamento ETL (steam_raw → steam_unificado)
        3. Lookup ITAD (mapeamento Steam ↔ ITAD)
        4. Histórico de preços ITAD
        5. Treinamento dos modelos de ML

        Retorna:
        - None
        """
        logger.info("="*60)
        logger.info("PROCESSANDO TAREFA — INICIANDO PIPELINE")
        logger.info("="*60)

        # ── Etapa 1: Coleta Steam (detalhes + reviews) ──────────────────────
        try:
            var_listDesatualizados = PostgreSQLSteam.buscar_appids_desatualizados_otimizado()
            if var_listDesatualizados:
                logger.info(f"Etapa 1/5 — Coleta Steam: {len(var_listDesatualizados):,} AppIDs desatualizados")
                Previsor.alimentar_banco_dados_raw_docker()
            else:
                logger.info("Etapa 1/5 — Coleta Steam: nenhum AppID desatualizado. Pulando.")
        except ClientError as e_http:
            # Graceful Degradation: Steam API instável, segue com ETL dos dados já em cache
            logger.warning(f" Etapa 1 parcialmente interrompida. API da Steam instável: {e_http}. Seguindo para o ETL.")
        except psycopg2.Error as e_db:
            logger.critical(f" Banco de Dados offline ou falha crítica. Erro: {e_db}")
            return  # Aborta ciclo atual se o banco cair
        except Exception as e:
            logger.error(f"Etapa 1/5 — Coleta Steam falhou: {e}", exc_info=True)

        # ── Etapa 2: ETL (steam_raw → steam_unificado) ──────────────────────
        try:
            var_listDesatualizados = PostgreSQLSteam.buscar_appids_desatualizados_otimizado()
            if var_listDesatualizados:
                logger.info(f"Etapa 2/5 — ETL: processando {len(var_listDesatualizados):,} registros")
                ProcessadorETL.processar_lote_unificado(var_listDesatualizados)
            elif Settings._var_dictSettings.get("etl_processar_todos_dados"):
                logger.info("Etapa 2/5 — ETL: processando todos os dados (flag etl_processar_todos_dados)")
                ProcessadorETL.processar_lote_unificado()
            else:
                logger.info("Etapa 2/5 — ETL: nenhum dado pendente. Pulando.")
        except Exception as e:
            logger.error(f"Etapa 2/5 — ETL falhou: {e}", exc_info=True)

        # ── Etapa 3 e 4: Integração ITAD ────────────────────────────────────
        try:
            if PostgreSQLSteam.buscar_appids_desatualizados_otimizado(arg_strNomeTabela="itad_raw"):
                logger.info("Etapa 3/5 — ITAD lookup: atualizando mapeamentos Steam ↔ ITAD")
                Previsor.alimentar_banco_dados_ITAD_docker()
                logger.info("Etapa 4/5 — ITAD histórico: coletando histórico de preços")
                Previsor.alimentar_ITAD_historico_precos()
            else:
                logger.info("Etapas 3-4/5 — ITAD: nenhum AppID pendente. Pulando.")
        except Exception as e:
            logger.error(f"Etapas 3-4/5 — ITAD falhou: {e}", exc_info=True)

        # ── Etapa 5: Treinamento ML ──────────────────────────────────────────
        try:
            logger.info("Etapa 5/5 — Treinamento ML: iniciando")
            ProcessadorTreinamento.executar_treinamento()
        except Exception as e:
            # Treinamento falhou, mas não deve interromper o ciclo de coleta/ETL.
            logger.warning(f"Etapa 5/5 — Treinamento ML não executado nesta rodada: {e}")

        logger.info("="*60)
        logger.info("PIPELINE CONCLUÍDO — TAREFA PROCESSADA")
        logger.info("="*60)
