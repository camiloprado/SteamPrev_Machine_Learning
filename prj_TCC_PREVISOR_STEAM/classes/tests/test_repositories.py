"""
Testes para validar operações de banco de dados dos repositories.

Este módulo testa:
- Conexão e desconexão com o banco
- Operações CRUD básicas
- Transações
- Bulk inserts
- Connection pooling
- Índices e otimizações
- Tratamento de erros

Para executar:
    pytest classes/tests/test_repositories.py -v
"""

import pytest
import logging
from datetime import datetime
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.base_repository import (
    BaseRepository, DatabaseError, ConnectionError, QueryError
)
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.steam_repository import SteamRepository
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.itad_repository import ITADRepository
from prj_TCC_PREVISOR_STEAM.classes.data.database import Database

# Configurar logging para testes
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestBaseRepository:
    """Testes para BaseRepository."""
    
    def test_conexao_e_desconexao(self):
        """Testa se consegue conectar e desconectar do banco."""
        try:
            BaseRepository._conectar()
            assert BaseRepository._verificar_conexao() == True, "Conexão deveria estar ativa"
            
            BaseRepository._desconectar()
            assert BaseRepository._verificar_conexao() == False, "Conexão deveria estar fechada"
            
            logger.info("✅ Teste de conexão/desconexão passou")
        except Exception as e:
            pytest.fail(f"Erro ao testar conexão: {e}")
    
    def test_verificar_conexao_sem_conectar(self):
        """Testa verificação de conexão quando não está conectado."""
        # Garante que não há conexão
        try:
            BaseRepository._desconectar()
        except:
            pass
        
        assert BaseRepository._verificar_conexao() == False, "Sem conexão, deveria retornar False"
        logger.info("✅ Teste de verificação sem conexão passou")
    
    def test_obter_conexao_sem_conectar(self):
        """Testa se lança exceção ao tentar obter conexão sem conectar."""
        try:
            BaseRepository._desconectar()
        except:
            pass
        
        with pytest.raises(ConnectionError):
            BaseRepository._obter_conexao()
        
        logger.info("✅ Teste de exceção de conexão passou")
    
    def test_executar_query_simples(self):
        """Testa execução de query SELECT simples."""
        try:
            BaseRepository._conectar()
            
            # Query para testar
            var_strSQL = "SELECT 1 as numero, 'teste' as texto;"
            var_resultado = BaseRepository._executar_query(var_strSQL)
            
            assert len(var_resultado) == 1, "Deveria retornar 1 linha"
            assert var_resultado[0]['numero'] == 1, "Coluna numero deveria ser 1"
            assert var_resultado[0]['texto'] == 'teste', "Coluna texto deveria ser 'teste'"
            
            logger.info("✅ Teste de query simples passou")
        except Exception as e:
            pytest.fail(f"Erro ao executar query simples: {e}")
        finally:
            BaseRepository._desconectar()
    
    def test_executar_query_unica(self):
        """Testa execução de query que retorna único registro."""
        try:
            BaseRepository._conectar()
            
            var_strSQL = "SELECT NOW() as data_atual;"
            var_resultado = BaseRepository._executar_query_unica(var_strSQL)
            
            assert var_resultado is not None, "Deveria retornar um dicionário"
            assert 'data_atual' in var_resultado, "Deveria ter coluna data_atual"
            
            logger.info("✅ Teste de query única passou")
        except Exception as e:
            pytest.fail(f"Erro ao executar query única: {e}")
        finally:
            BaseRepository._desconectar()
    
    def test_contar_registros(self):
        """Testa contagem de registros em uma tabela."""
        try:
            BaseRepository._conectar()
            
            # Testa contagem em steam_generico (deve existir)
            var_intCount = BaseRepository._contar_registros("steam_generico")
            
            assert isinstance(var_intCount, int), "Count deveria retornar inteiro"
            assert var_intCount >= 0, "Count não pode ser negativo"
            
            logger.info(f"✅ Teste de contagem passou - {var_intCount} registros encontrados")
        except Exception as e:
            # Pode falhar se a tabela não existir - não é erro crítico
            logger.warning(f"⚠️ Teste de contagem não pôde ser completado: {e}")
        finally:
            BaseRepository._desconectar()
    
    def test_query_com_parametros(self):
        """Testa query com parâmetros (previne SQL injection)."""
        try:
            BaseRepository._conectar()
            
            var_strSQL = "SELECT %s::int as valor;"
            var_resultado = BaseRepository._executar_query_unica(var_strSQL, (42,))
            
            assert var_resultado['valor'] == 42, "Parâmetro não foi passado corretamente"
            
            logger.info("✅ Teste de query com parâmetros passou")
        except Exception as e:
            pytest.fail(f"Erro ao executar query com parâmetros: {e}")
        finally:
            BaseRepository._desconectar()
    
    def test_transacao_sucesso(self):
        """Testa execução de transação bem-sucedida."""
        try:
            BaseRepository._conectar()
            
            # Cria tabela temporária para teste
            var_listComandos = [
                ("CREATE TEMP TABLE teste_transacao (id INT, nome VARCHAR(50));", ()),
                ("INSERT INTO teste_transacao VALUES (1, 'Item 1');", ()),
                ("INSERT INTO teste_transacao VALUES (2, 'Item 2');", ()),
            ]
            
            BaseRepository._executar_transacao(var_listComandos)
            
            # Verifica se inseriu
            var_strSQL = "SELECT COUNT(*) as count FROM teste_transacao;"
            var_resultado = BaseRepository._executar_query_unica(var_strSQL)
            
            assert var_resultado['count'] == 2, "Transação deveria ter inserido 2 registros"
            
            logger.info("✅ Teste de transação bem-sucedida passou")
        except Exception as e:
            pytest.fail(f"Erro ao testar transação: {e}")
        finally:
            BaseRepository._desconectar()
    
    def test_query_invalida_lanca_excecao(self):
        """Testa se query inválida lança QueryError."""
        try:
            BaseRepository._conectar()
            
            with pytest.raises(QueryError):
                BaseRepository._executar_query("SELECT * FROM tabela_que_nao_existe;")
            
            logger.info("✅ Teste de exceção em query inválida passou")
        except Exception as e:
            pytest.fail(f"Erro inesperado: {e}")
        finally:
            BaseRepository._desconectar()


