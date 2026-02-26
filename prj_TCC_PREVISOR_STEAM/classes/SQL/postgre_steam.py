from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

from datetime import datetime
from psycopg2.extras import execute_batch, execute_values
import json, logging

logger = logging.getLogger(__name__)

class PostgreSQLSteam(PostgreSQL):
    """
    Classe para operações com PostgreSQL.
    """
    
    @classmethod
    def inserir_dadosSteamRaw_Bulk(cls, arg_listDados: list) -> None:
        """
        Insere ou atualiza dados em bulk na tabela steam_raw de forma otimizada e atualiza steam_generico automaticamente.

        Parâmetros:
        - arg_listDados (list): Lista de dicionários com os dados a inserir.
                               Cada dicionário deve ter: appid, detalhes (opcional), reviews (opcional)
        """
        var_connConnection = cls.conectar()
        
        try:
            if not arg_listDados:
                logger.warning("Lista de dados vazia, nenhum dado para inserir.")
                raise Exception("Lista de dados vazia, nenhum dado para inserir.")
            
            # Prepara os valores para inserção em batch
            var_listValores = []
            
            # Processa cada registro para extrair os campos necessários e converter para JSON string
            for var_dictDados in arg_listDados:
                # Valida presença de appid obrigatório
                var_intAppid = var_dictDados.get("appid")
                if not var_intAppid:
                    logger.warning(f"AppID ausente em dados, pulando registro: {var_dictDados}")
                    continue
                
                # Extrai detalhes e reviews, convertendo para JSON string se necessário
                var_dictDetalhes = var_dictDados.get("detalhes")
                var_dictReviews = var_dictDados.get("reviews")
                var_dateNow = var_dictDados.get("ultima_atualizacao", datetime.utcnow().isoformat(sep=' ', timespec='microseconds'))

                # Converte para JSON string se não for None/vazio
                var_strDetalhes = json.dumps(var_dictDetalhes) if var_dictDetalhes else None
                var_strReviews = json.dumps(var_dictReviews) if var_dictReviews else None
                
                var_listValores.append((
                    var_intAppid,
                    var_strDetalhes,
                    var_strReviews,
                    var_dateNow
                ))
            
            if not var_listValores:
                logger.warning("Nenhum dado válido para inserir após processamento.")
                return
            
            # Executa a inserção em batch otimizada com execute_values
            var_strSQL = """
            INSERT INTO steam_raw (appid, detalhes, reviews, ultima_atualizacao)
            VALUES %s
            ON CONFLICT (appid) DO UPDATE SET
                detalhes = COALESCE(EXCLUDED.detalhes, steam_raw.detalhes),
                reviews = COALESCE(EXCLUDED.reviews, steam_raw.reviews),
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            with var_connConnection.cursor() as cursor:
                execute_values(
                    cursor, 
                    var_strSQL,  # SQL com placeholder %s para os valores em batch
                    var_listValores, # Lista de tuplas com os valores a serem inseridos
                    template='(%s, %s, %s, %s)', # Define o template para os valores a serem inseridos
                    page_size=200 # Ajuste o tamanho do lote conforme necessário para otimizar desempenho e evitar sobrecarga de memória
                )
                # Obtém o número de registros processados
                var_intRowCount = cursor.rowcount

                # Confirma a transação após a inserção em batch
                var_connConnection.commit()
                logger.info(f"Inserção em bulk concluída: {var_intRowCount} registros processados em steam_raw.")
                
                var_listAppidsInseridos = []
                for var_dictDados in arg_listDados:
                    var_intAppid = var_dictDados.get("appid")
                    var_dictDetalhes = var_dictDados.get("detalhes")
                    if var_dictDetalhes == "AUSENTE":
                        continue
                    
                    if var_intAppid and var_dictDetalhes and var_dictDetalhes.get("name"):
                        var_listAppidsInseridos.append((
                            var_intAppid,
                            var_dictDetalhes.get("name")
                        ))
                
                # Insere/atualiza steam_generico (batch)
                if var_listAppidsInseridos:
                    var_strSQLGenerico = """
                    INSERT INTO steam_generico (appid, name, ultima_atualizacao)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (appid) DO UPDATE SET
                        name = EXCLUDED.name,
                        ultima_atualizacao = EXCLUDED.ultima_atualizacao;
                    """
                    
                    with var_connConnection.cursor() as var_curCursor:
                        execute_batch(var_curCursor, var_strSQLGenerico, var_listAppidsInseridos)
                    
                    var_connConnection.commit()
                    logger.debug(f"Sincronizados {len(var_listAppidsInseridos)} registros em steam_generico")
        
        except Exception as err:
            logger.error(f"Erro ao inserir dados steam_raw: {err}")
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao inserir dados em bulk em steam_raw e/ou steam_generico: {err}")
        finally:
            cls.desconectar(var_connConnection)

    @classmethod
    def inserir_dadosSteamGenerico(cls, arg_listDadosGerais: list) -> bool:
        """
        Insere ou atualiza dados na tabela steam_generico.
        Apenas insere jogos que estão desatualizados.

        Parâmetros:
        - arg_listDadosGerais (list): Lista de dicionários com os dados gerais da Steam
                                      Cada dicionário deve conter: {"appid": int, "name": str}

        Retorna:
        - bool: True se inseriu dados, False se não havia jogos desatualizados
        """
        var_connConnection = None
        try:
            # Verifica se há jogos desatualizados
            var_listDesatualizados = cls.buscar_jogos_desatualizados(arg_strNomeTabela="steam_generico")

            if not var_listDesatualizados:
                logger.info("Nenhum jogo desatualizado encontrado em steam_generico.")
                return False
            
            # Cria set de AppIDs desatualizados para verificação rápida
            var_setAppidsDesatualizados = {jogo.get("appid") for jogo in var_listDesatualizados}
            
            # Filtra apenas os dados que precisam ser atualizados
            var_listDadosParaInserir = [
                dados for dados in arg_listDadosGerais 
                if dados.get("appid") in var_setAppidsDesatualizados
            ]
            
            if not var_listDadosParaInserir:
                logger.info("Nenhum dado dos fornecidos precisa ser atualizado.")
                return False
            
            # Insere/atualiza em lotes de 5000
            var_intTotalInserido = 0
            for var_intIndex in range(0, len(var_listDadosParaInserir), 5000):
                var_listLote = var_listDadosParaInserir[var_intIndex:var_intIndex + 5000]
                
                for var_dictDados in var_listLote:
                    var_intAppid = var_dictDados.get("appid")
                    if not var_intAppid:
                        logger.warning("AppID ausente em dados steam_generico")
                        continue
                    
                    var_strSQL = """
                    INSERT INTO steam_generico (appid, name, ultima_atualizacao)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (appid) DO UPDATE SET
                        name = EXCLUDED.name,
                        ultima_atualizacao = EXCLUDED.ultima_atualizacao;
                    """
                    
                    var_connConnection = cls.conectar()
                    with var_connConnection.cursor() as cursor:
                        cursor.execute(var_strSQL, (
                            var_intAppid,
                            var_dictDados.get("name"),
                            datetime.now()
                        ))
                        var_intTotalInserido += cursor.rowcount
                
                var_connConnection.commit()
                logger.info(f"Lote de {len(var_listLote)} registros processado.")
            
            logger.info(f"Dados de steam_generico salvos/atualizados para {var_intTotalInserido} registros.")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_generico: {e}")
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao inserir dados steam_generico: {e}")

        finally:
            if var_connConnection:
                cls.desconectar(var_connConnection)

    @classmethod
    def inserir_steam_unificado(cls, arg_dictDados: dict) -> None:
        """
        Insere ou atualiza um registro na tabela steam_unificado.
        Combina dados estruturados + JSONB completos.
        
        Parâmetros:
        - arg_dictDados (dict): Dicionário com os dados do jogo
        
        Retorna:
        - None
        """
        try:
            var_connConnection = cls.conectar()
            
            if var_connConnection is None:
                logger.error("Conexão com banco de dados não estabelecida")
                return
            
            var_strSQL = """
            INSERT INTO steam_unificado (
                appid, nome, classificacao_etaria, linguagens, desenvolvedores,
                distribuidores, preco, metacritic_score, categorias, genero,
                data_lancamento, type, review_score, total_reviews, total_negative,
                total_positive, review_score_desc, detalhes_completos, reviews_completos,
                ultima_atualizacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                nome = EXCLUDED.nome,
                classificacao_etaria = EXCLUDED.classificacao_etaria,
                linguagens = EXCLUDED.linguagens,
                desenvolvedores = EXCLUDED.desenvolvedores,
                distribuidores = EXCLUDED.distribuidores,
                preco = EXCLUDED.preco,
                metacritic_score = EXCLUDED.metacritic_score,
                categorias = EXCLUDED.categorias,
                genero = EXCLUDED.genero,
                data_lancamento = EXCLUDED.data_lancamento,
                type = EXCLUDED.type,
                review_score = EXCLUDED.review_score,
                total_reviews = EXCLUDED.total_reviews,
                total_negative = EXCLUDED.total_negative,
                total_positive = EXCLUDED.total_positive,
                review_score_desc = EXCLUDED.review_score_desc,
                detalhes_completos = EXCLUDED.detalhes_completos,
                reviews_completos = EXCLUDED.reviews_completos,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            var_tupleValores = (
                arg_dictDados.get('appid'),
                arg_dictDados.get('nome', 'Desconhecido'),
                arg_dictDados.get('classificacao_etaria'),
                arg_dictDados.get('linguagens'),
                arg_dictDados.get('desenvolvedores'),
                arg_dictDados.get('distribuidores'),
                arg_dictDados.get('preco'),
                arg_dictDados.get('metacritic_score'),
                arg_dictDados.get('categorias'),
                arg_dictDados.get('genero'),
                arg_dictDados.get('data_lancamento'),
                arg_dictDados.get('type', 'ausente'),
                arg_dictDados.get('review_score'),
                arg_dictDados.get('total_reviews'),
                arg_dictDados.get('total_negative'),
                arg_dictDados.get('total_positive'),
                arg_dictDados.get('review_score_desc'),
                json.dumps(arg_dictDados.get('detalhes_completos')) if arg_dictDados.get('detalhes_completos') else None,
                json.dumps(arg_dictDados.get('reviews_completos')) if arg_dictDados.get('reviews_completos') else None,
                datetime.now()
            )
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, var_tupleValores)
                var_connConnection.commit()
                
        except Exception as e:
            logger.error(f"Erro ao inserir em steam_unificado: {e}")
            if var_connConnection:
                var_connConnection.rollback()
            raise

        finally:
            cls.desconectar(var_connConnection)

    @classmethod
    def inserir_steam_unificado_batch(cls, arg_listDados: list) -> None:
        """
        Insere ou atualiza múltiplos registros na tabela steam_unificado usando batch.
        Combina dados estruturados + JSONB completos.
        
        Parâmetros:
        - arg_listDados (list): Lista de dicionários com os dados dos jogos
        
        Retorna:
        - None
        """
        try:
            var_connConnection = cls.conectar()
            
            if var_connConnection is None:
                logger.error("Conexão com banco de dados não estabelecida")
                return
            
            var_strSQL = """
            INSERT INTO steam_unificado (
                appid, nome, classificacao_etaria, linguagens, desenvolvedores,
                distribuidores, preco, metacritic_score, categorias, genero,
                data_lancamento, type, review_score, total_reviews, total_negative,
                total_positive, review_score_desc, detalhes_completos, reviews_completos,
                ultima_atualizacao
            ) VALUES %s
            ON CONFLICT (appid) DO UPDATE SET
                nome = EXCLUDED.nome,
                classificacao_etaria = EXCLUDED.classificacao_etaria,
                linguagens = EXCLUDED.linguagens,
                desenvolvedores = EXCLUDED.desenvolvedores,
                distribuidores = EXCLUDED.distribuidores,
                preco = EXCLUDED.preco,
                metacritic_score = EXCLUDED.metacritic_score,
                categorias = EXCLUDED.categorias,
                genero = EXCLUDED.genero,
                data_lancamento = EXCLUDED.data_lancamento,
                type = EXCLUDED.type,
                review_score = EXCLUDED.review_score,
                total_reviews = EXCLUDED.total_reviews,
                total_negative = EXCLUDED.total_negative,
                total_positive = EXCLUDED.total_positive,
                review_score_desc = EXCLUDED.review_score_desc,
                detalhes_completos = EXCLUDED.detalhes_completos,
                reviews_completos = EXCLUDED.reviews_completos,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            var_listValores = []
            for var_dictDados in arg_listDados:
                var_tupleValores = (
                    var_dictDados.get('appid'),
                    var_dictDados.get('nome', 'Desconhecido'),
                    var_dictDados.get('classificacao_etaria'),
                    var_dictDados.get('linguagens'),
                    var_dictDados.get('desenvolvedores'),
                    var_dictDados.get('distribuidores'),
                    var_dictDados.get('preco'),
                    var_dictDados.get('metacritic_score'),
                    var_dictDados.get('categorias'),
                    var_dictDados.get('genero'),
                    var_dictDados.get('data_lancamento'),
                    var_dictDados.get('type', 'ausente'),
                    var_dictDados.get('review_score'),
                    var_dictDados.get('total_reviews'),
                    var_dictDados.get('total_negative'),
                    var_dictDados.get('total_positive'),
                    var_dictDados.get('review_score_desc'),
                    json.dumps(var_dictDados.get('detalhes_completos')) if var_dictDados.get('detalhes_completos') else None,
                    json.dumps(var_dictDados.get('reviews_completos')) if var_dictDados.get('reviews_completos') else None,
                    datetime.now()
                )
                var_listValores.append(var_tupleValores)

            if var_listValores:
                with var_connConnection.cursor() as var_curCursor:
                    execute_values(
                        var_curCursor, 
                        var_strSQL,  # SQL com placeholder %s para os valores em batch
                        var_listValores, # Lista de tuplas com os valores a serem inseridos
                        template='(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', # Define o template para os valores a serem inseridos
                        page_size=200 # Ajuste o tamanho do lote conforme necessário para otimizar desempenho e evitar sobrecarga de memória
                    )
                    # Obtém o número de registros processados
                    var_intRowCount = var_curCursor.rowcount

                    # Confirma a transação após a inserção em batch
                    var_connConnection.commit()
                    logger.info(f"Inserção em bulk concluída: {var_intRowCount} registros processados em steam_raw.")

        except Exception as e:
            logger.error(f"Erro ao inserir em steam_unificado batch: {e}")
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao inserir em steam_unificado batch: {e}")
        finally:
            if var_connConnection:
                cls.desconectar(var_connConnection)

    @classmethod
    def buscar_appids_nao_processados_otimizado(cls, arg_intPcId: int = 1, arg_intTotalPcs: int = 1, arg_intLimite: int = None) -> list[int]:
        """
        Busca AppIDs que NÃO estão em steam_raw usando SQL eficiente.
        Evita carregar todos os 280k registros na memória.
        Suporta divisão de trabalho entre múltiplos PCs.

        Parâmetros:
        - arg_intPcId (int): ID deste PC (1, 2, 3...). (Padrão: 1)
        - arg_intTotalPcs (int): Total de PCs processando. (Padrão: 1)
        - arg_intLimite (int): Número máximo de AppIDs a retornar. (Padrão: None = todos)

        Retorna:
        - list[int]: Lista de AppIDs que precisam ser processados (já filtrados para este PC).
        """
        var_connConnection = cls.conectar()
        try:
            logger.info(f"Buscando AppIDs não processados (PC {arg_intPcId}/{arg_intTotalPcs})...")
            
            # faz LEFT JOIN direto no banco
            # Retorna apenas AppIDs que NÃO existem em steam_raw
            var_strSQL = """
            SELECT sg.appid 
            FROM steam_generico sg
            LEFT JOIN steam_raw sr ON sg.appid = sr.appid
            WHERE sr.appid IS NULL
            """
            
            # Aplica filtro de divisão de trabalho entre PCs (se aplicável)
            if arg_intTotalPcs > 1:
                # MOD(appid, total_pcs) = (pc_id - 1)
                # PC 1: MOD(appid, 2) = 0 (pares)
                # PC 2: MOD(appid, 2) = 1 (ímpares)
                var_strSQL += f" AND MOD(sg.appid, {arg_intTotalPcs}) = {arg_intPcId - 1}"
            
            if arg_intLimite:
                var_strSQL += f" LIMIT {arg_intLimite}"
            
            var_strSQL += ";"
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                
                logger.info(f"Encontrados {len(var_listAppids):,} AppIDs não processados para PC {arg_intPcId}")
                return var_listAppids
                
        except Exception as e:
            logger.error(f"Erro ao buscar AppIDs não processados: {e}")
            return []
        finally:
            cls.desconectar(var_connConnection)
    
    @classmethod
    def buscar_appids_desatualizados_otimizado(cls, arg_intDiasAtualizacao: int = None, arg_intPcId: int = 1, arg_intTotalPcs: int = 1, arg_strNomeTabela: str = "steam_raw") -> list[int]:
        """
        Busca apenas AppIDs de jogos desatualizados.
        Não carrega dados completos, apenas os IDs.

        Parâmetros:
        - arg_intDiasAtualizacao (int): Dias para considerar desatualizado. (Padrão: 30)
        - arg_intPcId (int): ID deste PC. (Padrão: 1)
        - arg_intTotalPcs (int): Total de PCs. (Padrão: 1)

        Retorna:
        - list[int]: Lista de AppIDs desatualizados.
        """
        try:
            var_connConnection = cls.conectar()
            
            if var_connConnection is None:
                logger.error("Conexão com banco de dados não estabelecida")
                return []
            
            var_intDias = arg_intDiasAtualizacao or Settings._var_dictSettings.get("dias_para_atualizacao", 30)
            
            logger.info(f"Buscando AppIDs desatualizados (>{var_intDias} dias)...")

            if arg_strNomeTabela == 'itad_raw':
                arg_strNomeTabela = 'steam_itad_mapping sim JOIN itad_raw ir ON sim.id_itad = ir.id_itad'

            var_strSQL = f"""
            SELECT appid FROM {arg_strNomeTabela}
            WHERE ultima_atualizacao < CURRENT_DATE - INTERVAL '{var_intDias} days'
            """
            
            # Aplica filtro de PC se necessário
            if arg_intTotalPcs > 1:
                var_strSQL += f" AND MOD(appid, {arg_intTotalPcs}) = {arg_intPcId - 1}"
            
            var_strSQL += ";"
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()  
                var_listAppids = [row[0] for row in var_listResultados]
                
                logger.info(f"Encontrados {len(var_listAppids):,} AppIDs desatualizados")
                return var_listAppids
                
        except Exception as e:
            logger.error(f"Erro ao buscar AppIDs desatualizados: {e}")
            return []
        finally:            
            cls.desconectar(var_connConnection)
