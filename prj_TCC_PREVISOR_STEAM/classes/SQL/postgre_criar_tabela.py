from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL

class CriarTabela:
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
                    app_id INTEGER,
                    name TEXT
                );
            """
            with var_connConnection.cursor() as var_cursorCursor:
                var_cursorCursor.execute(var_strQuery)
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
                    app_id INTEGER,
                    detalhes JSONB,
                    reviews JSONB
                );
            """
            with var_connConnection.cursor() as var_cursorCursor:
                var_cursorCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_raw': {err}")
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
            #TODO: ALTERAR PARA A QUERY DE CRIAÇÃO DA TABELA UNIFICADA, COM OS TIPOS DE DADOS CORRETOS
            var_strQuery = """
                CREATE TABLE IF NOT EXISTS steam_unificado (
                    app_id INTEGER,
                    name TEXT,
                    release_date DATE,
                    review_score INTEGER,
                    price NUMERIC(10, 2),
                    genres JSONB
                );
            """
            with var_connConnection.cursor() as var_cursorCursor:
                var_cursorCursor.execute(var_strQuery)
                var_connConnection.commit()

        except Exception as err:
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao criar a query para criar a tabela 'steam_unificado': {err}")
        finally:
            PostgreSQL.desconectar(var_connConnection)

    @classmethod
    def 