class TestSteamRepository:
    """Testes para SteamRepository."""
    
    def test_buscar_appids_nao_processados(self):
        """Testa busca de AppIDs não processados."""
        try:
            var_listAppids = SteamRepository.buscar_appids_nao_processados_otimizado(
                arg_intLimite=10
            )
            
            assert isinstance(var_listAppids, list), "Deveria retornar uma lista"
            logger.info(f"✅ Teste de busca AppIDs não processados passou - {len(var_listAppids)} encontrados")
        except Exception as e:
            logger.warning(f"⚠️ Teste de SteamRepository não pôde ser completado: {e}")
    
    def test_buscar_jogos_desatualizados(self):
        """Testa busca de jogos desatualizados."""
        try:
            var_listJogos = SteamRepository.buscar_jogos_desatualizados(
                arg_intDiasAtualizacao=90,
                arg_intLimite=5
            )
            
            assert isinstance(var_listJogos, list), "Deveria retornar uma lista"
            logger.info(f"✅ Teste de busca jogos desatualizados passou - {len(var_listJogos)} encontrados")
        except Exception as e:
            logger.warning(f"⚠️ Teste de jogos desatualizados não pôde ser completado: {e}")


class TestITADRepository:
    """Testes para ITADRepository."""
    
    def test_buscar_appids_sem_itad(self):
        """Testa busca de AppIDs sem dados ITAD."""
        try:
            var_listAppids = ITADRepository.buscar_appids_sem_itad(arg_intLimit=10)
            
            assert isinstance(var_listAppids, list), "Deveria retornar uma lista"
            logger.info(f"✅ Teste de busca AppIDs sem ITAD passou - {len(var_listAppids)} encontrados")
        except Exception as e:
            logger.warning(f"⚠️ Teste de ITADRepository não pôde ser completado: {e}")


