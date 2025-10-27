from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

import psycopg2, sqlalchemy

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

    @classmethod
    def desconectar(cls):
        """
        Encerra a conexão com o banco de dados PostgreSQL.
        """
        if cls._var_connConnection:
            cls._var_connConnection.close()
            print("Conexão com o banco de dados encerrada.")
            cls._var_connConnection = None
        else:
            print("Nenhuma conexão ativa para encerrar.")

    @classmethod
    def criar_tabela(cls):
        """
        Cria a tabela de jogos no banco de dados.
        """
        var_strSQL = """
        CREATE TABLE IF NOT EXISTS steam_bd (
            id SERIAL PRIMARY KEY,
            appid INTEGER UNIQUE NOT NULL,
            nome VARCHAR(255) NOT NULL,
            detalhes JSONB,
            reviews JSONB
        );
        """
        with cls._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL)
            cls._var_connConnection.commit()
            print("Tabela 'steam_bd' criada com sucesso (se não existia).")
        
print(Settings._var_dictSettings)