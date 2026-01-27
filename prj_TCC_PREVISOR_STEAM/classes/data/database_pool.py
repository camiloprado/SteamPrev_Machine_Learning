"""
IMPLEMENTAÇÃO FUTURA: Connection Pooling para PostgreSQL

Este arquivo contém a implementação futura de connection pooling usando
psycopg2.pool.ThreadedConnectionPool para melhorar a performance e escalabilidade.

BENEFÍCIOS DO CONNECTION POOLING:
- Reduz overhead de criar/destruir conexões constantemente
- Permite reutilização de conexões abertas
- Gerencia múltiplas conexões concorrentes de forma eficiente
- Melhora performance em aplicações multi-threaded

QUANDO IMPLEMENTAR:
- Quando houver múltiplas requisições simultâneas ao banco
- Quando o overhead de criar conexões estiver impactando performance
- Em ambientes de produção com carga elevada

EXEMPLO DE USO (após implementação):
    from prj_TCC_PREVISOR_STEAM.classes.data.database_pool import DatabasePool
    
    # Inicializar pool (uma vez na aplicação)
    DatabasePool.inicializar_pool(min_connections=2, max_connections=10)
    
    # Usar em repositories
    with DatabasePool.obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tabela;")
        resultado = cursor.fetchall()
    
    # Fechar pool (ao encerrar aplicação)
    DatabasePool.fechar_pool()
"""