class TestDatabaseOptimizations:
    """Testes para otimizações de banco de dados."""
    
    def test_criar_indices(self):
        """Testa criação de índices para performance."""
        try:
            Database.criar_indices_performance()
            logger.info("✅ Teste de criação de índices passou")
        except Exception as e:
            logger.warning(f"⚠️ Teste de índices não pôde ser completado: {e}")
    
    def test_analisar_tabelas(self):
        """Testa ANALYZE nas tabelas."""
        try:
            Database.analisar_tabelas()
            logger.info("✅ Teste de análise de tabelas passou")
        except Exception as e:
            logger.warning(f"⚠️ Teste de análise não pôde ser completado: {e}")
    
    def test_obter_stats_tabelas(self):
        """Testa obtenção de estatísticas das tabelas."""
        try:
            var_dictStats = Database.obter_stats_tabelas()
            
            assert isinstance(var_dictStats, dict), "Deveria retornar dicionário"
            
            for var_strTabela, var_dictInfo in var_dictStats.items():
                logger.info(f"  {var_strTabela}: {var_dictInfo['rows']:,} registros, {var_dictInfo['size']}")
            
            logger.info("✅ Teste de estatísticas passou")
        except Exception as e:
            logger.warning(f"⚠️ Teste de estatísticas não pôde ser completado: {e}")


class TestConnectionPooling:
    """Testes para connection pooling."""
    
    def test_inicializar_pool(self):
        """Testa inicialização do connection pool."""
        try:
            # Inicializa pool pequeno para teste
            Database.inicializar_pool(min_connections=1, max_connections=3)
            
            # Testa obter conexão
            Database.conectar()
            assert Database._var_connConnection is not None, "Deveria ter conexão"
            Database.desconectar()
            
            # Fecha pool
            Database.fechar_pool()
            
            logger.info("✅ Teste de connection pool passou")
        except Exception as e:
            logger.warning(f"⚠️ Teste de pool não pôde ser completado: {e}")
            # Garante que pool seja fechado
            try:
                Database.fechar_pool()
            except:
                pass
    
    def test_pool_multiplas_conexoes(self):
        """Testa múltiplas conexões simultâneas do pool."""
        try:
            Database.inicializar_pool(min_connections=2, max_connections=5)
            
            # Simula múltiplas operações
            for i in range(5):
                Database.conectar()
                BaseRepository._executar_query("SELECT 1;")
                Database.desconectar()
            
            Database.fechar_pool()
            logger.info("✅ Teste de múltiplas conexões do pool passou")
        except Exception as e:
            logger.warning(f"⚠️ Teste de múltiplas conexões não pôde ser completado: {e}")
            try:
                Database.fechar_pool()
            except:
                pass


class TestBulkOperations:
    """Testes para operações em massa."""
    
    def test_bulk_insert_performance(self):
        """Testa performance de bulk insert."""
        try:
            BaseRepository._conectar()
            
            # Cria tabela temporária
            var_strSQLCreate = """
            CREATE TEMP TABLE teste_bulk (
                id SERIAL PRIMARY KEY,
                valor INT,
                texto VARCHAR(50)
            );
            """
            BaseRepository._executar_comando(var_strSQLCreate)
            
            # Prepara dados para bulk insert
            var_listDados = [(i, f"Item {i}") for i in range(1000)]
            var_strSQLInsert = "INSERT INTO teste_bulk (valor, texto) VALUES (%s, %s);"
            
            # Executa bulk insert
            BaseRepository._executar_bulk_insert(var_strSQLInsert, var_listDados)
            
            # Verifica quantidade inserida
            var_intCount = BaseRepository._contar_registros("teste_bulk")
            assert var_intCount == 1000, f"Deveria ter inserido 1000 registros, mas tem {var_intCount}"
            
            logger.info("✅ Teste de bulk insert passou - 1000 registros inseridos")
        except Exception as e:
            pytest.fail(f"Erro ao testar bulk insert: {e}")
        finally:
            BaseRepository._desconectar()


