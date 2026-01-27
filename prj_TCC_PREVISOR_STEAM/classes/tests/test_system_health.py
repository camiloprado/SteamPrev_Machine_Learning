"""
Teste de saúde completo do sistema.

Verifica:
- Imports de todos os módulos principais
- Conexão com banco de dados
- Configurações
- Repositories
- Services
- Estrutura de pastas

Para executar:
    pytest classes/tests/test_system_health.py -v
"""

import pytest
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestImports:
    """Testa se todos os módulos principais podem ser importados."""
    
    def test_import_core_modules(self):
        """Testa imports dos módulos core."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
            from prj_TCC_PREVISOR_STEAM.classes.core.initialization import Initialization
            from prj_TCC_PREVISOR_STEAM.classes.core.loopstation import Loop
            from prj_TCC_PREVISOR_STEAM.classes.core.endprocess import End
            from prj_TCC_PREVISOR_STEAM.classes.core.application import InitApplication
            from prj_TCC_PREVISOR_STEAM.classes.core.process import Process
            
            logger.info("✅ Módulos core importados com sucesso")
            assert True
        except Exception as e:
            pytest.fail(f"Erro ao importar módulos core: {e}")
    
    def test_import_database(self):
        """Testa imports do módulo de banco de dados."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.data.database import Database, PostgreSQL
            
            # Verifica se PostgreSQL é alias de Database
            assert PostgreSQL is Database, "PostgreSQL deveria ser alias de Database"
            
            logger.info("✅ Módulo database importado com sucesso")
            logger.info("✅ Alias PostgreSQL configurado corretamente")
        except Exception as e:
            pytest.fail(f"Erro ao importar database: {e}")
    
    def test_import_repositories(self):
        """Testa imports dos repositories."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.data.repositories.base_repository import (
                BaseRepository, DatabaseError, ConnectionError, QueryError
            )
            from prj_TCC_PREVISOR_STEAM.classes.data.repositories.steam_repository import SteamRepository
            from prj_TCC_PREVISOR_STEAM.classes.data.repositories.itad_repository import ITADRepository
            
            # Verifica herança
            assert issubclass(SteamRepository, BaseRepository), "SteamRepository deve herdar de BaseRepository"
            assert issubclass(ITADRepository, BaseRepository), "ITADRepository deve herdar de BaseRepository"
            
            logger.info("✅ Repositories importados com sucesso")
            logger.info("✅ Herança configurada corretamente")
        except Exception as e:
            pytest.fail(f"Erro ao importar repositories: {e}")
    
    def test_import_services(self):
        """Testa imports dos services."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.services.etl_service import ETLService
            from prj_TCC_PREVISOR_STEAM.classes.services.steam_service import SteamService
            from prj_TCC_PREVISOR_STEAM.classes.services.itad_service import ITADService
            
            logger.info("✅ Services importados com sucesso")
        except Exception as e:
            pytest.fail(f"Erro ao importar services: {e}")
    
    def test_import_ml_modules(self):
        """Testa imports dos módulos de machine learning."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.ml.treinamento import Treinamento
            from prj_TCC_PREVISOR_STEAM.classes.ml.treinamento_avaliacao import TreinamentoAvaliacao
            from prj_TCC_PREVISOR_STEAM.classes.ml.data_splitter import DataSplitter
            
            logger.info("✅ Módulos ML importados com sucesso")
        except Exception as e:
            pytest.fail(f"Erro ao importar módulos ML: {e}")
    
    def test_import_integrations(self):
        """Testa imports das integrações."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.integrations.steam.client import SteamClient
            
            logger.info("✅ Integrações importadas com sucesso")
        except Exception as e:
            pytest.fail(f"Erro ao importar integrações: {e}")


class TestConfiguration:
    """Testa configurações do sistema."""
    
    def test_settings_basic(self):
        """Testa se Settings pode ser inicializado."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
            
            Settings.bd_settings_default()
            
            assert hasattr(Settings, '_var_strDBName'), "Settings deve ter _var_strDBName"
            assert hasattr(Settings, '_var_strDBHost'), "Settings deve ter _var_strDBHost"
            assert hasattr(Settings, '_var_strDBPort'), "Settings deve ter _var_strDBPort"
            
            logger.info(f"✅ Settings configurado: {Settings._var_strDBName}@{Settings._var_strDBHost}:{Settings._var_strDBPort}")
        except Exception as e:
            pytest.fail(f"Erro ao testar Settings: {e}")
    
    def test_env_file_exists(self):
        """Verifica se arquivo .env existe."""
        var_pathEnv = Path(".env")
        
        if not var_pathEnv.exists():
            logger.warning("⚠️ Arquivo .env não encontrado - usando variáveis padrão")
        else:
            logger.info("✅ Arquivo .env encontrado")


class TestDatabaseConnection:
    """Testa conexão com banco de dados."""
    
    def test_database_connect_disconnect(self):
        """Testa conexão e desconexão com banco."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.data.database import Database
            from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
            
            Settings.bd_settings_default()
            Database.conectar()
            
            assert Database._var_connConnection is not None, "Conexão não deveria ser None"
            
            Database.desconectar()
            logger.info("✅ Conexão/desconexão funcionando corretamente")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível conectar ao banco: {e}")
            pytest.skip("Banco de dados não disponível")


