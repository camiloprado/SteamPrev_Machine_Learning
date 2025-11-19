from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
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
    _var_boolUseSupabase = os.getenv("USE_SUPABASE", "false").lower() == "true"

    @classmethod
    def seleciona_games(cls, arg_listDados: list) -> list:
        """
        Seleciona apenas os jogos dos dados fornecidos.
        
        Parâmetros:
        - arg_listDados (list): Lista de dados a serem filtrados.

        Retorna:
        - var_listGames (list): Lista contendo apenas os jogos.
        """
        try:
            var_listGames = []
            for var_dictDado in arg_listDados:
                if var_dictDado.get("detalhes").get("type") == "game" and not var_dictDado.get("detalhes").get("is_free"):
                    var_listGames.append(var_dictDado)
            logger.info(f"Número de jogos pagos selecionados: {len(var_listGames)}")
            return var_listGames
        except Exception as e:
            logger.error(f"Erro ao selecionar jogos: {e}")
            return []
        
    @classmethod
    def selecionar_base_dadosSteamBD(cls, arg_listDados: list) -> dict:
        """
        Seleciona os dados relevantes para a base de dados.
        """
        try:
            var_setCategorias = set()
            var_setGenero = set()
            var_strdataLancamento = ""
            var_listDados = []

            for var_dictApp in arg_listDados:
                # Dados Detalhes
                var_dictDetalhes = var_dictApp.get("detalhes")
                if not var_dictDetalhes:
                    logger.warning("Aplicativo inválido ou vazio encontrado, pulando.")
                    logger.debug(f"Dados do aplicativo: {var_dictApp}")
                    continue

                var_intAppid = int(var_dictDetalhes.get("steam_appid"))
                var_strName = var_dictDetalhes.get("name")

                if var_dictDetalhes.get("ratings") and var_dictDetalhes.get("ratings").get("dejus"):
                    var_strClassificacaoEtaria = var_dictDetalhes.get("ratings").get("dejus").get("rating")
                else:
                    var_strClassificacaoEtaria = "l"

                if var_dictDetalhes.get("supported_languages"):
                    var_listLinguagens = var_dictDetalhes.get("supported_languages").replace("<strong>*</strong>", "").replace("<br>", ", ").split(", ")
                else:
                    var_listLinguagens = []

                if var_dictDetalhes.get("developers"):
                    var_listDesenvolvedores = var_dictDetalhes.get("developers")
                else:
                    var_listDesenvolvedores = []

                if var_dictDetalhes.get("publishers"):
                    var_listDistribuidores = var_dictDetalhes.get("publishers")
                else:
                    var_listDistribuidores = []

                var_strPreco = var_dictDetalhes.get("price_overview").get("final_formatted") if var_dictDetalhes.get("price_overview") else 0
                var_intMetacriticScore = var_dictDetalhes.get("metacritic").get("score") if var_dictDetalhes.get("metacritic") else 0
                
                if var_dictDetalhes.get("categories"):
                    for var_dictCategoria in var_dictDetalhes.get("categories"):
                        var_setCategorias.add(var_dictCategoria.get("description"))
                
                if var_dictDetalhes.get("genres"):
                    for var_dictGenero in var_dictDetalhes.get("genres"):
                        var_setGenero.add(var_dictGenero.get("description"))

                if not var_dictDetalhes.get("release_date").get("coming_soon"):
                    if var_dictDetalhes.get("release_date").get("date"):
                        var_strdataLancamento = LimpezaDados.tratar_data(arg_strData=var_dictDetalhes.get("release_date").get("date"))
                    else:
                        var_strdataLancamento = None
                else:
                    var_strdataLancamento = "Em Breve"

                var_listCategorias = list(var_setCategorias)
                var_listGenero = list(var_setGenero)

                # Dados Reviews
                var_dictReviews = var_dictApp.get("reviews")
                var_intReviewScore = int(json.dumps(var_dictReviews.get("review_score"))) if var_dictReviews else 0
                var_intTotalReviews = int(json.dumps(var_dictReviews.get("total_reviews"))) if var_dictReviews else 0
                var_intTotalNegative = int(json.dumps(var_dictReviews.get("total_negative"))) if var_dictReviews else 0
                var_intTotalPositive = int(json.dumps(var_dictReviews.get("total_positive"))) if var_dictReviews else 0
                var_strReviewDesc = json.dumps(var_dictReviews.get("review_score_desc")) if var_dictReviews else None

                var_dictDados={
                    "appid": var_intAppid,
                    "nome": var_strName,
                    "classificacao_etaria": var_strClassificacaoEtaria,
                    "linguagens": var_listLinguagens,
                    "desenvolvedores": var_listDesenvolvedores,
                    "distribuidores": var_listDistribuidores,
                    "preco": var_strPreco,
                    "metacritic_score": var_intMetacriticScore,
                    "categorias": var_listCategorias,
                    "genero": var_listGenero,
                    "data_lancamento": var_strdataLancamento,
                    "review_score": var_intReviewScore,
                    "total_reviews": var_intTotalReviews,
                    "total_negative": var_intTotalNegative,
                    "total_positive": var_intTotalPositive,
                    "review_score_desc": var_strReviewDesc,
                }
                var_listDados.append(var_dictDados)
            return var_listDados
        
        except Exception as e:
            logger.error(f"Erro ao selecionar base de dados Steam BD: {e}")
            return []
        
    @classmethod
    def alimentar_banco_dados_raw(cls):
        """
        Alimenta o banco de dados raiz com os dados coletados da API.

        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            # Inicializa o contador de tentativas
            var_intTentativaMaxima = Settings._var_dictSettings.get("max_tentativas", 3)
            
            # Define o range de processamento por vez pelo .env
            var_intRange = int(os.getenv("RANGE_PROCESSAMENTO_APPIDS_RAW", 1000))
            
            # Carrega a lista de aplicativos
            var_listApp = SupabaseDB.buscar_todos_dadosSteamGenerico()
            var_listAppID = [var_listApp[j]['appid'] for j in range(len(var_listApp))]
            var_intTamanhoTotalFila = len(var_listAppID)

            # Tamanho do lote de carga a mais, se aplicavel
            var_intTamanhoaMais = int(os.getenv("TAMANHO_LOTE_CARGA_MAIS", 0))

            # Carregamento de teste de carga
            var_intAmbiente = os.getenv("AMBIENTE", "PROD").upper()

            # Verifica quais AppIDs já estão no banco de dados
            var_listDadosSteamBD = SupabaseDB.buscar_todos_dadosSteamRaw()
            for var_dictAppID in var_listDadosSteamBD:
                var_intAppID = var_dictAppID['appid']
                # Remove os AppIDs que já estão no banco de dados
                if var_intAppID in var_listAppID:
                    var_listAppID.remove(var_intAppID)

            if len(var_listAppID) != var_intTamanhoTotalFila:
                logger.info(f"Número total de AppIDs a processar após remoção: {len(var_listAppID)}. Removido: {var_intTamanhoTotalFila - len(var_listAppID)}")
                var_intTamanhoTotalFila = len(var_listAppID)

            # Verifica quais AppIDs estão desatualizados
            var_listAppIDDesatualizado = SupabaseDB.buscar_jogos_desatualizados()
            for var_dictAppID in var_listAppIDDesatualizado:
                var_intAppID = var_dictAppID['appid']
                # Adiciona os AppIDs desatualizados para reprocessamento
                if var_intAppID not in var_listAppID:
                    var_listAppID.append(var_intAppID)

            if len(var_listAppID) != var_intTamanhoTotalFila:
                logger.info(f"Número total de AppIDs a processar após verificação de desatualizados: {len(var_listAppID)}. Desatualizados adicionados: {len(var_listAppID) - var_intTamanhoTotalFila}")
                var_intTamanhoTotalFila = len(var_listAppID)

            # Itera sobre os aplicativos em lotes
            for i in range(0, var_intTamanhoTotalFila, var_intRange):
                logger.info(f"Processando aplicativos de {i + 1} a {min(i + var_intRange, var_intTamanhoTotalFila)} de {var_intTamanhoTotalFila}")
                logger.info(f"Tempo estimado restante: {((var_intTamanhoTotalFila - i) / var_intRange) * 2} minutos")
                logger.info(f"----------------------------------------")
                # Carrega os aplicativos atuais
                if var_intAmbiente == "HML":
                    var_listAppIDAtual = var_listAppID[i:i+int(os.getenv("BATCH_TESTE", 20))]
                else:
                    var_listAppIDAtual = var_listAppID[i:i+var_intRange]
                
                # Verifica quais AppIDs estão incompletos
                var_listAppIDIncompleto = SupabaseDB.buscar_jogos_incompletos(arg_boolRequererReviews=True)
                if var_listAppIDIncompleto:
                    for var_dictAppID in var_listAppIDIncompleto:
                        var_intAppID = var_dictAppID['appid']
                        # Adiciona os AppIDs com detalhes incompletos para reprocessamento
                        if var_dictAppID.get('detalhes') is None:
                            if var_intAppID not in var_listAppIDAtual:
                                var_listAppIDAtual.append(var_intAppID)
                logger.info(f"Número de IDs a processar neste lote: {len(var_listAppIDAtual)}")
                # Busca detalhes dos jogos
                asyncio.run(SteamClient.fetch_details_bulk_batched(arg_seqAppids=var_listAppIDAtual))
                
                # Busca reviews dos jogos incompletos
                if var_listAppIDIncompleto:
                    logger.info(f"Número de AppIDs com dados incompletos: {len(var_listAppIDIncompleto)}")
                    for var_dictAppID in var_listAppIDIncompleto:
                        var_intAppID = var_dictAppID['appid']
                        # Adiciona os AppIDs com reviews incompletos para reprocessamento
                        if var_dictAppID.get('reviews') is None:
                            if var_intAppID not in var_listAppIDAtual:
                                var_listAppIDAtual.append(var_intAppID)

                # Busca reviews dos jogos
                asyncio.run(SteamClient.fetch_reviews_summary_batched(arg_seqAppids=var_listAppIDAtual))
                
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados: {e}")
    
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
    def alimentar_banco_dados_Steam(cls):
        """
        Alimenta o banco de dados Steam BD com os dados processados do steam_raw.
        
        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            var_intTentativaMaxima = Settings._var_dictSettings.get("max_tentativas", 3)
            # Busca dados raw do Supabase da tabela steam_raw
            var_listDadosSteamRaw = SupabaseDB.buscar_todos_dadosSteamRaw()
            # Seleciona apenas os jogos
            var_listGames = cls.seleciona_games(var_listDadosSteamRaw)

            if var_listGames:
                # Seleciona os dados relevantes para a base de dados steam_bd
                var_listDados = cls.selecionar_base_dadosSteamBD(var_listGames)
                # Define o range de processamento por vez pelo .env
                var_intRange = int(os.getenv("RANGE_PROCESSAMENTO_APPIDS_BD", 3000))

                # Insere em lotes
                for i in range(0, len(var_listDados), var_intRange):
                    logger.info(f"Inserindo registros de {i + 1} a {min(i + var_intRange, len(var_listDados))} de {len(var_listDados)} na tabela steam_bd")
                    # Pega o lote atual
                    var_listDadosParcial = var_listDados[i:i+var_intRange]
                    # Tenta inserir os dados com múltiplas tentativas
                    for var_intTentativa in range(var_intTentativaMaxima):
                        try:
                            SupabaseDB.inserir_dadosSteamBD(var_listDadosParcial)
                            break  # Sai do loop se a inserção for bem-sucedida
                        except Exception as e:
                            logger.error(f"Erro ao inserir dados na tentativa {var_intTentativa + 1}: {e}")
                            if var_intTentativa < var_intTentativaMaxima - 1:
                                sleep(5)  # Espera 5 segundos antes de tentar novamente
                            else:
                                raise Exception(f"Erro {e} ao inserir dados na tabela steam_bd após {var_intTentativaMaxima} tentativas.")

                logger.info("Dados processados inseridos na tabela steam_bd com sucesso.")
            else:
                raise Exception("Nenhum jogo válido encontrado para processar.")

        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados Steam BD: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados Steam BD: {e}")
        
    @classmethod
    def alimentar_banco_dados_ITAD(cls):
        """
        Alimenta o banco de dados com dados do ITAD.
        
        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            # Inicializa o contador de tentativas
            var_intTentativaMaxima = Settings._var_dictSettings.get("max_tentativas", 3)
            var_listAppID = PostgreSQL.buscar_todos_appids()
            # Define o tamanho total da fila
            var_intTamanhoTotalFila = len(var_listAppID)
            # Define o range de processamento por vez pelo .env
            var_intRange = int(os.getenv("RANGE_PROCESSAMENTO_ITAD_RAW", 5000))
            
            # Itera sobre os aplicativos em lotes
            for i in range(0, var_intTamanhoTotalFila, var_intRange):
                logger.info(f"Processando aplicativos de {i + 1} a {min(i + var_intRange, var_intTamanhoTotalFila)} de {var_intTamanhoTotalFila}")
                # Carrega os aplicativos atuais
                var_listAppIDAtual = var_listAppID[i:i+var_intRange]
                
                # Verifica quais AppIDs já estão no banco de dados ITAD
                var_listAppIDnoBD = SupabaseDB.buscar_jogos_por_ID(arg_listAppIDs=var_listAppIDAtual, arg_strNomeTabel="itad_raw")

                # Verifica quais AppIDs estão desatualizados
                var_listAppIDDesatualizado = SupabaseDB.buscar_jogos_desatualizados(arg_strNomeTabela="itad_raw")
                for var_dictAppID in var_listAppIDnoBD:
                    var_intAppID = var_dictAppID['appid']
                    # Remove os AppIDs que já estão no banco de dados
                    if var_intAppID in var_listAppIDAtual:
                        var_listAppIDAtual.remove(var_intAppID)

                for var_dictAppID in var_listAppIDDesatualizado:
                    var_intAppID = var_dictAppID['appid']
                    if var_intAppID not in var_listAppIDAtual:
                        var_listAppIDAtual.append(var_intAppID)
                
                if not var_listAppIDAtual:
                    logger.info("Nenhum AppID encontrado para atualização nesta iteração.")
                    continue

                logger.info(f"Número de IDs a processar: {len(var_listAppIDAtual)}")

                # Busca detalhes dos jogos
                var_dictITAD = asyncio.run(SteamClient.lookup_itad_ids_batched(arg_seqAppids=var_listAppIDAtual))
                if not var_dictITAD:
                    logger.warning("Nenhum dado de detalhes retornado da API Steam.")
                else:
                    for var_dictITADValues in var_dictITAD.values():
                        var_dictRawData = {
                            "id_itad": var_dictITADValues.get("id"),
                            "slug": var_dictITADValues.get("slug"),
                            "title": var_dictITADValues.get("title"),
                            "type": var_dictITADValues.get("type"),
                            "mature": var_dictITADValues.get("mature"),
                            "assets": var_dictITADValues.get("assets"),
                            "ultima_atualizacao": datetime.now().isoformat(),
                        }
                        # Tenta inserir os dados com múltiplas tentativas
                        for var_intTentativa in range(var_intTentativaMaxima):
                            try:
                                SupabaseDB.inserir_dados_ITAD_Raw(var_dictRawData)    
                                break  # Sai do loop se a inserção for bem-sucedida
                            except Exception as e:
                                logger.error(f"Erro ao inserir dados ITAD para AppID {var_dictITADValues.get('id')} na tentativa {var_intTentativa + 1}: {e}")
                                if var_intTentativa < var_intTentativaMaxima - 1:
                                    sleep(5)  # Espera 5 segundos antes de tentar novamente
                                else:
                                    raise Exception(f"Erro ao inserir dados ITAD para AppID {var_dictITADValues.get('id')} após {var_intTentativaMaxima} tentativas.")
                    logger.info("Dados de detalhes inseridos com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados ITAD: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados ITAD: {e}")
    
    @classmethod
    def alimentar_banco_dados_ITAD_docker(cls):
        """
        Alimenta o banco de dados PostgreSQL (Docker) com dados do ITAD.
        Versão otimizada que usa o PostgreSQL local em vez do Supabase.
        Suporta divisão de trabalho entre múltiplos PCs usando PC_ID.
        
        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            PostgreSQL.conectar()
            
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
            var_listAppIDParaProcessar = PostgreSQL.buscar_appids_sem_itad(
                arg_intPcId=var_intPcId,
                arg_intTotalPcs=var_intTotalPcs
            )
            
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
                var_dictResultado = asyncio.run(SteamClient.lookup_itad_ids_batched(arg_seqAppids=var_listAppIDAtual))
                
                if var_dictResultado:
                    logger.info(f"Obtidos {len(var_dictResultado):,} registros do ITAD")
                    
                    # Insere os dados no PostgreSQL (itad_raw + steam_itad_mapping)
                    var_intInseridos = PostgreSQL.inserir_dados_itad_raw_bulk(var_dictResultado)
                    logger.info(f"Registros inseridos no banco: {var_intInseridos:,}")
                else:
                    logger.warning("Nenhum dado retornado do ITAD neste lote")
                
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
        
        
    # ================ AUSENTES ================
    @staticmethod
    def criar_reviews_padrao(arg_intAppid: int, arg_strMotivo: str = "Sem reviews disponíveis") -> Dict[str, Any]:
        """
        Cria um dicionário de reviews com valores padrão.
        
        Parâmetros:
        - arg_intAppid (int): AppID do jogo
        - arg_strMotivo (str): Motivo da ausência de reviews
        
        Retorna:
        - dict: Dicionário com estrutura de reviews padrão
        """
        var_dictReviewsPadrao = {
            "appid": arg_intAppid,
            "total_reviews": 0,
            "total_positive": 0,
            "total_negative": 0,
            "review_score": 0,
            "review_score_desc": arg_strMotivo,
            "_padrao": True,  # Flag para identificar dados padrão
            "_motivo": arg_strMotivo
        }
        
        logger.debug(f"AppID {arg_intAppid}: Reviews preenchidos com valores padrão - {arg_strMotivo}")
        return var_dictReviewsPadrao
    
    @classmethod
    def preencher_se_ausente(cls, arg_dictDados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preenche reviews com valores padrão se estiverem ausentes.
        
        Parâmetros:
        - arg_dictDados (dict): Dicionário com dados do jogo (pode ou não ter 'reviews')
        
        Retorna:
        - dict: Dicionário com reviews garantidos (originais ou padrão)
        """
        var_intAppid = arg_dictDados.get("appid")
        
        # Se já tem reviews válidos, retorna como está
        if "reviews" in arg_dictDados and arg_dictDados["reviews"] is not None:
            var_dictReviews = arg_dictDados["reviews"]
            # Verifica se tem pelo menos total_reviews
            if isinstance(var_dictReviews, dict) and "total_reviews" in var_dictReviews:
                return arg_dictDados
        
        # Se não tem reviews, preenche com padrão
        arg_dictDados["reviews"] = cls.criar_reviews_padrao(
            var_intAppid,
            "API Steam não retornou reviews"
        )
        
        return arg_dictDados
    
    @classmethod
    def processar_lote(cls, arg_listDados: list) -> list:
        """
        Processa um lote de dados, preenchendo reviews ausentes.
        
        Parâmetros:
        - arg_listDados (list): Lista de dicionários com dados de jogos
        
        Retorna:
        - list: Lista processada com reviews garantidos
        """
        var_intTotal = len(arg_listDados)
        var_intPreenchidos = 0
        
        var_listProcessados = []
        for var_dictDado in arg_listDados:
            var_boolTemReviews = "reviews" in var_dictDado and var_dictDado["reviews"] is not None
            
            var_dictProcessado = cls.preencher_se_ausente(var_dictDado)
            var_listProcessados.append(var_dictProcessado)
            
            if not var_boolTemReviews:
                var_intPreenchidos += 1
        
        if var_intPreenchidos > 0:
            logger.info(f"Reviews padrão: {var_intPreenchidos}/{var_intTotal} jogos ({var_intPreenchidos/var_intTotal:.1%})")
        
        return var_listProcessados
