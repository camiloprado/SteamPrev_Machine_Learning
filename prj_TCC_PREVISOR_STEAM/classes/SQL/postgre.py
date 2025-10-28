from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from datetime import datetime
import psycopg2, sqlalchemy, json

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
                    print("Conexão com o banco de dados estabelecida com sucesso.")
                except Exception as e:
                    print(f"Erro ao conectar ao banco de dados: {e}")
            else:
                print("Já existe uma conexão ativa com o banco de dados.")
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise Exception(f"Erro ao conectar ao banco de dados: {e}")
        
    @classmethod
    def desconectar(cls):
        """
        Encerra a conexão com o banco de dados PostgreSQL.
        """
        try:
            if cls._var_connConnection:
                cls._var_connConnection.close()
                print("Conexão com o banco de dados encerrada.")
                cls._var_connConnection = None
            else:
                print("Nenhuma conexão ativa para encerrar.")
        except Exception as e:
            print(f"Erro ao desconectar do banco de dados: {e}")
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
                print("Tabela criada com sucesso.")
        except Exception as e:
            print(f"Erro ao criar a tabela: {e}")
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
            print(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
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
            print(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao criar a tabela '{arg_strNomeTabela}': {e}")
        
    @classmethod
    def inserir_dadosSteamBD(cls, arg_dictDados: dict):
        """
        Insere ou atualiza os dados de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_dictDados (dict): Dicionário contendo os dados do jogo a serem inseridos.

        Retorna:
        - None
        """
        try:
            var_strSQL = """
            INSERT INTO steam_bd (
                appid, nome, idade_classificada, classificacao_etaria, linguagens, desenvolvedores,
                distribuidores, preco, metacritic_score, categorias, genero, data_lancamento, ultima_atualizacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                ultima_atualizacao = EXCLUDED.ultima_atualizacao;
            """
            # Extrai os campos na ordem correta
            var_listCampos = [
                "appid", "nome", "idade_classificada", "classificacao_etaria", "linguagens", "desenvolvedores",
                "distribuidores", "preco", "metacritic_score", "categorias", "genero", "data_lancamento", "ultima_atualizacao"
            ]

            var_listValores = []
            for var_strColuna in var_listCampos[:-1]:
                var_anyValor = arg_dictDados.get(var_strColuna)
                # Se for None, alimenta como vazio (string ou lista)
                if var_anyValor is None:
                    # Campos que são listas
                    if var_strColuna in ["linguagens", "desenvolvedores", "distribuidores", "categorias", "genero"]:
                        var_anyValor = []
                    else:
                        var_anyValor = ""
                var_listValores.append(var_anyValor)
            var_listValores.append(datetime.now())
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, tuple(var_listValores))
                cls._var_connConnection.commit()
                print(f"Dados inseridos/atualizados para o AppID {arg_dictDados.get('appid')} - {arg_dictDados.get('nome')}")
        except Exception as e:
            print(f"Erro ao inserir/atualizar dados para o AppID {arg_dictDados.get('appid')}: {e}")
            raise Exception(f"Erro ao inserir/atualizar dados para o AppID {arg_dictDados.get('appid')}: {e}")
        
    @classmethod
    def atualizar_reviews(cls, arg_intAppid: int, arg_jsonReviews: dict):
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
                print(f"Resenhas atualizadas para o AppID {arg_intAppid}.")
        except Exception as e:
            print(f"Erro ao atualizar resenhas para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao atualizar resenhas para o AppID {arg_intAppid}: {e}")
        
    @classmethod
    def buscar_dados(cls, arg_intAppid: int) -> dict | None:
        """
        Busca os dados de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam.

        Retorna:
        - dict | None: Dicionário com os dados do jogo ou None se não encontrado.
        """
        try:
            var_strSQL = """
            SELECT * FROM steam_bd WHERE appid = %s;
            """
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_intAppid,))
                var_resultado = cursor.fetchone()
                if var_resultado:
                    var_listColnames = [desc[0] for desc in cursor.description]
                    return dict(zip(var_listColnames, var_resultado))
                else:
                    print(f"Nenhum dado encontrado para o AppID {arg_intAppid}.")
                    return None
        except Exception as e:
            print(f"Erro ao buscar dados para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao buscar dados para o AppID {arg_intAppid}: {e}")
        
    @classmethod
    def verificar_ultima_atualizacao(cls, arg_intAppid: int) -> datetime | None:
        """
        Verifica a última atualização dos dados de um jogo na tabela do banco de dados da Steam.

        Parâmetros:
        - arg_intAppid (int): ID do aplicativo Steam.

        Retorna:
        - datetime | None: Data e hora da última atualização ou None se não encontrado.
        """
        try:
            var_strSQL = """
            SELECT ultima_atualizacao FROM steam_bd WHERE appid = %s;
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
            print(f"Erro ao verificar última atualização para o AppID {arg_intAppid}: {e}")
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
                print(f"Dados atualizados para o AppID {arg_intAppid}.")
        except Exception as e:
            print(f"Erro ao atualizar dados para o AppID {arg_intAppid}: {e}")
            raise Exception(f"Erro ao atualizar dados para o AppID {arg_intAppid}: {e}")