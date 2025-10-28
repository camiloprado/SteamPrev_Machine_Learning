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
                    logger.info("Conexão com o banco de dados estabelecida com sucesso.")
                except Exception as e:
                    logger.error(f"Erro ao conectar ao banco de dados: {e}")
            else:
                logger.info("Já existe uma conexão ativa com o banco de dados.")
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
    def criar_tabela_SteamRaw(cls, arg_strNomeTabela: str = "steam_raw"):
        """
        Cria a tabela de dados brutos da Steam no banco de dados.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser criada. (Padrão: "steam_raw")
        """
        try:
            var_strSQL = f"""
            CREATE TABLE IF NOT EXISTS {arg_strNomeTabela} (
                id SERIAL PRIMARY KEY,
                appid INTEGER UNIQUE NOT NULL,
                detalhes JSONB,
                reviews JSONB,
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
    def inserir_dadosSteamRaw(cls, arg_dictDados: dict):
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
            var_strSQLBusca = "SELECT detalhes, reviews FROM steam_raw WHERE appid = %s;"
            var_dictDadosExistentes = {}
            
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLBusca, (arg_dictDados.get('appid'),))
                var_tupleResultado = cursor.fetchone()
                if var_tupleResultado:
                    var_dictDadosExistentes = {
                        "detalhes": var_tupleResultado[0] if var_tupleResultado[0] else {},
                        "reviews": var_tupleResultado[1] if var_tupleResultado[1] else {}
                    }
            
            # Prepara os novos valores, mantendo os existentes se os novos forem vazios/nulos
            var_dictDetalhes = arg_dictDados.get("detalhes", {})
            var_dictReviews = arg_dictDados.get("reviews", {})
            
            # Se o novo valor for vazio/nulo e houver um valor existente, mantém o existente
            if not var_dictDetalhes and var_dictDadosExistentes.get("detalhes"):
                var_dictDetalhes = var_dictDadosExistentes["detalhes"]
            if not var_dictReviews and var_dictDadosExistentes.get("reviews"):
                var_dictReviews = var_dictDadosExistentes["reviews"]
            
            # Se ambos ainda estiverem vazios, não insere/atualiza
            if not var_dictDetalhes and not var_dictReviews:
                logger.warning(f"Nenhum dado válido para inserir/atualizar para o AppID {arg_dictDados.get('appid')}")
                return
            
            var_strSQL = """
            INSERT INTO steam_raw (
                appid, detalhes, reviews, ultima_atualizacao
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (appid) DO UPDATE SET
                detalhes = EXCLUDED.detalhes,
                reviews = EXCLUDED.reviews,
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            
            var_listValores = [
                arg_dictDados.get("appid"),
                json.dumps(var_dictDetalhes),
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