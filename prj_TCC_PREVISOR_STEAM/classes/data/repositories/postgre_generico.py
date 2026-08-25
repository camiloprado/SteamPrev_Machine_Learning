from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

from psycopg2 import pool
import logging

logger = logging.getLogger("db.core")

# Allowlist de tabelas conhecidas, usada para validar SQL dinâmico.
CON_TABELAS_VALIDAS = frozenset({
    "steam_generico",
    "steam_raw",
    "steam_categorias",
    "steam_generos",
    "steam_linguagens",
    "steam_review_score_desc",
    "steam_unificado",
    "itad_raw",
    "steam_itad_mapping",
    "steam_geral",
    "processing_checkpoint",
})

class PostgreSQL:
    """
    Classe para operações com PostgreSQL.
    """
    _var_connConnection = None
    _var_poolConnectionPool = None

    @classmethod
    def _validar_nome_tabela(cls, arg_strNomeTabela: str) -> str:
        """
        Valida que o nome da tabela pertence à allowlist de tabelas conhecidas do projeto,
        prevenindo SQL injection via interpolação de nome de tabela em f-string.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser validado.

        Retorna:
        - str: O próprio nome da tabela, se válido.

        Levanta:
        - ValueError: Se o nome da tabela não estiver na allowlist.
        """
        if arg_strNomeTabela not in CON_TABELAS_VALIDAS:
            raise ValueError(f"Nome de tabela inválido ou não permitido: '{arg_strNomeTabela}'")
        return arg_strNomeTabela

    @classmethod
    def _init_pool(cls):
        """
        Inicializa o connection pool compartilhado, se ainda não existir.

        Escreve sempre em PostgreSQL._var_poolConnectionPool (a classe base),
        nunca em cls._var_poolConnectionPool — "cls.attr = valor" dentro de um
        classmethod grava no __dict__ da subclasse que chamou (PostgreSQLSteam,
        PostgreSQLITAD, etc.), não no da base. Sem essa referência explícita,
        cada subclasse acabava criando seu próprio pool de até 10 conexões,
        multiplicando o número real de conexões abertas no Postgres.
        """
        if PostgreSQL._var_poolConnectionPool is None:
            try:
                var_strDbname = Settings._var_dictSettings["db_name"]
                var_strUser = Settings._var_dictSettings["db_user"]
                var_strPassword = Settings._var_dictSettings["db_password"]
                var_strHost = Settings._var_dictSettings["db_host"]
                var_intPort = Settings._var_dictSettings["db_port"]

                PostgreSQL._var_poolConnectionPool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dbname=var_strDbname,
                    user=var_strUser,
                    password=var_strPassword,
                    host=var_strHost,
                    port=var_intPort
                )
                logger.info(f"Connection pool criado: {var_strUser}@{var_strHost}:{var_intPort}/{var_strDbname}")
            except Exception as e:
                logger.error(f"Erro ao criar connection pool: {e}")
                raise Exception(f"Erro ao criar connection pool: {e}")

    @classmethod
    def conectar(cls):
        """
        Estabelece uma conexão com o banco de dados PostgreSQL usando pool.
        Levanta exceção se não conseguir conectar.

        Retorna:
        - var_connConnection: Objeto de conexão do psycopg2.
        """
        if cls._var_connConnection is None or cls._var_connConnection.closed:
            try:
                cls._init_pool()
                cls._var_connConnection = PostgreSQL._var_poolConnectionPool.getconn()
                logger.debug("Conexão obtida do pool")
                return cls._var_connConnection
            except Exception as e:
                cls._var_connConnection = None
                logger.error(f"Erro ao obter conexão do pool: {e}")
                raise Exception(f"Erro ao obter conexão do pool: {e}")
        else:
            logger.debug("Conexão já estabelecida")
            return cls._var_connConnection

    @classmethod
    def desconectar(cls, arg_connConnection = None):
        """
        Devolve a conexão ao pool em vez de fechar.

        Parâmetros:
        - arg_connConnection: Conexão específica a ser devolvida (opcional). Se None, usa a conexão atual da classe.
        """
        try:
            if arg_connConnection and PostgreSQL._var_poolConnectionPool:
                PostgreSQL._var_poolConnectionPool.putconn(arg_connConnection)
                logger.debug("Conexão devolvida ao pool")
                cls._var_connConnection = None
                return

            if cls._var_connConnection and PostgreSQL._var_poolConnectionPool:
                PostgreSQL._var_poolConnectionPool.putconn(cls._var_connConnection)
                logger.debug("Conexão devolvida ao pool")
                cls._var_connConnection = None
            elif cls._var_connConnection:
                cls._var_connConnection.close()
                logger.debug("Conexão fechada (sem pool)")
                cls._var_connConnection = None

        except Exception as e:
            logger.error(f"Erro ao devolver conexão ao pool: {e}")
            raise Exception(f"Erro ao devolver conexão ao pool: {e}")
                    
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
            cls._validar_nome_tabela(arg_strNomeTabela)
            var_strSQL = f"""
            SELECT * FROM {arg_strNomeTabela};
            """
            cls.conectar()
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()
                var_listColnames = [desc[0] for desc in cursor.description]
                var_listDados = [dict(zip(var_listColnames, row)) for row in var_listResultados]
                return var_listDados
            
        except Exception as e:
            logger.error(f"Erro ao buscar todos os dados da tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao buscar todos os dados da tabela '{arg_strNomeTabela}': {e}")
        finally:
            cls.desconectar()
    
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
            cls._validar_nome_tabela(arg_strNomeTabela)
            var_intDias = Settings._var_dictSettings.get("dias_para_atualizacao", 30)

            var_strSQL = f"""
            SELECT * FROM {arg_strNomeTabela}
            WHERE ultima_atualizacao < CURRENT_DATE - INTERVAL '{var_intDias} days'
            """

            var_listParams = []
            if arg_intLimite:
                var_strSQL += " LIMIT %s"
                var_listParams.append(arg_intLimite)

            var_strSQL += ";"

            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, var_listParams or None)
                var_listResultados = cursor.fetchall()
                var_listColnames = [desc[0] for desc in cursor.description]
                var_listDados = [dict(zip(var_listColnames, row)) for row in var_listResultados]
                logger.info(f"Encontrados {len(var_listDados)} jogos desatualizados na tabela '{arg_strNomeTabela}'.")
                return var_listDados
        except Exception as e:
            logger.error(f"Erro ao buscar jogos desatualizados: {e}")
            return []
        finally:
            cls.desconectar()