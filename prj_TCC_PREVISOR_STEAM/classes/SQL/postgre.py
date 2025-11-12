from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from datetime import datetime
import psycopg2, sqlalchemy, json, logging

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
        """
        try:
            if cls._var_connConnection is None:
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
                    logger.error(f"Erro ao conectar ao banco de dados: {e}")
        except Exception as e:
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
    def criar_tabela_SteamRaw_reviews(cls, arg_strNomeTabela: str = "steam_raw_reviews"):
        """
        Cria a tabela de dados brutos da Steam no banco de dados.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser criada. (Padrão: "steam_raw_reviews")
        """
        try:
            var_strSQL = f"""
            CREATE TABLE IF NOT EXISTS {arg_strNomeTabela} (
                id SERIAL PRIMARY KEY,
                appid INTEGER UNIQUE NOT NULL,
                reviews JSONB,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cls.criar_tabela(arg_strSQL=var_strSQL)
        except Exception as e:
            logger.error(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
        
    @classmethod
    def criar_tabela_SteamRaw_details(cls, arg_strNomeTabela: str = "steam_raw_details"):
        """
        Cria a tabela de dados brutos da Steam no banco de dados.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser criada. (Padrão: "steam_raw_details")
        """
        try:
            var_strSQL = f"""
            CREATE TABLE IF NOT EXISTS {arg_strNomeTabela} (
                id SERIAL PRIMARY KEY,
                appid INTEGER UNIQUE NOT NULL,
                detalhes JSONB,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cls.criar_tabela(arg_strSQL=var_strSQL)
        except Exception as e:
            logger.error(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
        
    @classmethod
    def criar_tabela_dadosSteam(cls, arg_strNomeTabela: str = "steam_bd"):
        """
        Cria a tabela de jogos da Steam no banco de dados.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser criada. (Padrão: "steam_bd")
        """
        try:
            var_strSQL = f"""
            CREATE TABLE IF NOT EXISTS {arg_strNomeTabela} (
                id SERIAL PRIMARY KEY,
                appid INTEGER UNIQUE NOT NULL,
                nome VARCHAR(255) NOT NULL,
                idade_classificada VARCHAR(50),
                classificacao_etaria VARCHAR(50),
                linguagens TEXT[],
                desenvolvedores TEXT[],
                distribuidores TEXT[],
                preco VARCHAR(50),
                metacritic_score VARCHAR(10),
                categorias TEXT[],
                genero TEXT[],
                data_lancamento VARCHAR(50),
                reviews JSONB,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cls.criar_tabela(arg_strSQL=var_strSQL)
        except Exception as e:
            logger.error(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")

    @classmethod
    def inserir_dadosSteamRaw(cls, arg_dictDados: dict) -> None:
        """
        Insere ou atualiza dados na tabela steam_raw.

        Parâmetros:
        - arg_dictDados (dict): Dicionário com os dados a inserir.
        """
        cls.conectar()
        try:
            var_intAppid = arg_dictDados.get("appid") or arg_dictDados.get("steam_appid")
            if not var_intAppid:
                logger.warning("AppID ausente em dados steam_raw")
                return
            
            var_dictDetalhes = arg_dictDados.get("detalhes", {})
            var_dictReviews = arg_dictDados.get("reviews", {})
            
            # Verifica se há dados existentes
            var_strSQLBusca = "SELECT detalhes, reviews FROM steam_raw WHERE appid = %s;"
            var_dictExistente = {}
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLBusca, (var_intAppid,))
                var_tuple = cursor.fetchone()
                if var_tuple:
                    var_dictExistente = {
                        "detalhes": var_tuple[0] if var_tuple[0] else {},
                        "reviews": var_tuple[1] if var_tuple[1] else {}
                    }
            
            # Lógica de sobrescrever nulos/vazios
            if not var_dictDetalhes and var_dictExistente.get("detalhes"):
                var_dictDetalhes = var_dictExistente["detalhes"]
            if not var_dictReviews and var_dictExistente.get("reviews"):
                var_dictReviews = var_dictExistente["reviews"]
            
            if not var_dictDetalhes and not var_dictReviews:
                logger.warning(f"Nenhum dado válido para inserir/atualizar para o AppID {var_intAppid}")
                return
            
            var_strSQL = """
            INSERT INTO steam_raw (appid, detalhes, reviews, ultima_atualizacao)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                detalhes = EXCLUDED.detalhes,
                reviews = EXCLUDED.reviews,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            var_listValores = [
                var_intAppid,
                json.dumps(var_dictDetalhes),
                json.dumps(var_dictReviews),
                datetime.now()
            ]
            
            with cls._var_connConnection.cursor() as cursor:
                logger.info(f"Executando SQL INSERT/UPDATE para AppID {var_intAppid}")
                logger.info(f"Valores: detalhes={var_dictDetalhes}, reviews={var_dictReviews}")
                cursor.execute(var_strSQL, tuple(var_listValores))
                var_intRowCount = cursor.rowcount
                cls._var_connConnection.commit()
                logger.info(f"Dados steam_raw inseridos/atualizados para o AppID {var_intAppid} (linhas afetadas: {var_intRowCount})")
        except Exception as e:
            logger.error(f"Erro ao inserir dados steam_raw: {e}")
            raise Exception(f"Erro ao inserir dados steam_raw: {e}")

    @classmethod
    def inserir_dadosSteamRaw_Bulk(cls, arg_listDados: list) -> None:
        """
        Insere ou atualiza dados em bulk na tabela steam_raw de forma otimizada.
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
                
        except Exception as e:
            cls._var_connConnection.rollback()
            logger.error(f"Erro ao inserir dados em bulk em steam_raw: {e}")
            raise Exception(f"Erro ao inserir dados em bulk em steam_raw: {e}")
        
        
    @classmethod
    def inserir_dadosSteamRaw_details(cls, arg_dictDados: dict):
        """
        Insere ou atualiza os dados brutos de um jogo na tabela do banco de dados SteamRaw.
        Não sobrescreve valores preenchidos com valores nulos/vazios.

        Parâmetros:
        - arg_dictDados (dict): Dicionário contendo os dados brutos do jogo a serem inseridos.

        Retorna:
        - None
        """
        try:
            # Verifica se há dados existentes
            var_strSQLBusca = "SELECT detalhes FROM steam_raw_details WHERE appid = %s;"
            var_dictDadosExistentes = {}
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLBusca, (arg_dictDados.get('appid'),))
                var_tupleResultado = cursor.fetchone()
                if var_tupleResultado:
                    var_dictDadosExistentes = {
                        "detalhes": var_tupleResultado[0] if var_tupleResultado[0] else {}
                    }
            
            # Prepara os novos valores, mantendo os existentes se os novos forem vazios/nulos
            var_dictDetalhes = arg_dictDados.get("detalhes", {})
            
            # Se o novo valor for vazio/nulo e houver um valor existente, mantém o existente
            if not var_dictDetalhes and var_dictDadosExistentes.get("detalhes"):
                var_dictDetalhes = var_dictDadosExistentes["detalhes"]
            
            # Se ambos ainda estiverem vazios, não insere/atualiza
            if not var_dictDetalhes:
                logger.warning(f"Nenhum dado válido para inserir/atualizar para o AppID {arg_dictDados.get('appid')}")
                return
            
            var_strSQL = """
            INSERT INTO steam_raw (
                appid, detalhes, ultima_atualizacao
            ) VALUES (%s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                detalhes = EXCLUDED.detalhes,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            var_listValores = [
                arg_dictDados.get("appid"),
                json.dumps(var_dictDetalhes),
                datetime.now()
            ]
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, tuple(var_listValores))
                cls._var_connConnection.commit()
                logger.info(f"Dados brutos inseridos/atualizados para o AppID {arg_dictDados.get('appid')}")
        except Exception as e:
            logger.error(f"Erro ao inserir/atualizar dados brutos para o AppID {arg_dictDados.get('appid')}: {e}")
            raise Exception(f"Erro ao inserir/atualizar dados brutos para o AppID {arg_dictDados.get('appid')}: {e}")
    
    @classmethod
    def inserir_dadosSteamRaw_reviews(cls, arg_dictDados: dict):
        """
        Insere ou atualiza os dados brutos de um jogo na tabela do banco de dados SteamRaw.
        Não sobrescreve valores preenchidos com valores nulos/vazios.

        Parâmetros:
        - arg_dictDados (dict): Dicionário contendo os dados brutos do jogo a serem inseridos.

        Retorna:
        - None
        """
        try:
            # Verifica se há dados existentes
            var_strSQLBusca = "SELECT reviews FROM steam_raw_reviews WHERE appid = %s;"
            var_dictDadosExistentes = {}
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLBusca, (arg_dictDados.get('appid'),))
                var_tupleResultado = cursor.fetchone()
                if var_tupleResultado:
                    var_dictDadosExistentes = {
                        "reviews": var_tupleResultado[0] if var_tupleResultado[0] else {}
                    }
            
            # Prepara os novos valores, mantendo os existentes se os novos forem vazios/nulos
            var_dictReviews = arg_dictDados.get("reviews", {})
            
            # Se o novo valor for vazio/nulo e houver um valor existente, mantém o existente
            if not var_dictReviews and var_dictDadosExistentes.get("reviews"):
                var_dictReviews = var_dictDadosExistentes["reviews"]
            
            # Se ambos ainda estiverem vazios, não insere/atualiza
            if not var_dictReviews:
                logger.warning(f"Nenhum dado válido para inserir/atualizar para o AppID {arg_dictDados.get('appid')}")
                return
            
            var_strSQL = """
            INSERT INTO steam_raw (
                appid, reviews, ultima_atualizacao
            ) VALUES (%s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                reviews = EXCLUDED.reviews,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            var_listValores = [
                arg_dictDados.get("appid"),
                json.dumps(var_dictReviews),
                datetime.now()
            ]
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, tuple(var_listValores))
                cls._var_connConnection.commit()
                logger.info(f"Dados brutos inseridos/atualizados para o AppID {arg_dictDados.get('appid')}")
        except Exception as e:
            logger.error(f"Erro ao inserir/atualizar dados brutos para o AppID {arg_dictDados.get('appid')}: {e}")
            raise Exception(f"Erro ao inserir/atualizar dados brutos para o AppID {arg_dictDados.get('appid')}: {e}")
        
    @classmethod
    def inserir_dadosSteamBD(cls, arg_dictDados: dict):
        """
        Insere ou atualiza os dados de um jogo na tabela do banco de dados da Steam.
        Não sobrescreve valores preenchidos com valores nulos/vazios.

        Parâmetros:
        - arg_dictDados (dict): Dicionário contendo os dados do jogo a serem inseridos.

        Retorna:
        - None
        """
        try:
            # Verifica se há dados existentes
            var_strSQLBusca = "SELECT * FROM steam_bd WHERE appid = %s;"
            var_dictDadosExistentes = {}
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLBusca, (arg_dictDados.get('appid'),))
                var_tupleResultado = cursor.fetchone()
                if var_tupleResultado:
                    var_listColnames = [desc[0] for desc in cursor.description]
                    var_dictDadosExistentes = dict(zip(var_listColnames, var_tupleResultado))
            
            var_strSQL = """
            INSERT INTO steam_bd (
                appid, nome, idade_classificada, classificacao_etaria, linguagens, desenvolvedores,
                distribuidores, preco, metacritic_score, categorias, genero, data_lancamento, reviews, ultima_atualizacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                nome = EXCLUDED.nome,
                idade_classificada = EXCLUDED.idade_classificada,
                classificacao_etaria = EXCLUDED.classificacao_etaria,
                linguagens = EXCLUDED.linguagens,
                desenvolvedores = EXCLUDED.desenvolvedores,
                distribuidores = EXCLUDED.distribuidores,
                preco = EXCLUDED.preco,
                metacritic_score = EXCLUDED.metacritic_score,
                categorias = EXCLUDED.categorias,
                genero = EXCLUDED.genero,
                data_lancamento = EXCLUDED.data_lancamento,
                reviews = EXCLUDED.reviews,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            # Extrai os campos na ordem correta
            var_listCampos = [
                "appid", "nome", "idade_classificada", "classificacao_etaria", "linguagens", "desenvolvedores",
                "distribuidores", "preco", "metacritic_score", "categorias", "genero", "data_lancamento", "reviews", "ultima_atualizacao"
            ]

            var_listValores = []
            for var_strColuna in var_listCampos[:-1]:
                var_anyValor = arg_dictDados.get(var_strColuna)
                
                # Se o novo valor for None ou vazio e houver um valor existente, mantém o existente
                if var_dictDadosExistentes:
                    var_anyValorExistente = var_dictDadosExistentes.get(var_strColuna)
                    
                    # Para listas: se o novo valor for None ou lista vazia e o existente tiver conteúdo
                    if var_strColuna in ["linguagens", "desenvolvedores", "distribuidores", "categorias", "genero"]:
                        if (var_anyValor is None or var_anyValor == [] or var_anyValor == "null") and var_anyValorExistente:
                            var_anyValor = var_anyValorExistente
                        elif var_anyValor is None or var_anyValor == [] or var_anyValor == "null":
                            var_anyValor = []
                    # Para strings: se o novo valor for None ou vazio e o existente tiver conteúdo
                    else:
                        if (var_anyValor is None or var_anyValor == "" or var_anyValor == "null") and var_anyValorExistente:
                            var_anyValor = var_anyValorExistente
                        elif var_anyValor is None or var_anyValor == "null":
                            var_anyValor = "null"
                else:
                    # Se não houver dados existentes, trata None normalmente
                    if var_anyValor is None or var_anyValor == "null":
                        if var_strColuna in ["linguagens", "desenvolvedores", "distribuidores", "categorias", "genero"]:
                            var_anyValor = []
                        else:
                            var_anyValor = "null"
                
                var_listValores.append(var_anyValor)
            var_listValores.append(datetime.now())
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, tuple(var_listValores))
                cls._var_connConnection.commit()
                logger.info(f"Dados inseridos/atualizados para o AppID {arg_dictDados.get('appid')} - {arg_dictDados.get('nome')}")
        except Exception as e:
            logger.error(f"Erro ao inserir/atualizar dados para o AppID {arg_dictDados.get('appid')}: {e}")
            raise Exception(f"Erro ao inserir/atualizar dados para o AppID {arg_dictDados.get('appid')}: {e}")
        
    @classmethod
    def atualizar_reviewsSteamBD(cls, arg_intAppid: int, arg_jsonReviews: dict):
        """
        Atualiza as resenhas de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam.
        - arg_jsonReviews (dict): Resenhas em formato JSON.

        Retorna:
        - None
        """
        try:
            var_strSQL = """
            UPDATE steam_bd
            SET reviews = %s,
                ultima_atualizacao = %s
            WHERE appid = %s;
            """
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(
                    var_strSQL,
                    (
                        json.dumps(arg_jsonReviews),
                        datetime.now(),
                        arg_intAppid
                    )
                )
                cls._var_connConnection.commit()
                logger.info(f"Resenhas atualizadas para o AppID {arg_intAppid}.")
        except Exception as e:
            logger.error(f"Erro ao atualizar resenhas para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao atualizar resenhas para o AppID {arg_intAppid}: {e}")
        
    @classmethod
    def buscar_dados(cls, arg_intAppid: int, arg_strNomeTabela: str) -> dict | None:
        """
        Busca os dados de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam.
        - arg_strNomeTabela (str): Nome da tabela onde os dados serão buscados.

        Retorna:
        - dict | None: Dicionário com os dados do jogo ou None se não encontrado.
        """
        try:
            var_strSQL = f"""
            SELECT * FROM {arg_strNomeTabela} WHERE appid = %s;
            """
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_intAppid,))
                var_resultado = cursor.fetchone()
                if var_resultado:
                    var_listColnames = [desc[0] for desc in cursor.description]
                    return dict(zip(var_listColnames, var_resultado))
                else:
                    logger.warning(f"Nenhum dado encontrado para o AppID {arg_intAppid}.")
                    return None
        except Exception as e:
            logger.error(f"Erro ao buscar dados para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao buscar dados para o AppID {arg_intAppid}: {e}")
    
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
    def buscar_appids_nao_processados(cls, arg_intLimit: int = None) -> list[int]:
        """
        Busca AppIDs que estão em steam_raw mas não estão em steam_bd.
        Útil para identificar jogos que precisam ser processados.

        Parâmetros:
        - arg_intLimit (int): Número máximo de AppIDs a retornar. Use None para sem limite. (Padrão: None)

        Retorna:
        - list[int]: Lista de AppIDs que precisam ser processados.
        """
        cls.conectar()
        try:
            var_strSQL = """
            SELECT sr.appid 
            FROM steam_raw sr
            LEFT JOIN steam_bd sb ON sr.appid = sb.appid
            WHERE sb.appid IS NULL
            """
            
            if arg_intLimit is not None:
                var_strSQL += f" LIMIT {arg_intLimit}"
            
            var_strSQL += ";"
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                logger.info(f"Encontrados {len(var_listAppids)} AppIDs não processados.")
                return var_listAppids
        except Exception as e:
            logger.error(f"Erro ao buscar AppIDs não processados: {e}")
            return []
    
    @classmethod
    def buscar_todos_appids(cls, arg_strNomeTabela: str = "steam_raw") -> list[int]:
        """
        Busca todos os AppIDs de uma tabela.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela. (Padrão: "steam_raw")

        Retorna:
        - list[int]: Lista de todos os AppIDs na tabela.
        """
        cls.conectar()
        try:
            var_strSQL = f"""
            SELECT appid FROM {arg_strNomeTabela};
            """
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                logger.info(f"Encontrados {len(var_listAppids)} AppIDs na tabela '{arg_strNomeTabela}'.")
                return var_listAppids
        except Exception as e:
            logger.error(f"Erro ao buscar todos os AppIDs da tabela '{arg_strNomeTabela}': {e}")
            return []
    
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
    def verificar_ultima_atualizacao(cls, arg_intAppid: int, arg_strNomeTabela: str) -> datetime | None:
        """
        Verifica a última atualização dos dados de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam.

        Retorna:
        - datetime | None: Data e hora da última atualização ou None se não encontrado.
        """
        try:
            var_strSQL = f"""
            SELECT ultima_atualizacao FROM {arg_strNomeTabela} WHERE appid = %s;
            """
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_intAppid,))
                var_tupleResultado = cursor.fetchone()
                if var_tupleResultado:
                    return var_tupleResultado[0]
                else:
                    # print(f"Nenhum dado encontrado para o AppID {arg_intAppid}.")
                    return None
        except Exception as e:
            logger.error(f"Erro ao verificar última atualização para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao verificar última atualização para o AppID {arg_intAppid}: {e}")
            
    @classmethod
    def atualizar_dados(cls, arg_intAppid: int, arg_dictNovosDados: dict):
        """
        Atualiza os dados de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam.
        - arg_dictNovosDados (dict): Dicionário com os novos dados a serem atualizados.

        Retorna:
        - None
        """
        try:
            var_strSQL = "UPDATE steam_bd SET "
            var_listCampos = []
            var_listValores = []

            for var_strChave, var_listValor in arg_dictNovosDados.items():
                var_listCampos.append(f"{var_strChave} = %s")
                var_listValores.append(var_listValor)

            var_strSQL += ", ".join(var_listCampos)
            var_strSQL += ", ultima_atualizacao = %s WHERE appid = %s"
            var_listValores.append(datetime.now())
            var_listValores.append(arg_intAppid)

            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, tuple(var_listValores))
                cls._var_connConnection.commit()
                logger.info(f"Dados atualizados para o AppID {arg_intAppid}.")
        except Exception as e:
            logger.error(f"Erro ao atualizar dados para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao atualizar dados para o AppID {arg_intAppid}: {e}")