from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
from psycopg2 import pool
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    Gerenciador de connection pool para PostgreSQL.
    
    Usa psycopg2.pool.ThreadedConnectionPool para gerenciar um pool de conexões
    reutilizáveis, melhorando performance e escalabilidade.
    """
    
    _var_objPool = None
    _var_intMinConnections = 2
    _var_intMaxConnections = 10
    
    @classmethod
    def inicializar_pool(cls, arg_intMinConnections: int = 2, arg_intMaxConnections: int = 10):
        """
        Inicializa o connection pool.
        
        Parâmetros:
        - arg_intMinConnections (int): Número mínimo de conexões mantidas abertas (padrão: 2)
        - arg_intMaxConnections (int): Número máximo de conexões permitidas (padrão: 10)
        
        Raises:
            Exception: Se houver erro ao criar o pool.
        """
        if cls._var_objPool is not None:
            logger.warning("Pool de conexões já está inicializado. Ignorando.")
            return
        
        try:
            cls._var_intMinConnections = arg_intMinConnections
            cls._var_intMaxConnections = arg_intMaxConnections
            
            var_strDbname = Settings._var_dictSettings["db_name"]
            var_strUser = Settings._var_dictSettings["db_user"]
            var_strPassword = Settings._var_dictSettings["db_password"]
            var_strHost = Settings._var_dictSettings["db_host"]
            var_intPort = Settings._var_dictSettings["db_port"]
            
            cls._var_objPool = pool.ThreadedConnectionPool(
                minconn=cls._var_intMinConnections,
                maxconn=cls._var_intMaxConnections,
                dbname=var_strDbname,
                user=var_strUser,
                password=var_strPassword,
                host=var_strHost,
                port=var_intPort
            )
            
            logger.info(
                f"Connection pool inicializado: "
                f"{cls._var_intMinConnections}-{cls._var_intMaxConnections} conexões para "
                f"{var_strUser}@{var_strHost}:{var_intPort}/{var_strDbname}"
            )
        except Exception as e:
            logger.error(f"Erro ao inicializar connection pool: {e}")
            raise
    
    @classmethod
    @contextmanager
    def obter_conexao(cls):
        """
        Context manager para obter conexão do pool.
        
        Uso:
            with DatabasePool.obter_conexao() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tabela;")
                resultado = cursor.fetchall()
        
        A conexão é automaticamente devolvida ao pool ao sair do contexto.
        
        Yields:
            psycopg2.connection: Conexão do pool.
            
        Raises:
            Exception: Se pool não estiver inicializado ou não houver conexões disponíveis.
        """
        if cls._var_objPool is None:
            raise Exception(
                "Connection pool não inicializado. "
                "Chame DatabasePool.inicializar_pool() primeiro."
            )
        
        var_connConnection = None
        try:
            # Obtém conexão do pool
            var_connConnection = cls._var_objPool.getconn()
            
            if var_connConnection is None:
                raise Exception("Não foi possível obter conexão do pool.")
            
            logger.debug("Conexão obtida do pool")
            yield var_connConnection
            
        except Exception as e:
            # Em caso de erro, faz rollback
            if var_connConnection:
                var_connConnection.rollback()
            logger.error(f"Erro ao usar conexão do pool: {e}")
            raise
        finally:
            # Sempre devolve conexão ao pool
            if var_connConnection:
                cls._var_objPool.putconn(var_connConnection)
                logger.debug("Conexão devolvida ao pool")
    
    @classmethod
    def fechar_pool(cls):
        """
        Fecha todas as conexões do pool.
        
        Deve ser chamado ao encerrar a aplicação para liberar recursos.
        """
        if cls._var_objPool is not None:
            cls._var_objPool.closeall()
            cls._var_objPool = None
            logger.info("Connection pool fechado. Todas as conexões liberadas.")
        else:
            logger.warning("Pool de conexões já estava fechado ou não foi inicializado.")
    
    @classmethod
    def obter_stats(cls) -> dict:
        """
        Retorna estatísticas do connection pool.
        
        Retorna:
            dict: Dicionário com informações sobre o pool.
        """
        if cls._var_objPool is None:
            return {
                "status": "não inicializado",
                "min_connections": 0,
                "max_connections": 0
            }
        
        # psycopg2 pool não expõe estatísticas detalhadas nativamente
        # Aqui retornamos configurações básicas
        return {
            "status": "ativo",
            "min_connections": cls._var_intMinConnections,
            "max_connections": cls._var_intMaxConnections
        }


# ==========================================
# EXEMPLO DE INTEGRAÇÃO COM BaseRepository
# ==========================================

class BaseRepositoryComPool:
    """
    Exemplo de como modificar BaseRepository para usar connection pool.
    
    MUDANÇAS NECESSÁRIAS:
    1. Remover dependência de Database._var_connConnection
    2. Usar DatabasePool.obter_conexao() em todos os métodos
    3. Usar context manager (with) para garantir devolução de conexão
    """
    
    @classmethod
    def _executar_query_exemplo(cls, arg_strSQL: str, arg_tupleParams: tuple = ()) -> list[dict]:
        """
        Exemplo de _executar_query usando connection pool.
        """
        with DatabasePool.obter_conexao() as conn:
            with conn.cursor() as cursor:
                cursor.execute(arg_strSQL, arg_tupleParams)
                var_listResultados = cursor.fetchall()
                var_listColnames = [desc[0] for desc in cursor.description]
                return [dict(zip(var_listColnames, row)) for row in var_listResultados]
    
    @classmethod
    def _executar_comando_exemplo(cls, arg_strSQL: str, arg_tupleParams: tuple = ()):
        """
        Exemplo de _executar_comando usando connection pool.
        """
        with DatabasePool.obter_conexao() as conn:
            with conn.cursor() as cursor:
                cursor.execute(arg_strSQL, arg_tupleParams)
                conn.commit()


# ==========================================
# EXEMPLO DE USO EM APLICAÇÃO
# ==========================================

def exemplo_uso_pool():
    """
    Exemplo completo de como usar DatabasePool na aplicação.
    """
    # 1. Inicializar pool no início da aplicação (ex: bot.py ou __main__)
    DatabasePool.inicializar_pool(arg_intMinConnections=5, arg_intMaxConnections=20)
    
    try:
        # 2. Usar pool para executar queries
        with DatabasePool.obter_conexao() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM steam_generico;")
            var_intTotal = cursor.fetchone()[0]
            print(f"Total de jogos: {var_intTotal}")
        
        # 3. Múltiplas operações podem reutilizar conexões do pool
        for i in range(10):
            with DatabasePool.obter_conexao() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT NOW();")
                print(f"Operação {i+1}: {cursor.fetchone()[0]}")
        
        # 4. Ver estatísticas do pool
        var_dictStats = DatabasePool.obter_stats()
        print(f"Stats do pool: {var_dictStats}")
        
    finally:
        # 5. Fechar pool ao encerrar aplicação
        DatabasePool.fechar_pool()


if __name__ == "__main__":
    print("=" * 80)
    print("EXEMPLO DE CONNECTION POOLING (NÃO EXECUTAR EM PRODUÇÃO)")
    print("=" * 80)
    print("\nEste arquivo é apenas documentação para implementação futura.")
    print("\nPara implementar:")
    print("1. Descomentar código de exemplo")
    print("2. Modificar BaseRepository para usar DatabasePool")
    print("3. Inicializar pool em bot.py ou InitApplication")
    print("4. Fechar pool em Close.py")
    print("\nBenefícios esperados:")
    print("- Redução de 30-50% no tempo de queries repetidas")
    print("- Melhor performance em ambientes multi-threaded")
    print("- Gerenciamento automático de conexões")
    print("=" * 80)
