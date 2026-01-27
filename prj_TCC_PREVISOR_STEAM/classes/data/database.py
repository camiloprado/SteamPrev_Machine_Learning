from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings

from datetime import datetime
from psycopg2.extras import execute_batch
from psycopg2 import pool
from time import sleep, time
from typing import Generator
import psycopg2, json, logging

logger = logging.getLogger(__name__)

class Database:
    """
    Classe para operações com PostgreSQL.
    Suporta connection pooling para melhor performance em produção.
    """
    _var_connConnection = None
    _var_connPool = None
    _var_boolUsePool = False

    @classmethod
    def inicializar_pool(cls, arg_intMinConnections: int = 2, arg_intMaxConnections: int = 10):
        """
        Inicializa connection pool para melhor performance.
        Recomendado para ambientes de produção com múltiplas requisições.
        
        Parâmetros:
        - min_connections (int): Número mínimo de conexões (padrão: 2)
        - max_connections (int): Número máximo de conexões (padrão: 10)
        """
        if cls._var_connPool is not None:
            logger.warning("Connection pool já inicializado.")
            return
        
        try:
            var_strDbname = Settings._var_dictSettings["db_name"]
            var_strUser = Settings._var_dictSettings["db_user"]
            var_strPassword = Settings._var_dictSettings["db_password"]
            var_strHost = Settings._var_dictSettings["db_host"]
            var_intPort = Settings._var_dictSettings["db_port"]
            
            cls._var_connPool = pool.ThreadedConnectionPool(
                minconn=arg_intMinConnections,
                maxconn=arg_intMaxConnections,
                dbname=var_strDbname,
                user=var_strUser,
                password=var_strPassword,
                host=var_strHost,
                port=var_intPort
            )
            cls._var_boolUsePool = True
            logger.info(f"Connection pool inicializado: {arg_intMinConnections}-{arg_intMaxConnections} conexões")
        except Exception as e:
            logger.error(f"Erro ao inicializar pool: {e}")
            raise
    
    @classmethod
    def fechar_pool(cls):
        """
        Fecha o connection pool e libera todos os recursos.
        """
        if cls._var_connPool is not None:
            cls._var_connPool.closeall()
            cls._var_connPool = None
            cls._var_boolUsePool = False
            logger.info("Connection pool fechado.")
    
    @classmethod
    def conectar(cls):
        """
        Estabelece uma conexão com o banco de dados PostgreSQL.
        Se connection pool estiver ativo, obtém conexão do pool.
        Levanta exceção se não conseguir conectar.
        """
        # Se usar pool, obtém conexão do pool
        if cls._var_boolUsePool and cls._var_connPool is not None:
            cls._var_connConnection = cls._var_connPool.getconn()
            logger.debug("Conexão obtida do pool")
            return
        
        # Caso contrário, usa conexão única
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
        Se connection pool estiver ativo, devolve conexão ao pool.
        """
        try:
            if cls._var_connConnection:
                # Se usar pool, devolve conexão ao invés de fechar
                if cls._var_boolUsePool and cls._var_connPool is not None:
                    cls._var_connPool.putconn(cls._var_connConnection)
                    logger.debug("Conexão devolvida ao pool")
                else:
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
    def executar_query(cls, arg_strSQL: str, arg_tupleParams: tuple = ()):
        """
        Executa um comando SQL genérico no banco de dados.

        Parâmetros:
        - arg_strSQL (str): Comando SQL a ser executado.
        - arg_tupleParams (tuple): Parâmetros para o comando SQL.
        """
        try:
            with cls._var_connConnection.cursor() as cursor:
                cursor.execute(arg_strSQL, arg_tupleParams)
                cls._var_connConnection.commit()
                logger.info("Comando SQL executado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao executar o comando SQL: {e}")
            raise Exception(f"Erro ao executar o comando SQL: {e}")
        
    @classmethod
    def executar_transacao(cls, arg_listSQLCommands: list[tuple[str, tuple]]):
        """
        Executa uma transação com múltiplos comandos SQL no banco de dados.

        Parâmetros:
        - arg_listSQLCommands (list[tuple[str, tuple]]): Lista de tuplas contendo comandos SQL e seus parâmetros.
        """
        try:
            with cls._var_connConnection.cursor() as cursor:
                for var_strSQL, var_tupleParams in arg_listSQLCommands:
                    cursor.execute(var_strSQL, var_tupleParams)
                cls._var_connConnection.commit()
                logger.info("Transação executada com sucesso.")
        except Exception as e:
            cls._var_connConnection.rollback()
            logger.error(f"Erro ao executar a transação: {e}")
            raise Exception(f"Erro ao executar a transação: {e}")
        
    @classmethod
    def backup_dados(cls, arg_strNomeTabela: str, arg_strCaminhoArquivo: str):
        """
        Realiza um backup dos dados de uma tabela específica para um arquivo JSON.

        Parâmetros:
        - arg_strNomeTabela (str): Nome da tabela a ser feita o backup.
        - arg_strCaminhoArquivo (str): Caminho do arquivo onde o backup será salvo.
        """
        try:
            var_listDados = cls.buscar_todos_dados(arg_strNomeTabela)
            with open(arg_strCaminhoArquivo, 'w', encoding='utf-8') as file:
                json.dump(var_listDados, file, ensure_ascii=False, indent=4)
            logger.info(f"Backup dos dados da tabela '{arg_strNomeTabela}' realizado com sucesso em '{arg_strCaminhoArquivo}'.")
        except Exception as e:
            logger.error(f"Erro ao realizar o backup dos dados da tabela '{arg_strNomeTabela}': {e}")
            raise Exception(f"Erro ao realizar o backup dos dados da tabela '{arg_strNomeTabela}': {e}")
    
    @classmethod
    def criar_indices_performance(cls):
        """
        Cria índices nas tabelas para melhorar performance de queries lentas.
        Baseado na análise de performance dos testes.
        """
        cls.conectar()
        try:
            var_listIndices = [
                # Índices para steam_generico
                "CREATE INDEX IF NOT EXISTS idx_steam_generico_appid ON steam_generico(appid);",
                "CREATE INDEX IF NOT EXISTS idx_steam_generico_ultima_atualizacao ON steam_generico(ultima_atualizacao);",
                
                # Índices para steam_raw
                "CREATE INDEX IF NOT EXISTS idx_steam_raw_appid ON steam_raw(appid);",
                "CREATE INDEX IF NOT EXISTS idx_steam_raw_ultima_atualizacao ON steam_raw(ultima_atualizacao);",
                
                # Índices para steam_itad_mapping
                "CREATE INDEX IF NOT EXISTS idx_steam_itad_mapping_appid ON steam_itad_mapping(appid);",
                "CREATE INDEX IF NOT EXISTS idx_steam_itad_mapping_id_itad ON steam_itad_mapping(id_itad);",
                
                # Índices para itad_raw
                "CREATE INDEX IF NOT EXISTS idx_itad_raw_id_itad ON itad_raw(id_itad);",
                "CREATE INDEX IF NOT EXISTS idx_itad_raw_ultima_atualizacao ON itad_raw(ultima_atualizacao);",
                
                # Índice para steam_unificado
                "CREATE INDEX IF NOT EXISTS idx_steam_unificado_appid ON steam_unificado(appid);",
                "CREATE INDEX IF NOT EXISTS idx_steam_unificado_preco ON steam_unificado(preco);",
            ]
            
            var_intCriados = 0
            var_floatInicio = time()
            
            with cls._var_connConnection.cursor() as cursor:
                for var_strSQL in var_listIndices:
                    try:
                        cursor.execute(var_strSQL)
                        cls._var_connConnection.commit()
                        var_intCriados += 1
                    except Exception as e:
                        logger.warning(f"Índice já existe ou erro ao criar: {e}")
                        cls._var_connConnection.rollback()
            
            var_floatTempo = time() - var_floatInicio
            logger.info(f"{var_intCriados} índices criados/verificados em {var_floatTempo:.2f}s")
            
        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")
            raise
        finally:
            cls.desconectar()
    
    @classmethod
    def analisar_tabelas(cls):
        """
        Executa ANALYZE em todas as tabelas principais para atualizar estatísticas do PostgreSQL.
        Melhora o planejamento de queries pelo optimizer.
        """
        cls.conectar()
        try:
            var_listTabelas = [
                'steam_generico', 'steam_raw', 'steam_unificado',
                'itad_raw', 'steam_itad_mapping'
            ]
            
            var_floatInicio = time()
            
            with cls._var_connConnection.cursor() as cursor:
                for var_strTabela in var_listTabelas:
                    try:
                        cursor.execute(f"ANALYZE {var_strTabela};")
                        cls._var_connConnection.commit()
                    except Exception as e:
                        logger.warning(f"Erro ao analisar {var_strTabela}: {e}")
                        cls._var_connConnection.rollback()
            
            var_floatTempo = time() - var_floatInicio
            logger.info(f"Análise de {len(var_listTabelas)} tabelas concluída em {var_floatTempo:.2f}s")
            
        except Exception as e:
            logger.error(f"Erro ao analisar tabelas: {e}")
            raise
        finally:
            cls.desconectar()
    
    @classmethod
    def obter_stats_tabelas(cls) -> dict:
        """
        Retorna estatísticas de tamanho e contagem das tabelas principais.
        Útil para monitoramento de performance.
        
        Retorna:
        - dict: Dicionário com nome_tabela -> {rows, size}
        """
        cls.conectar()
        try:
            var_dictStats = {}
            var_listTabelas = [
                'steam_generico', 'steam_raw', 'steam_unificado',
                'itad_raw', 'steam_itad_mapping'
            ]
            
            with cls._var_connConnection.cursor() as cursor:
                for var_strTabela in var_listTabelas:
                    try:
                        # Conta registros
                        cursor.execute(f"SELECT COUNT(*) FROM {var_strTabela};")
                        var_intRows = cursor.fetchone()[0]
                        
                        # Obtém tamanho
                        cursor.execute(f"SELECT pg_size_pretty(pg_total_relation_size('{var_strTabela}'));")
                        var_strSize = cursor.fetchone()[0]
                        
                        var_dictStats[var_strTabela] = {
                            'rows': var_intRows,
                            'size': var_strSize
                        }
                    except Exception as e:
                        logger.warning(f"Erro ao obter stats de {var_strTabela}: {e}")
            
            return var_dictStats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
        finally:
            cls.desconectar()


# Alias para compatibilidade com código legado
PostgreSQL = Database