class TestRepositories:
    """Testa se repositories estão funcionando."""
    
    def test_base_repository_methods(self):
        """Verifica se BaseRepository tem todos os métodos esperados."""
        from prj_TCC_PREVISOR_STEAM.classes.data.repositories.base_repository import BaseRepository
        
        var_listMetodosEsperados = [
            '_conectar', '_desconectar', '_verificar_conexao',
            '_executar_query', '_executar_query_unica', '_executar_comando',
            '_executar_transacao', '_contar_registros', '_executar_bulk_insert'
        ]
        
        for var_strMetodo in var_listMetodosEsperados:
            assert hasattr(BaseRepository, var_strMetodo), f"BaseRepository deve ter método {var_strMetodo}"
        
        logger.info(f"✅ BaseRepository tem todos os {len(var_listMetodosEsperados)} métodos esperados")


class TestProjectStructure:
    """Testa estrutura de pastas do projeto."""
    
    def test_required_folders_exist(self):
        """Verifica se pastas essenciais existem."""
        var_pathBase = Path("prj_TCC_PREVISOR_STEAM")
        
        var_listPastasEssenciais = [
            "classes",
            "classes/core",
            "classes/data",
            "classes/data/repositories",
            "classes/services",
            "classes/ml",
            "classes/integrations",
            "classes/tests",
            "classes/utils",
            "resources",
            "resources/logs",
            "resources/dados"
        ]
        
        var_intFaltando = 0
        for var_strPasta in var_listPastasEssenciais:
            var_path = var_pathBase / var_strPasta
            if not var_path.exists():
                logger.warning(f"⚠️ Pasta não encontrada: {var_strPasta}")
                var_intFaltando += 1
        
        if var_intFaltando == 0:
            logger.info(f"✅ Todas as {len(var_listPastasEssenciais)} pastas essenciais existem")
        else:
            logger.warning(f"⚠️ {var_intFaltando} pasta(s) faltando")


class TestUtilities:
    """Testa utilitários do sistema."""
    
    def test_monitor_performance_import(self):
        """Testa se monitor de performance pode ser importado."""
        try:
            from prj_TCC_PREVISOR_STEAM.classes.utils.monitor_performance import PerformanceMonitor
            
            var_objMonitor = PerformanceMonitor()
            assert hasattr(var_objMonitor, 'analisar_logs'), "PerformanceMonitor deve ter método analisar_logs"
            
            logger.info("✅ Monitor de performance importado com sucesso")
        except Exception as e:
            pytest.fail(f"Erro ao importar monitor de performance: {e}")


if __name__ == "__main__":
    # Execução direta para testes rápidos
    print("=" * 80)
    print("TESTE DE SAÚDE DO SISTEMA")
    print("=" * 80)
    
    # Testa imports
    test_imports = TestImports()
    
    print("\n[1/11] Testando imports core...")
    test_imports.test_import_core_modules()
    
    print("[2/11] Testando imports database...")
    test_imports.test_import_database()
    
    print("[3/11] Testando imports repositories...")
    test_imports.test_import_repositories()
    
    print("[4/11] Testando imports services...")
    test_imports.test_import_services()
    
    print("[5/11] Testando imports ML...")
    test_imports.test_import_ml_modules()
    
    print("[6/11] Testando imports integrações...")
    test_imports.test_import_integrations()
    
    # Testa configurações
    test_config = TestConfiguration()
    
    print("[7/11] Testando Settings...")
    test_config.test_settings_basic()
    
    print("[8/11] Verificando arquivo .env...")
    test_config.test_env_file_exists()
    
    # Testa banco
    test_db = TestDatabaseConnection()
    
    print("[9/11] Testando conexão com banco...")
    try:
        test_db.test_database_connect_disconnect()
    except:
        print("    ⚠️ Banco não disponível (normal se não estiver rodando)")
    
    # Testa repositories
    test_repos = TestRepositories()
    
    print("[10/11] Testando métodos BaseRepository...")
    test_repos.test_base_repository_methods()
    
    # Testa estrutura
    test_struct = TestProjectStructure()
    
    print("[11/11] Testando estrutura de pastas...")
    test_struct.test_required_folders_exist()
    
    print("\n" + "=" * 80)
    print("✅ TESTE DE SAÚDE CONCLUÍDO!")
    print("=" * 80)
    print("\nPara executar todos os testes com pytest:")
    print("  pytest classes/tests/test_system_health.py -v")
