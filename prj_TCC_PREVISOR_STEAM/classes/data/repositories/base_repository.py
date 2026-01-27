from prj_TCC_PREVISOR_STEAM.classes.data.database import Database
from psycopg2.extras import execute_batch
from functools import wraps
from time import time
import logging, json, psycopg2

logger = logging.getLogger(__name__)

# Configurações de performance
SLOW_QUERY_THRESHOLD = 1.0  # segundos - queries acima desse valor serão logadas como lentas

def log_query_performance(func):
    """
    Decorador para medir e logar performance de queries.
    Loga queries lentas (acima do threshold) como WARNING.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        var_floatStart = time()
        try:
            var_result = func(*args, **kwargs)
            var_floatDuration = time() - var_floatStart
            
            # Loga queries lentas
            if var_floatDuration > SLOW_QUERY_THRESHOLD:
                var_strFuncName = func.__name__
                logger.warning(f"SLOW QUERY: {var_strFuncName} levou {var_floatDuration:.2f}s")
            else:
                logger.debug(f"Query {func.__name__} executada em {var_floatDuration:.3f}s")
            
            return var_result
        except Exception as e:
            var_floatDuration = time() - var_floatStart
            logger.error(f"Query {func.__name__} falhou após {var_floatDuration:.3f}s: {e}")
            raise
    return wrapper

class DatabaseError(Exception):
    """Exceção customizada para erros de banco de dados."""
    pass

class ConnectionError(DatabaseError):
    """Exceção para erros de conexão."""
    pass

class QueryError(DatabaseError):
    """Exceção para erros de query."""
    pass

class BaseRepository:
    """
    Classe base para repositórios com métodos genéricos de acesso ao banco de dados.
    Todos os repositories devem herdar desta classe e usar estes métodos ao invés de acessar Database diretamente.
    
    Features:
    - Tratamento de erros robusto com exceções customizadas
    - Log de performance de queries (detecta queries lentas)
    - Preparado para connection pooling futuro
    - Métodos reutilizáveis para operações CRUD
    
    TODO (Connection Pooling):
    - Implementar psycopg2.pool.ThreadedConnectionPool
    - Adicionar método _obter_conexao_do_pool()
    - Implementar método _devolver_conexao_ao_pool()
    - Configurar min_connections e max_connections via Settings
    """
    
    # ========== CONNECTION MANAGEMENT ==========
    @classmethod
    def _conectar(cls):
        """
        Estabelece conexão com o banco de dados através do Database.
        
        Raises:
            ConnectionError: Se não conseguir conectar ao banco.
        """
        try:
            Database.conectar()
        except Exception as e:
            raise ConnectionError(f"Falha ao conectar ao banco de dados: {e}")
        
    @classmethod
    def _desconectar(cls):
        """
        Encerra conexão com o banco de dados através do Database.
        
        Raises:
            ConnectionError: Se houver erro ao desconectar.
        """
        try:
            Database.desconectar()
        except Exception as e:
            logger.error(f"Erro ao desconectar do banco: {e}")
            raise ConnectionError(f"Falha ao desconectar do banco de dados: {e}")
    
    @classmethod
    def _obter_conexao(cls):
        """
        Obtém a conexão atual do Database.
        
        Returns:
            psycopg2.connection: Conexão ativa com o banco.
            
        Raises:
            ConnectionError: Se a conexão não estiver disponível.
        """
        var_connConnection = Database._var_connConnection
        if var_connConnection is None or var_connConnection.closed:
            raise ConnectionError("Conexão com banco de dados não está disponível. Chame _conectar() primeiro.")
        return var_connConnection
    
    @classmethod
    def _verificar_conexao(cls) -> bool:
        """
        Verifica se a conexão está ativa e funcional.
        
        Returns:
            bool: True se conexão está OK, False caso contrário.
        """
        try:
            var_connConnection = Database._var_connConnection
            if var_connConnection is None or var_connConnection.closed:
                return False
            
            # Testa conexão com query simples
            with var_connConnection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            return True
        except Exception as e:
            logger.debug(f"Verificação de conexão falhou: {e}")
            return False
    
    # ========== QUERY HELPERS ==========
    @classmethod
    @log_query_performance
    def _executar_query(cls, arg_strSQL: str, arg_tupleParams: tuple = ()) -> list[dict]:
        """
        Executa uma query SELECT e retorna uma lista de dicionários.

        Parâmetros:
        - arg_strSQL (str): Comando SQL a ser executado.
        - arg_tupleParams (tuple): Parâmetros para o comando SQL.

        Retorna:
        - list[dict]: Lista de dicionários com os resultados da query.
        
        Raises:
            QueryError: Se houver erro ao executar a query.
            ConnectionError: Se a conexão não estiver disponível.
        """
        try:
            with cls._obter_conexao().cursor() as cursor:
                cursor.execute(arg_strSQL, arg_tupleParams)
                var_listResultados = cursor.fetchall()
                
                if cursor.description:
                    var_listColnames = [desc[0] for desc in cursor.description]
                    var_listDados = [dict(zip(var_listColnames, row)) for row in var_listResultados]
                    return var_listDados
                return []
        except psycopg2.Error as e:
            logger.error(f"Erro PostgreSQL ao executar query: {e}")
            raise QueryError(f"Erro ao executar query: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao executar query: {e}")
            raise

    @classmethod
    @log_query_performance
    def _executar_query_unica(cls, arg_strSQL: str, arg_tupleParams: tuple = ()) -> dict:
        """
        Executa uma query e retorna um único dicionário (primeira linha).

        Parâmetros:
        - arg_strSQL (str): Comando SQL a ser executado.
        - arg_tupleParams (tuple): Parâmetros para o comando SQL.

        Retorna:
        - dict: Dicionário com o resultado da query ou None se não encontrar.
        
        Raises:
            QueryError: Se houver erro ao executar a query.
            ConnectionError: Se a conexão não estiver disponível.
        """
        try:
            with cls._obter_conexao().cursor() as cursor:
                cursor.execute(arg_strSQL, arg_tupleParams)
                var_resultado = cursor.fetchone()
                
                if var_resultado and cursor.description:
                    var_listColnames = [desc[0] for desc in cursor.description]
                    return dict(zip(var_listColnames, var_resultado))
                return None
        except psycopg2.Error as e:
            logger.error(f"Erro PostgreSQL ao executar query única: {e}")
            raise QueryError(f"Erro ao executar query única: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao executar query única: {e}")
            raise

    @classmethod
    @log_query_performance
    def _executar_comando(cls, arg_strSQL: str, arg_tupleParams: tuple = ()):
        """
        Executa um comando SQL genérico (INSERT, UPDATE, DELETE) com commit.

        Parâmetros:
        - arg_strSQL (str): Comando SQL a ser executado.
        - arg_tupleParams (tuple): Parâmetros para o comando SQL.
        
        Raises:
            QueryError: Se houver erro ao executar o comando.
            ConnectionError: Se a conexão não estiver disponível.
        """
        try:
            with cls._obter_conexao().cursor() as cursor:
                cursor.execute(arg_strSQL, arg_tupleParams)
                cls._obter_conexao().commit()
                logger.debug(f"Comando SQL executado com sucesso. Linhas afetadas: {cursor.rowcount}")
        except psycopg2.Error as e:
            cls._obter_conexao().rollback()
            logger.error(f"Erro PostgreSQL ao executar comando: {e}")
            raise QueryError(f"Erro ao executar comando SQL: {e}")
        except Exception as e:
            cls._obter_conexao().rollback()
            logger.error(f"Erro inesperado ao executar comando: {e}")
            raise
    
    @classmethod
    @log_query_performance
    def _executar_transacao(cls, arg_listSQLCommands: list[tuple[str, tuple]]):
        """
        Executa uma transação com múltiplos comandos SQL no banco de dados.

        Parâmetros:
        - arg_listSQLCommands (list[tuple[str, tuple]]): Lista de tuplas contendo comandos SQL e seus parâmetros.
        
        Raises:
            QueryError: Se houver erro em qualquer comando da transação.
            ConnectionError: Se a conexão não estiver disponível.
        """
        try:
            with cls._obter_conexao().cursor() as cursor:
                for var_strSQL, var_tupleParams in arg_listSQLCommands:
                    cursor.execute(var_strSQL, var_tupleParams)
                cls._obter_conexao().commit()
                logger.info(f"Transação com {len(arg_listSQLCommands)} comandos executada com sucesso.")
        except psycopg2.Error as e:
            cls._obter_conexao().rollback()
            logger.error(f"Erro PostgreSQL na transação (rollback executado): {e}")
            raise QueryError(f"Erro ao executar a transação: {e}")
        except Exception as e:
            cls._obter_conexao().rollback()
            logger.error(f"Erro inesperado na transação (rollback executado): {e}")
            raise

    @classmethod
    @log_query_performance
    def _contar_registros(cls, arg_strTabela: str, arg_strWhere: str = "") -> int:
        """
        Conta o número de registros em uma tabela.

        Parâmetros:
        - arg_strTabela (str): Nome da tabela.
        - arg_strWhere (str): Cláusula WHERE opcional (sem a palavra WHERE).

        Retorna:
        - int: Número de registros.
        
        Raises:
            QueryError: Se houver erro ao contar registros.
        """
        try:
            var_strSQL = f"SELECT COUNT(*) as count FROM {arg_strTabela}"
            if arg_strWhere:
                var_strSQL += f" WHERE {arg_strWhere}"
            
            var_resultado = cls._executar_query_unica(var_strSQL)
            return var_resultado['count'] if var_resultado else 0
        except Exception as e:
            logger.error(f"Erro ao contar registros na tabela '{arg_strTabela}': {e}")
            raise
    
    # ========== BULK OPERATIONS ==========
    @classmethod
    @log_query_performance
    def _executar_bulk_insert(cls, arg_strSQL: str, arg_listDados: list[tuple], arg_intBatchSize: int = 1000):
        """
        Executa bulk insert usando execute_batch do psycopg2 (muito mais eficiente).

        Parâmetros:
        - arg_strSQL (str): Comando SQL de INSERT com placeholders (%s).
        - arg_listDados (list[tuple]): Lista de tuplas com os dados a serem inseridos.
        - arg_intBatchSize (int): Tamanho do lote para inserção em massa.
        
        Raises:
            QueryError: Se houver erro durante o bulk insert.
            ConnectionError: Se a conexão não estiver disponível.
        """
        if not arg_listDados:
            logger.warning("Lista de dados vazia para bulk insert. Nenhuma operação realizada.")
            return
            
        try:
            with cls._obter_conexao().cursor() as cursor:
                execute_batch(cursor, arg_strSQL, arg_listDados, page_size=arg_intBatchSize)
                cls._obter_conexao().commit()
                logger.info(f"Bulk insert executado: {len(arg_listDados)} registros inseridos em lotes de {arg_intBatchSize}.")
        except psycopg2.Error as e:
            cls._obter_conexao().rollback()
            logger.error(f"Erro PostgreSQL no bulk insert (rollback executado): {e}")
            raise QueryError(f"Erro ao executar bulk insert: {e}")
        except Exception as e:
            cls._obter_conexao().rollback()
            logger.error(f"Erro inesperado no bulk insert (rollback executado): {e}")
            raise
    
    # ========== BACKUP E UTILITÁRIOS ==========
    @classmethod
    @log_query_performance
    def _backup_tabela(cls, arg_strNomeTabela: str, arg_strCaminhoArquivo: str):
        """
        Realiza um backup dos dados de uma tabela específica para um arquivo JSON.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser feita o backup.
        - arg_strCaminhoArquivo (str): Caminho do arquivo onde o backup será salvo.
        
        Raises:
            QueryError: Se houver erro ao realizar o backup.
            IOError: Se houver erro ao salvar o arquivo.
        """
        try:
            var_strSQL = f"SELECT * FROM {arg_strNomeTabela};"
            var_listDados = cls._executar_query(var_strSQL)
            
            with open(arg_strCaminhoArquivo, 'w', encoding='utf-8') as file:
                json.dump(var_listDados, file, ensure_ascii=False, indent=4, default=str)
            
            logger.info(f"Backup da tabela '{arg_strNomeTabela}' realizado com sucesso: {len(var_listDados)} registros salvos em '{arg_strCaminhoArquivo}'.")
        except IOError as e:
            logger.error(f"Erro ao salvar arquivo de backup: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro ao realizar o backup da tabela '{arg_strNomeTabela}': {e}")
            raise