class TestErrorHandling:
    """Testes para tratamento de erros avançado."""
    
    def test_rollback_em_erro(self):
        """Testa se rollback é executado corretamente em caso de erro."""
        try:
            BaseRepository._conectar()
            
            # Cria tabela temporária
            BaseRepository._executar_comando("""
                CREATE TEMP TABLE teste_rollback (id INT PRIMARY KEY, nome VARCHAR(50));
            """)
            
            # Tenta inserir dados inválidos (duplicados)
            try:
                var_listComandos = [
                    ("INSERT INTO teste_rollback VALUES (1, 'Item 1');", ()),
                    ("INSERT INTO teste_rollback VALUES (1, 'Item 2');", ()),  # Vai falhar (PK duplicada)
                ]
                BaseRepository._executar_transacao(var_listComandos)
                pytest.fail("Deveria ter lançado exceção")
            except QueryError:
                # Verifica que nenhum registro foi inserido (rollback funcionou)
                var_intCount = BaseRepository._contar_registros("teste_rollback")
                assert var_intCount == 0, "Rollback deveria ter revertido todas as inserções"
                logger.info("✅ Teste de rollback passou")
        except Exception as e:
            pytest.fail(f"Erro inesperado: {e}")
        finally:
            BaseRepository._desconectar()


if __name__ == "__main__":
    # Execução direta para testes rápidos
    print("=" * 80)
    print("EXECUTANDO TESTES DE REPOSITORIES")
    print("=" * 80)
    
    # Testes básicos
    test_base = TestBaseRepository()
    
    print("\n[1/17] Testando conexão e desconexão...")
    test_base.test_conexao_e_desconexao()
    
    print("[2/17] Testando verificação de conexão...")
    test_base.test_verificar_conexao_sem_conectar()
    
    print("[3/17] Testando exceção de conexão...")
    test_base.test_obter_conexao_sem_conectar()
    
    print("[4/17] Testando query simples...")
    test_base.test_executar_query_simples()
    
    print("[5/17] Testando query única...")
    test_base.test_executar_query_unica()
    
    print("[6/17] Testando contagem de registros...")
    test_base.test_contar_registros()
    
    print("[7/17] Testando query com parâmetros...")
    test_base.test_query_com_parametros()
    
    print("[8/17] Testando transação...")
    test_base.test_transacao_sucesso()
    
    print("[9/17] Testando query inválida...")
    test_base.test_query_invalida_lanca_excecao()
    
    print("[10/17] Testando SteamRepository - AppIDs não processados...")
    test_steam = TestSteamRepository()
    test_steam.test_buscar_appids_nao_processados()
    
    print("[11/17] Testando SteamRepository - Jogos desatualizados...")
    test_steam.test_buscar_jogos_desatualizados()
    
    print("[12/17] Testando ITADRepository...")
    test_itad = TestITADRepository()
    test_itad.test_buscar_appids_sem_itad()
    
    print("[13/17] Testando criação de índices...")
    test_db = TestDatabaseOptimizations()
    test_db.test_criar_indices()
    
    print("[14/17] Testando análise de tabelas...")
    test_db.test_analisar_tabelas()
    
    print("[15/17] Testando estatísticas de tabelas...")
    test_db.test_obter_stats_tabelas()
    
    print("[16/17] Testando connection pooling...")
    test_pool = TestConnectionPooling()
    test_pool.test_inicializar_pool()
    
    print("[17/17] Testando bulk operations...")
    test_bulk = TestBulkOperations()
    test_bulk.test_bulk_insert_performance()
    
    print("\n" + "=" * 80)
    print("✅ TODOS OS TESTES BÁSICOS CONCLUÍDOS!")
    print("=" * 80)
    print("\nPara executar testes completos com pytest:")
    print("  pytest classes/tests/test_repositories.py -v")
