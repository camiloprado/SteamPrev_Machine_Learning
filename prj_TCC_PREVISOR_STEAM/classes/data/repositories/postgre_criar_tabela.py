from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL

class CriarTabela(PostgreSQL):
    """
    Classe responsável por criar tabelas no banco de dados PostgreSQL.
    """

    @classmethod 
    def steam_generico(cls):
        """
        Cria a tabela 'steam_generico' no banco de dados PostgreSQL, se ela ainda não existir.
        
        Parâmetros:
        
        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_generico (
                    appid INTEGER PRIMARY KEY,
                    name TEXT
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_generico': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def steam_raw(cls):
        """
        Cria a tabela 'steam_raw' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_raw (
                    appid INTEGER PRIMARY KEY,
                    detalhes JSONB,
                    reviews JSONB,
                    ultima_atualizacao TIMESTAMP
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_raw': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def steam_categorias(cls):
        """
        Cria a tabela 'steam_categorias' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_categorias (
                    id_categoria INTEGER PRIMARY KEY,
                    nome_categoria VARCHAR(255)
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_categorias': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)
    
    @classmethod
    def steam_generos(cls):
        """
        Cria a tabela 'steam_generos' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_generos (
                    id_genero INTEGER PRIMARY KEY,
                    nome_genero VARCHAR(255)
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_generos': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def steam_linguagens(cls):
        """
        Cria a tabela 'steam_linguagens' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_linguagens (
                    id_linguagem INTEGER PRIMARY KEY,
                    nome_linguagem VARCHAR(255)
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_linguagens': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)
    
    @classmethod
    def steam_review_score_desc(cls):
        """
        Cria a tabela 'steam_review_score_desc' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_review_score_desc (
                    id_review_score INTEGER PRIMARY KEY,
                    descricao VARCHAR(255)
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_review_score_desc': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def steam_unificado(cls):
        """
        Cria a tabela 'steam_unificado' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_unificado (
                    appid INTEGER PRIMARY KEY,
                    name VARCHAR(600),
                    classificacao_etaria VARCHAR(50),
                    linguagens TEXT[],
                    desenvolvedores TEXT[],
                    distribuidores TEXT[],
                    preco VARCHAR(50),
                    categoria TEXT[],
                    genero TEXT[],
                    data_lancamento VARCHAR(50),
                    type VARCHAR(50),
                    review_score INTEGER,
                    total_reviews INTEGER,
                    total_negative INTEGER,
                    total_positive INTEGER,
                    review_score_desc VARCHAR(255),
                    detalhes_completo JSONB,
                    reviews_completo JSONB
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_unificado': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def itad_raw(cls):
        """
        Cria a tabela 'itad_raw' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS itad_raw (
                    id_itad VARCHAR(100) PRIMARY KEY,
                    slug VARCHAR(600),
                    title VARCHAR(600),
                    type VARCHAR(50),
                    mature BOOLEAN,
                    assets JSONB,
                    historico_preco JSONB,
                    ultima_atualizacao TIMESTAMP
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'itad_raw': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def steam_itad_mapping(cls):
        """
        Cria a tabela 'steam_itad_mapping' no banco de dados, se ela ainda não existir.

        Parâmetros:

        Retorna:
        """
        try:
            var_connConnection = PostgreSQL.conectar()
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_itad_mapping (
                    appid INTEGER PRIMARY KEY,
                    id_itad VARCHAR(100)
                );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_itad_mapping': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)
    
    @classmethod
    def steam_geral(cls) -> None:
        """
        Cria a tabela steam_geral no banco de dados, se ainda não existir.
        """
        var_connConnection = PostgreSQL.conectar()
        
        try:
            var_strSQL = """
            CREATE TABLE IF NOT EXISTS steam_geral (
                appid INTEGER PRIMARY KEY,
                id_itad VARCHAR(100) REFERENCES public.itad_raw(id_itad) ON DELETE SET NULL,
                nome VARCHAR(600) NOT NULL,
                type VARCHAR(50),
                preco VARCHAR(50),
                data_lancamento VARCHAR(50),
                classificacao_etaria VARCHAR(50),
                linguagens TEXT[],
                categorias TEXT[],
                genero TEXT[],
                desenvolvedores TEXT[],
                distribuidores TEXT[],
                review_score INTEGER,
                total_positive INTEGER,
                total_negative INTEGER,
                total_reviews INTEGER,
                review_score_desc VARCHAR(255),
                historico_precos JSONB,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            with var_connConnection.cursor() as var_objCursor:
                var_objCursor.execute(var_strSQL)
                var_connConnection.commit()

        except Exception as e:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar tabela steam_geral: {e}")
        finally:
            PostgreSQL.desconectar(var_connConnection)