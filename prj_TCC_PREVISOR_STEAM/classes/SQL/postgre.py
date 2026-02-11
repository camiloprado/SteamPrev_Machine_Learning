from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from datetime import datetime
from psycopg2.extras import execute_batch
from time import sleep
from typing import Generator
import psycopg2, json, logging

logger = logging.getLogger(__name__)

class PostgreSQL:
    """
    Classe para operações com PostgreSQL.
    """
    _var_connConnection = None

    @classmethod
    def conectar(cls):
        """
        Estabelece uma conexão com o banco de dados PostgreSQL.
        Levanta exceção se não conseguir conectar.
        """
        if cls._var_connConnection is None or cls._var_connConnection.closed:
            try:
                var_strDbname = Settings._var_dictSettings["db_name"]
                var_strUser = Settings._var_dictSettings["db_user"]
                var_strPassword = Settings._var_dictSettings["db_password"]
                var_strHost = Settings._var_dictSettings["db_host"]
                var_intPort = Settings._var_dictSettings["db_port"]
                cls._var_connConnection = psycopg2.connect(
                    dbname=var_strDbname,
                    user=var_strUser,
                    password=var_strPassword,
                    host=var_strHost,
                    port=var_intPort
                )
                logger.info(f"Conexão com o banco de dados estabelecida com sucesso: {var_strUser}@{var_strHost}:{var_intPort}/{var_strDbname}")
            except Exception as e:
                cls._var_connConnection = None
                logger.error(f"Erro ao conectar ao banco de dados: {e}")
                raise Exception(f"Erro ao conectar ao banco de dados: {e}")
        
    @classmethod
    def desconectar(cls):
        """
        Encerra a conexão com o banco de dados PostgreSQL.
        """
        try:
            if cls._var_connConnection:
                cls._var_connConnection.close()
                logger.info("Conexão com o banco de dados encerrada.")
                cls._var_connConnection = None
            else:
                logger.info("Nenhuma conexão ativa para encerrar.")
        except Exception as e:
            logger.error(f"Erro ao desconectar do banco de dados: {e}")
            raise Exception(f"Erro ao desconectar do banco de dados: {e}")
    
    @classmethod
    def criar_tabela(cls, arg_strSQL: str):
        """
        Executa um comando SQL para criar uma tabela no banco de dados.

        Parâmetros:
        - arg_strSQL (str): Comando SQL para criar a tabela.
        """
        try:
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(arg_strSQL)
                cls._var_connConnection.commit()
                logger.info("Tabela criada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao criar a tabela: {e}")
            raise Exception(f"Erro ao criar a tabela: {e}")
            
    @classmethod
    def inserir_dadosSteamRaw_Bulk(cls, arg_listDados: list) -> None:
        """
        Insere ou atualiza dados em bulk na tabela steam_raw de forma otimizada e atualiza steam_generico automaticamente.
        Parâmetros:
        - arg_listDados (list): Lista de dicionários com os dados a inserir.
                               Cada dicionário deve ter: appid, detalhes (opcional), reviews (opcional)
        """
        cls.conectar()
        
        try:
            if not arg_listDados:
                logger.warning("Lista de dados vazia, nenhum dado para inserir.")
                raise Exception("Lista de dados vazia, nenhum dado para inserir.")
            
            # SQL para UPSERT (INSERT ... ON CONFLICT)
            var_strSQL = """
            INSERT INTO steam_raw (appid, detalhes, reviews, ultima_atualizacao)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                detalhes = COALESCE(EXCLUDED.detalhes, steam_raw.detalhes),
                reviews = COALESCE(EXCLUDED.reviews, steam_raw.reviews),
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            # Prepara os valores para inserção em batch
            var_listValores = []
            
            for var_dictDados in arg_listDados:
                var_intAppid = var_dictDados.get("appid")
                if not var_intAppid:
                    logger.warning(f"AppID ausente em dados, pulando registro: {var_dictDados}")
                    continue
                
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
            
            # Executa a inserção em batch
            with cls._var_connConnection.cursor() as cursor:
                cursor.executemany(var_strSQL, var_listValores)
                var_intRowCount = cursor.rowcount
                cls._var_connConnection.commit()
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
                    
                    with cls._var_connConnection.cursor() as var_curCursor:
                        execute_batch(var_curCursor, var_strSQLGenerico, var_listAppidsInseridos)
                    
                    cls._var_connConnection.commit()
                    logger.debug(f"Sincronizados {len(var_listAppidsInseridos)} registros em steam_generico")
        
        except Exception as err:
            logger.error(f"Erro ao inserir dados steam_raw: {err}")
            cls._var_connConnection.rollback()
            raise Exception(f"Erro ao inserir dados em bulk em steam_raw e/ou steam_generico: {err}")
        finally:
            cls.desconectar()
            
    @classmethod
    def buscar_todos_dados(cls, arg_strNomeTabela: str) -> list[dict]:
        """
        Busca todos os dados de jogos na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela onde os dados serão buscados.

        Retorna:
        - list[dict]: Lista de dicionários com os dados dos jogos.
        """
        try:
            var_strSQL = f"""
            SELECT * FROM {arg_strNomeTabela};
            """
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_resultados = cursor.fetchall()
                var_listColnames = [desc[0] for desc in cursor.description]
                var_listDados = [dict(zip(var_listColnames, row)) for row in var_resultados]
                return var_listDados
        except Exception as e:
            logger.error(f"Erro ao buscar todos os dados da tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao buscar todos os dados da tabela '{arg_strNomeTabela}': {e}")
    
    @classmethod
    def buscar_jogos_desatualizados(cls, arg_strNomeTabela: str = "steam_raw", arg_intDiasAtualizacao: int = None, arg_intLimite: int = None) -> list[dict]:
        """
        Busca jogos que não foram atualizados recentemente.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela onde os dados serão buscados. (Padrão: "steam_raw")
        - arg_intDiasAtualizacao (int): Número de dias para considerar desatualizado. Se None, usa settings. (Padrão: None)
        - arg_intLimite (int): Número máximo de registros a retornar. (Padrão: None = todos)

        Retorna:
        - list[dict]: Lista de jogos desatualizados.
        """
        cls.conectar()
        try:
            var_intDias = arg_intDiasAtualizacao or Settings._var_dictSettings.get("dias_para_atualizacao", 30)
            var_dataCorte = datetime.now() - __import__('datetime').timedelta(days=var_intDias)
            
            var_strSQL = f"""
            SELECT * FROM {arg_strNomeTabela}
            WHERE ultima_atualizacao < %s
            """
            
            if arg_intLimite:
                var_strSQL += f" LIMIT {arg_intLimite}"
            
            var_strSQL += ";"
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (var_dataCorte,))
                var_listResultados = cursor.fetchall()
                var_listColnames = [desc[0] for desc in cursor.description]
                var_listDados = [dict(zip(var_listColnames, row)) for row in var_listResultados]
                logger.info(f"Encontrados {len(var_listDados)} jogos desatualizados na tabela '{arg_strNomeTabela}'.")
                return var_listDados
        except Exception as e:
            logger.error(f"Erro ao buscar jogos desatualizados: {e}")
            return []
    
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
        cls.conectar()
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
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                
                logger.info(f"Encontrados {len(var_listAppids):,} AppIDs não processados para PC {arg_intPcId}")
                return var_listAppids
                
        except Exception as e:
            logger.error(f"Erro ao buscar AppIDs não processados: {e}")
            return []
    
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
            cls.conectar()
            
            if cls._var_connConnection is None:
                logger.error("Conexão com banco de dados não estabelecida")
                return []
            
            var_intDias = arg_intDiasAtualizacao or Settings._var_dictSettings.get("dias_para_atualizacao", 30)
            var_dataCorte = datetime.now() - __import__('datetime').timedelta(days=var_intDias)
            
            logger.info(f"Buscando AppIDs desatualizados (>{var_intDias} dias)...")

            if arg_strNomeTabela == 'itad_raw':
                arg_strNomeTabela = 'steam_itad_mapping sim JOIN itad_raw ir ON sim.id_itad = ir.id_itad'

            var_strSQL = f"""
            SELECT appid FROM {arg_strNomeTabela}
            WHERE ultima_atualizacao < %s
            """
            
            # Aplica filtro de PC se necessário
            if arg_intTotalPcs > 1:
                var_strSQL += f" AND MOD(appid, {arg_intTotalPcs}) = {arg_intPcId - 1}"
            
            var_strSQL += ";"
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (var_dataCorte,))
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                
                logger.info(f"Encontrados {len(var_listAppids):,} AppIDs desatualizados")
                return var_listAppids
                
        except Exception as e:
            logger.error(f"Erro ao buscar AppIDs desatualizados: {e}")
            return []
    
    @classmethod
    def buscar_appids_sem_itad(cls, arg_intLimit: int = None) -> list:
        """
        Busca AppIDs que NÃO têm dados ITAD válidos (steam_itad_mapping).
        
        Retorna AppIDs que NÃO estão em steam_itad_mapping (nunca processados ou falharam).
        
        Args:
            arg_intLimit: Limite de resultados (None = todos)
        
        Returns:
            Lista de AppIDs sem dados ITAD válidos
        """
        cls.conectar()
        
        try:
            var_strSQL = """
            SELECT sg.appid
            FROM steam_generico sg
            LEFT JOIN steam_itad_mapping sim ON sg.appid = sim.appid
            WHERE sim.appid IS NULL
            ORDER BY sg.appid
            """
            
            if arg_intLimit:
                var_strSQL += f" LIMIT {arg_intLimit}"
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = [row[0] for row in cursor.fetchall()]
            
            return var_listResultados
            
        except Exception as e:
            raise Exception(f"Erro ao buscar AppIDs sem ITAD: {e}")
        
        finally:
            cls.desconectar()
    
    @classmethod
    def buscar_appids_itad_desatualizados(cls, arg_intDiasAtualizacao: int = None, arg_intPcId: int = 1, arg_intTotalPcs: int = 1) -> list[int]:
        """
        Busca AppIDs com dados ITAD desatualizados na tabela itad_raw.
        
        Parâmetros:
        - arg_intDiasAtualizacao (int): Dias para considerar desatualizado. (Padrão: 90)
        - arg_intPcId (int): ID deste PC. (Padrão: 1)
        - arg_intTotalPcs (int): Total de PCs. (Padrão: 1)
        
        Retorna:
        - list[int]: Lista de AppIDs com ITAD desatualizado
        """
        cls.conectar()
        try:
            var_intDias = arg_intDiasAtualizacao or 90  # ITAD atualiza menos frequentemente
            var_dataCorte = datetime.now() - __import__('datetime').timedelta(days=var_intDias)
            
            logger.info(f"Buscando AppIDs ITAD desatualizados (>{var_intDias} dias)...")
            
            var_strSQL = """
            SELECT sim.appid 
            FROM steam_itad_mapping sim
            JOIN itad_raw ir ON sim.id_itad = ir.id_itad
            WHERE ir.ultima_atualizacao < %s
            """
            
            # Aplica filtro de PC se necessário
            if arg_intTotalPcs > 1:
                var_strSQL += f" AND MOD(sim.appid, {arg_intTotalPcs}) = {arg_intPcId - 1}"
            
            var_strSQL += ";"
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (var_dataCorte,))
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                
                logger.info(f"Encontrados {len(var_listAppids):,} AppIDs ITAD desatualizados")
                return var_listAppids
                
        except Exception as e:
            raise Exception(f"Erro ao buscar AppIDs ITAD desatualizados: {e}")
    
    @classmethod
    def inserir_dados_itad_raw_bulk(cls, arg_dictDadosItad: dict[int, dict]) -> int:
        """
        Insere ou atualiza dados na tabela itad_raw e steam_itad_mapping em bulk.
        
        Parâmetros:
        - arg_dictDadosItad (dict): Dicionário mapeando appid -> dados ITAD
                                    Estrutura esperada: {appid: {"id": str, "slug": str, "title": str, ...}}
        
        Retorna:
        - int: Número de registros inseridos/atualizados
        """
        cls.conectar()
        try:
            if not arg_dictDadosItad:
                logger.warning("Nenhum dado ITAD fornecido para inserção")
                return 0
            
            var_intInseridos = 0
            var_dateNow = datetime.now()
            
            for var_intAppid, var_dictDados in arg_dictDadosItad.items():
                try:
                    # Extrai dados do ITAD
                    var_strIdItad = var_dictDados.get("id")
                    var_strSlug = var_dictDados.get("slug")
                    var_strTitle = var_dictDados.get("title")
                    var_strType = var_dictDados.get("type")
                    var_boolMature = var_dictDados.get("mature", False)
                    var_jsonAssets = json.dumps(var_dictDados.get("assets", {}))
                    
                    if not var_strIdItad:
                        logger.warning(f"AppID {var_intAppid}: ID ITAD ausente, pulando")
                        continue
                    
                    with cls._var_connConnection.cursor() as cursor:
                        # 1. Insere/atualiza na tabela itad_raw
                        var_strSQLItadRaw = """
                        INSERT INTO itad_raw (id_itad, slug, title, type, mature, assets, ultima_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (id_itad) 
                        DO UPDATE SET
                            slug = EXCLUDED.slug,
                            title = EXCLUDED.title,
                            type = EXCLUDED.type,
                            mature = EXCLUDED.mature,
                            assets = EXCLUDED.assets,
                            ultima_atualizacao = EXCLUDED.ultima_atualizacao;
                        """
                        cursor.execute(var_strSQLItadRaw, (
                            var_strIdItad, var_strSlug, var_strTitle, 
                            var_strType, var_boolMature, var_jsonAssets, var_dateNow
                        ))
                        
                        # 2. Insere/atualiza na tabela steam_itad_mapping
                        var_strSQLMapping = """
                        INSERT INTO steam_itad_mapping (appid, id_itad, slug, title)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (appid)
                        DO UPDATE SET
                            id_itad = EXCLUDED.id_itad,
                            slug = EXCLUDED.slug,
                            title = EXCLUDED.title;
                        """
                        cursor.execute(var_strSQLMapping, (
                            var_intAppid, var_strIdItad, var_strSlug, var_strTitle
                        ))
                        
                        # Commit individual para cada registro
                        cls._var_connConnection.commit()
                        var_intInseridos += 1
                        
                except Exception as e:
                    # Rollback em caso de erro
                    cls._var_connConnection.rollback()
                    logger.error(f"Erro ao inserir AppID {var_intAppid} no ITAD: {e}")
                    continue
            
            logger.info(f"Inseridos/atualizados {var_intInseridos:,} registros no ITAD (itad_raw + steam_itad_mapping)")
            return var_intInseridos
                
        except Exception as e:
            logger.error(f"Erro geral ao inserir dados ITAD em bulk: {e}\")")
            return var_intInseridos
    
    @classmethod
    def inserir_dados_itad_raw_historico_preco_bulk(cls, arg_dictDadosItad: dict[str, list[dict]]) -> int:
        """
        Insere dados históricos de preços na tabela itad_raw em bulk.
        
        Parâmetros:
        - arg_dictDadosItad (dict): Dicionário mapeando ID_ITAD -> lista de registros históricos
        
        Retorna:
        - int: Número de registros inseridos
        """
        cls.conectar()
        try:
            if not arg_dictDadosItad:
                logger.warning("Nenhum dado histórico de preços fornecido para inserção")
                return 0
            
            var_intInseridos = 0
            var_dateNow = datetime.now()

            for var_strIDITAD, var_listHistorico in arg_dictDadosItad.items():
                try:
                    with cls._var_connConnection.cursor() as cursor:
                        var_strSQLHistorico = """
                        UPDATE itad_raw
                        SET historico_preco = %s::jsonb,
                            ultima_atualizacao = %s
                        WHERE id_itad = %s;
                        """
                        
                        # Converte lista para JSON string
                        var_strHistoricoJson = json.dumps(var_listHistorico) if var_listHistorico else None
                        
                        cursor.execute(var_strSQLHistorico, (var_strHistoricoJson, var_dateNow, var_strIDITAD))
                        
                        # Verifica se algum registro foi atualizado
                        if cursor.rowcount > 0:
                            cls._var_connConnection.commit()
                            var_intInseridos += 1
                        else:
                            logger.warning(f"ID_ITAD {var_strIDITAD} não encontrado em itad_raw (pulando)")
                            cls._var_connConnection.rollback()

                except Exception as e:
                    cls._var_connConnection.rollback()
                    logger.error(f"Erro ao atualizar histórico de preços para ID_ITAD {var_strIDITAD}: {e}")
                    continue
            
            logger.info(f"Inseridos {var_intInseridos:,} registros no itad_raw")
            return var_intInseridos
                
        except Exception as e:
            logger.error(f"Erro geral ao inserir dados históricos de preços: {e}")
            return var_intInseridos
        
    @classmethod
    def inserir_dados_itad_raw_batched(cls, arg_dictDadosItad: dict[int, dict], arg_intBatchSize: int = 1000) -> int:
        """
        Insere dados ITAD em lotes para evitar timeout.
        
        Parâmetros:
        - arg_dictDadosItad (dict): Dicionário mapeando appid -> dados ITAD
        - arg_intBatchSize (int): Tamanho do lote (padrão: 1000)
        
        Retorna:
        - int: Total de registros inseridos/atualizados
        """
        if not arg_dictDadosItad:
            return 0
        
        var_listItems = list(arg_dictDadosItad.items())
        var_intTotal = len(var_listItems)
        var_intInseridosTotal = 0
        
        logger.info(f"Inserindo {var_intTotal:,} registros ITAD em lotes de {arg_intBatchSize}")
        
        for i in range(0, var_intTotal, arg_intBatchSize):
            var_listBatch = var_listItems[i:i + arg_intBatchSize]
            var_dictBatch = dict(var_listBatch)
            
            logger.info(f"Processando lote {i//arg_intBatchSize + 1} ({i+1} a {min(i+arg_intBatchSize, var_intTotal)} de {var_intTotal})")
            var_intInseridos = cls.inserir_dados_itad_raw_bulk(var_dictBatch)
            var_intInseridosTotal += var_intInseridos
            
            # Pausa entre lotes
            if i + arg_intBatchSize < var_intTotal:
                sleep(1)
        
        logger.info(f"Total inserido no ITAD: {var_intInseridosTotal:,} registros")
        return var_intInseridosTotal
    
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
        cls.conectar()
        
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
                    
                    with cls._var_connConnection.cursor() as cursor:
                        cursor.execute(var_strSQL, (
                            var_intAppid,
                            var_dictDados.get("name"),
                            datetime.now()
                        ))
                        var_intTotalInserido += cursor.rowcount
                
                cls._var_connConnection.commit()
                logger.info(f"Lote de {len(var_listLote)} registros processado.")
            
            logger.info(f"Dados de steam_generico salvos/atualizados para {var_intTotalInserido} registros.")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_generico: {e}")
            raise Exception(f"Erro ao inserir dados steam_generico: {e}")
                 
    @classmethod
    def buscar_itad_id_por_appid(cls, arg_listAppids: list) -> Generator[str | None, None, None]:
        """
        Busca o ID ITAD correspondente a uma lista de AppIDs Steam.

        Parâmetros:
        - arg_listAppids (list): Lista de AppIDs Steam.

        Retorna:
        - Generator[str | None, None, None]: Generator que produz IDs ITAD correspondentes (um por vez).
                                              Retorna None para AppIDs sem mapeamento ITAD.
        """
        try:
            for var_intAppid in arg_listAppids:
                var_strSQL = """
                SELECT id_itad FROM steam_itad_mapping WHERE appid = %s;
                """
                # Executa a consulta para cada AppID
                with cls._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL, (var_intAppid,))
                    var_tupleResultado = cursor.fetchone()
                    if var_tupleResultado:
                        # Retorna o ID ITAD encontrado
                        yield var_tupleResultado[0]
                    else:
                        yield None
        except Exception as e:
            logger.error(f"Erro ao buscar IDs ITAD para AppIDs fornecidos: {e}")
            raise Exception(f"Erro ao buscar IDs ITAD para AppIDs fornecidos: {e}")
        
    # ============================================
    # MÉTODOS PARA STEAM_UNIFICADO (TABELA CONSOLIDADA)
    # ============================================
    
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
            cls.conectar()
            
            if cls._var_connConnection is None:
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
                arg_dictDados.get('type', 'game'),
                arg_dictDados.get('review_score'),
                arg_dictDados.get('total_reviews'),
                arg_dictDados.get('total_negative'),
                arg_dictDados.get('total_positive'),
                arg_dictDados.get('review_score_desc'),
                json.dumps(arg_dictDados.get('detalhes_completos')) if arg_dictDados.get('detalhes_completos') else None,
                json.dumps(arg_dictDados.get('reviews_completos')) if arg_dictDados.get('reviews_completos') else None,
                datetime.now()
            )
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, var_tupleValores)
                cls._var_connConnection.commit()
                
        except Exception as e:
            logger.error(f"Erro ao inserir em steam_unificado: {e}")
            if cls._var_connConnection:
                cls._var_connConnection.rollback()
            raise